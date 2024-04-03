from enum import Enum
from doespy.etl.steps.colcross.hooks import CcpHooks
import gossip
from doespy.etl.steps.colcross.hooks import default_hooks
import abc
import os
import typing
from doespy.etl.etl_util import escape_dict_str
from doespy.etl.steps.colcross.components import (
    BasePlotConfig,
    LegendConfig,
    SubplotGrid,
    axis_formatter,
    AxisConfig,
    ArtistConfig,
    BaseSubplotConfig,
    ColsForEach,
    DataFilter,
    LabelFormatter,
    Metric,
)
from doespy.etl.steps.colcross.subplots.bar import GroupedStackedBarChart
from doespy.etl.steps.colcross.subplots.box import GroupedBoxplotChart
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd
import numpy as np
from typing import Dict, List, Literal, NamedTuple, Tuple, Union, Optional

from doespy.design.etl_design import MyETLBaseModel
from doespy.etl.steps.loaders import PlotLoader

from pydantic import Field

blueprints = {}


class PlotConfig(BasePlotConfig):

    legend_fig: LegendConfig = None

    # TODO: could add other logic other than a figure legend


class SubplotConfig(BaseSubplotConfig):

    # select chart type
    chart: Union[GroupedStackedBarChart, GroupedBoxplotChart] = (
        None  # TODO: could add others laters
    )

    label_map: Dict[str, str] = None

    ax_title: LabelFormatter = None

    legend_ax: LegendConfig = None

    xaxis: AxisConfig = None

    yaxis: AxisConfig = None

    cum_artist_config: List[ArtistConfig] = None

    def get_cols(self) -> List[str]:
        if self.chart is not None:
            return self.chart.get_cols()
        else:
            return []

    def create_chart(self, ax, df1, data_id, metric, plot_config):
        self.chart.plot(
            ax=ax,
            df1=df1,
            data_id=data_id,
            metric=metric,
            subplot_config=self,
            plot_config=plot_config,
        )

    def artist_config(self, artist_id, plot_config) -> Dict:
        if self.cum_artist_config is None:
            configs = []
        else:
            configs = self.cum_artist_config

        # inherit label info from legend_ax or legend_fig
        if plot_config is not None and plot_config.legend_fig is not None and plot_config.legend_fig.label is not None:
            base_label = plot_config.legend_fig.get_label(data_id=artist_id, subplot_config=self)
            configs.append(ArtistConfig(jp_query=None, label=base_label))
        elif self.legend_ax is not None and self.legend_ax.label is not None:
            base_label = self.legend_ax.get_label(
                data_id=artist_id, subplot_config=self
            )
            configs.append(ArtistConfig(jp_query=None, label=base_label))

        return ArtistConfig.merge_cumulative(
            configs=configs, data_id=artist_id, subplot_config=self
        )

    def label(self, lbl, data_id) -> str:
        if self.label_map is None:
            return lbl
        return self.label_map.get(lbl, lbl)


class BaseColumnCrossPlotLoader(PlotLoader, abc.ABC):

    data_filter: DataFilter = Field(default_factory=DataFilter.empty)

    fig_foreach: ColsForEach = Field(default_factory=ColsForEach.empty)

    subplot_grid: SubplotGrid = Field(default_factory=SubplotGrid.empty)

    # NOTE: each subplot and thus each artist has one metric
    metrics: Dict[str, Metric]

    cum_plot_config: Optional[List[PlotConfig]]

    cum_subplot_config: List[SubplotConfig]

    @abc.abstractmethod
    def setup_handlers():
        # NOTE: option to add custom handlers or remove them
        pass

    @classmethod
    def blueprint(cls):
        if cls not in blueprints:
            blueprints[cls] = gossip.Blueprint()
        return blueprints[cls]

    def collect_cols(self):
        cols = self.fig_foreach.get_cols()
        cols += self.subplot_grid.get_cols()
        for cfg in self.cum_subplot_config:
            cols += cfg.get_cols()
        return cols

    def load(self, df: pd.DataFrame, options: Dict, etl_info: Dict) -> None:
        if not df.empty:

            output_dir = self.get_output_dir(etl_info)
            os.makedirs(output_dir, exist_ok=True)

            for plot_id, df1, fig in self.plot(df):
                if plot_id is not None and len(plot_id) > 0:
                    filename = escape_dict_str(plot_id)
                else:
                    filename = "out"

                self.save_data(df1, filename=filename, output_dir=output_dir)
                self.save_plot(
                    fig,
                    filename=filename,
                    output_dir=output_dir,
                    use_tight_layout=True,
                    output_filetypes=["pdf"],
                )

    def plot(self, df: pd.DataFrame) -> List:
        if df.empty:
            return

        for hook in gossip.get_all_hooks():
            hook.unregister_all()

        default_hooks.install()

        self.setup_handlers()

        gossip.trigger(CcpHooks.DataPreMetrics, df=df, loader=self)

        if self.metrics is not None:
            df = Metric.convert_metrics(self.metrics, df)

        gossip.trigger(CcpHooks.DataPreFilter, df=df, loader=self)

        df = self.data_filter.apply(cols=self.collect_cols(), df=df)

        gossip.trigger(CcpHooks.DataPreGroup, df=df, loader=self)

        figs = []

        for _i_plot, df_plot, plot_id in self.fig_foreach.for_each(df, parent_id={}):

            print(f"{plot_id=}")

            gossip.trigger(
                CcpHooks.FigPreInit, df_plot=df_plot, plot_id=plot_id, loader=self
            )

            if self.cum_plot_config is not None and len(self.cum_plot_config) > 0:
                plot_config = self.cum_plot_config[0].__class__.merge_cumulative(
                    configs=self.cum_plot_config, plot_id=plot_id
                )
            else:
                plot_config = None

            fig, axs = self.subplot_grid.init(df=df_plot, parent_id=plot_id)

            gossip.trigger(
                CcpHooks.FigPreGroup,
                fig=fig,
                axs=axs,
                df_plot=df_plot,
                plot_id=plot_id,
                plot_config=plot_config,
                loader=self,
            )

            for subplot_idx, df_subplot, subplot_id in self.subplot_grid.for_each(
                axs, df=df_plot, parent_id=plot_id
            ):

                if "$metrics$" in plot_id:
                    m = plot_id["$metrics$"]
                elif "$metrics$" in subplot_id:
                    m = subplot_id["$metrics$"]
                elif len(self.metrics) == 1:
                    # there is only one -> get it
                    m = next(iter(self.metrics.keys()))
                    plot_id["$metrics$"] = m
                metric = self.metrics[m]
                subplot_id["$metric_unit$"] = metric.unit_label

                data_id = {
                    **plot_id,
                    **subplot_id,
                    "subplot_row_idx": subplot_idx[0],
                    "subplot_col_idx": subplot_idx[1],
                }

                gossip.trigger(
                    CcpHooks.SubplotPreConfigMerge,
                    df_subplot=df_subplot,
                    subplot_id=data_id,
                    plot_config=plot_config,
                    cum_subplot_config=self.cum_subplot_config,
                    loader=self,
                )

                assert (
                    self.cum_subplot_config is not None
                    and len(self.cum_subplot_config) > 0
                ), "cum_subplot_config is missing or empty"

                subplot_config = self.cum_subplot_config[0].__class__.merge_cumulative(
                    configs=self.cum_subplot_config, data_id=data_id
                )

                ax = axs[subplot_idx]

                gossip.trigger(
                    CcpHooks.SubplotPreChart,
                    ax=ax,
                    df_subplot=df_subplot,
                    subplot_id=data_id,
                    plot_config=plot_config,
                    subplot_config=subplot_config,
                    loader=self,
                )

                print(f"  subplot_id={data_id}")
                subplot_config.create_chart(
                    ax=ax,
                    df1=df_subplot,
                    data_id=data_id,
                    metric=metric,
                    plot_config=plot_config,
                )

                gossip.trigger(
                    CcpHooks.SubplotPostChart,
                    ax=ax,
                    df_subplot=df_subplot,
                    subplot_id=data_id,
                    plot_config=plot_config,
                    subplot_config=subplot_config,
                    loader=self,
                )

            gossip.trigger(
                CcpHooks.FigPost,
                fig=fig,
                axs=axs,
                df_plot=df_plot,
                plot_id=plot_id,
                plot_config=plot_config,
                loader=self,
            )



            figs.append((plot_id, df_plot, fig))

        return figs


# TODO [nku] cleanup these -> showcase what is possible
class ColumnCrossPlotLoader(BaseColumnCrossPlotLoader):

    def setup_handlers(self):
        pass
        # for x in gossip.get_hook(CcpHooks.SubplotPostChart).get_registrations():
        #    print(f"xxxxxxxxxxxxxxxxxxxx  {x=}  {x.func.__name__} ")
        #    if x.func.__name__ == "ax_title_3":
        #        print(f"UNREGISTERING!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        #        x.unregister()

        # gossip.get_hook(SubplotHooks.SubplotPostChart).unregister_all()

        # TODO [nku] per Loader can have a blueprint -> enables custom hooks

        # ColumnCrossPlotLoader.blueprint().install()

        # gossip.register(ax_title_3, SubplotHooks.SubplotPostChart)


# @ColumnCrossPlotLoader.blueprint().register(CcpHooks.SubplotPostChart)
# def ax_title_3(ax, df_subplot, subplot_id, subplot_config, plot_config):
#    print(f"REACHED!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

# class ColumnCrossPlotLoader2(BaseColumnCrossPlotLoader):
#
#    def setup_handlers(self):
#
#        default_hooks.install()
#        # no additional handlers
#        pass
