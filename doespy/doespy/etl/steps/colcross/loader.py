

import abc
import os
import typing
from doespy.etl.etl_util import escape_dict_str
from doespy.etl.steps.colcross.components import BasePlotConfig, axis_formatter, AxisConfig, ArtistConfig, BaseSubplotConfig, ColsForEach, DataFilter, LabelFormatter, Metric, Observer, ObserverContext
from doespy.etl.steps.colcross.subplots.bar import GroupedStackedBarChart
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd
import numpy as np
from typing import Dict, List, Literal, NamedTuple,Tuple,  Union

from doespy.design.etl_design import MyETLBaseModel
from doespy.etl.steps.loaders import PlotLoader

from pydantic import Field


class SubplotGrid(MyETLBaseModel):

    rows: List[str]
    cols: List[str]

    jp_except: str = None
    """Skip certain combinations based on the data id (and parent data_id)
    """

    share_x: Literal['none', 'all', 'row', 'col'] = 'none'
    share_y: Literal['none', 'all', 'row', 'col'] = 'row'

    class WidthHeight(NamedTuple):
        w: float
        h: float

    subplot_size: WidthHeight = WidthHeight(2.5, 2.5)

    def init(self, df: pd.DataFrame, parent_id: Dict[str, str], subplot_size: WidthHeight = None): # Tuple[width, height] ?

        # NOTE: also assumes correctly sorted df

        def dict_to_tuple(d):
            return tuple(sorted(d.items()))

        cfe = ColsForEach(cols=self.rows + self.cols, jp_except=self.jp_except)

        grid = dict()
        for i, df1, data_id in cfe.for_each(df=df, parent_id=parent_id):
            row_id = dict_to_tuple({row: data_id[row] for row in self.rows})
            col_id = dict_to_tuple({col: data_id[col] for col in self.cols})

            if row_id not in grid:
                grid[row_id] = list()

            grid[row_id].append(col_id)

        n_rows = len(grid)

        n_cols = [len(x) for x in grid.values()]
        assert n_cols.count(n_cols[0]) == len(n_cols), f"The subplots do not form a grid (not all rows have the same number of columns)  {n_rows=}  {n_cols=}  (do you use the correct jp_except condition?)"
        n_cols = n_cols[0]


        print(f"Init Subplot Grid: {n_rows=} {n_cols=}")

        print(f"\n{grid=}\n")
        if subplot_size is None:
            subplot_size = self.subplot_size

        # due to squeeze=False -> axs is always 2D array

        fig, axs = plt.subplots(nrows=n_rows, ncols=n_cols, figsize=(n_cols * subplot_size.w, n_rows * subplot_size.h), sharex=self.share_x, sharey=self.share_y, squeeze=False)

        return fig, axs

    def get_cols(self):
        return self.rows + self.cols


    def for_each(self, axs, df: pd.DataFrame, parent_id: Dict[str, str]):

        n_rows = len(axs)
        n_cols = len(axs[0])

        subplot_idx_lst = []

        for row_idx in range(n_rows):
            for col_idx in range(n_cols):
                subplot_idx_lst.append((row_idx, col_idx))

        cfe = ColsForEach(cols=self.rows + self.cols, jp_except=self.jp_except)
        for subplot_idx, (_i, df1, data_id) in zip(subplot_idx_lst, cfe.for_each(df=df, parent_id=parent_id), strict=True):
            yield subplot_idx, df1, data_id



class DefaultPlotConfig(BasePlotConfig):

    legend_fig_kwargs: Dict[str, typing.Any] = None
    """kwargs for figure level legend (no figure level legend if None).
        e.g. {loc: "upper center", ncol: 4, bbox_to_anchor: [0.51, 0.075], columnspacing: 3.5,  fancybox: True}
    """

    # TODO: could add other logic other than a figure legend



class DefaultSubplotConfig(BaseSubplotConfig):

    # select chart type
    chart: Union[GroupedStackedBarChart] = None # TODO: could add others laters

    label_map: Dict[str, str] = None

    ax_title: LabelFormatter = None

    legend: LabelFormatter = None

    xaxis: AxisConfig = None

    yaxis: AxisConfig = None

    cum_artist_config: List[ArtistConfig] = None


    def get_cols(self) -> List[str]:
        if self.chart is not None:
            return self.chart.get_cols()
        else:
            return []


    def create_chart(self, ax, df1, data_id, metric, plot_config, ctx):
        self.chart.plot(ax=ax, df1=df1, data_id=data_id, metric=metric, subplot_config=self, plot_config=plot_config, ctx=ctx)


    def artist_config(self, artist_id) -> Dict:
        return ArtistConfig.merge_cumulative(configs=self.cum_artist_config, data_id=artist_id)


    def label(self, lbl, data_id) -> str:
        if self.label_map is None:
            return lbl
        return self.label_map.get(lbl, lbl)





class DefaultColumnCrossPlotLoader(PlotLoader):

    data_filter: DataFilter

    fig_foreach: ColsForEach

    subplot_grid: SubplotGrid = SubplotGrid(rows=[], cols=[])

    # NOTE: each subplot and thus each artist has one metric
    metrics: Dict[str, Metric]

    # TODO [nku] decide if we want to keep or not
    cum_plot_config: List[DefaultPlotConfig]

    cum_subplot_config: List[DefaultSubplotConfig]

    ctx: ObserverContext = Field(ObserverContext(), alias="_CTX", exclude=True)
    """:meta private:"""

    @abc.abstractmethod
    def setup_handlers():
        # NOTE: option to add custom handlers
        pass


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
                filename = escape_dict_str(plot_id)
                self.save_data(df1, filename=filename, output_dir=output_dir)
                self.save_plot(fig, filename=filename, output_dir=output_dir, use_tight_layout=True, output_filetypes=["pdf"])




    def plot(self, df: pd.DataFrame) -> List:
        if df.empty:
            return

        self.setup_handlers()

        self.ctx.stage(DataPreMetrics).notify(df)

        if self.metrics is not None:
            df = Metric.convert_metrics(self.metrics, df)

        self.ctx.stage(DataPreFilter).notify(df)

        df = self.data_filter.apply(cols=self.collect_cols(), df=df)

        self.ctx.stage(DataPreGroup).notify(df)

        # TODO [nku] we currently don't have any aggregation option here (e.g., mean, std, etc.) -> could be added as an observer

        figs = []

        for _i_plot, df_plot, plot_id in self.fig_foreach.for_each(df, parent_id={}):

            print(f"{plot_id=}")

            self.ctx.stage(FigPreInit).notify(df_plot, plot_id)

            if self.cum_plot_config is not None and len(self.cum_plot_config) > 0:
                plot_config = self.cum_plot_config[0].__class__.merge_cumulative(configs=self.cum_plot_config, plot_id=plot_id)
            else:
                plot_config = None

            fig, axs = self.subplot_grid.init(df=df_plot, parent_id=plot_id)


            self.ctx.stage(FigPreGroup).notify(fig, axs, df_plot, plot_id, plot_config)


            for subplot_idx, df_subplot, subplot_id in self.subplot_grid.for_each(axs, df=df_plot, parent_id=plot_id):

                metric = self.metrics[subplot_id["$metrics$"]]
                subplot_id["$metric_unit$"] = metric.unit_label

                data_id = {**plot_id, **subplot_id, "subplot_row_idx": subplot_idx[0], "subplot_col_idx": subplot_idx[1]}

                self.ctx.stage(SubplotPreConfigMerge).notify(df_subplot, data_id, self.cum_subplot_config, plot_config)

                assert self.cum_subplot_config is not None and len(self.cum_subplot_config) > 0, "cum_subplot_config is missing or empty"

                subplot_config = self.cum_subplot_config[0].__class__.merge_cumulative(configs=self.cum_subplot_config, data_id=data_id)

                ax = axs[subplot_idx]

                self.ctx.stage(SubplotPreChart).notify(ax, df, data_id, subplot_config, plot_config)


                subplot_config.create_chart(ax=ax, df1=df_subplot, data_id=data_id, metric=metric, plot_config=plot_config, ctx=self.ctx)

                self.ctx.stage(SubplotPostChart, defaults=[ax_title, ax_legend, axis]).notify(ax, df, data_id, subplot_config, plot_config)

            self.ctx.stage(FigPost, defaults=[fig_legend]).notify(fig, axs, df_plot, plot_id, plot_config)

            figs.append((plot_id, df_plot, fig))

        return figs



class ColumnCrossPlotLoader(DefaultColumnCrossPlotLoader):

    def setup_handlers(self):
        # no additional handlers
        pass




class DataPreMetrics(Observer):
    def notify(self, df):
        for func in self.observers():
            func(df)

class DataPreFilter(Observer):
    def notify(self, df):
        for func in self.observers():
            func(df)

class DataPreGroup(Observer):
    def notify(self, df):
        for func in self.observers():
            func(df)

class FigPreInit(Observer):
    def notify(self, df_plot, plot_id):
        for func in self.observers():
            func(df_plot, plot_id)

class FigPreGroup(Observer):
    def notify(self, fig, axs, df_plot, plot_id, plot_config):
        for func in self.observers():
            func(fig, axs, df_plot, plot_id, plot_config)

class SubplotPreConfigMerge(Observer):
    def notify(self, df_subplot, subplot_id, cum_subplot_config, plot_config):
        for func in self.observers():
            func(df_subplot, subplot_id, cum_subplot_config, plot_config)

class SubplotPreChart(Observer):
    def notify(self, ax, df_subplot, subplot_id, subplot_config, plot_config):
        for func in self.observers():
            func(ax, df_subplot, subplot_id, subplot_config, plot_config)

class SubplotPostChart(Observer):
    def notify(self, ax, df_subplot, subplot_id,  subplot_config, plot_config):
        for func in self.observers():
            func(ax, df_subplot, subplot_id, subplot_config, plot_config)


def ax_title(ax, df_subplot, subplot_id, subplot_config, plot_config):
    if subplot_config.ax_title is not None:
        title = subplot_config.ax_title.apply(subplot_id, subplot_config=subplot_config, info="ax_title")
        ax.set_title(title)

def ax_legend(ax, df_subplot, subplot_id, subplot_config, plot_config):
    if subplot_config.legend is not None:
        handles, labels = ax.get_legend_handles_labels()
        # remove duplicates
        unique = [(h, l) for i, (h, l) in enumerate(zip(handles, labels)) if l not in labels[:i]]

        ax.legend(*zip(*unique), **subplot_config.legend.kwargs)


def axis(ax, df_subplot, subplot_id, subplot_config, plot_config):

    xcfg = AxisConfig() if subplot_config.xaxis is None else subplot_config.xaxis
    ycfg = AxisConfig() if subplot_config.yaxis is None else subplot_config.yaxis

    # scale
    if xcfg.scale is not None:
        ax.set_xscale(xcfg.scale)

    if ycfg.scale is not None:
        ax.set_yscale(ycfg.scale)

    # label
    if xcfg.label is not None:
        label = xcfg.label.apply(subplot_id, subplot_config=subplot_config, info="xaxis.label")
        ax.set_xlabel(label)

    if ycfg.label is not None:
        label = ycfg.label.apply(subplot_id, subplot_config=subplot_config, info="yaxis.label")
        ax.set_ylabel(label)

    # limits
    if xcfg.lim is not None:
        xmin, xmax = xcfg.lim.limits(ax.xaxis.get_data_interval())
        ax.set_xlim(xmin, xmax)

    if ycfg.lim is not None:
        ymin, ymax = ycfg.lim.limits(ax.yaxis.get_data_interval())
        ax.set_xlim(ymin, ymax)

    # ticks
    if xcfg.ticks is not None:
        if isinstance(xcfg.ticks, int):
            xmin, xmax = ax.get_xlim()
            ax.set_xticks(np.linspace(xmin, xmax, xcfg.ticks))
        else:
            ax.set_xticks(**xcfg.ticks)

    if ycfg.ticks is not None:
        if isinstance(ycfg.ticks, int):
            ymin, ymax = ax.get_ylim()
            ax.set_yticks(np.linspace(ymin, ymax, ycfg.ticks))
        else:
            ax.set_yticks(**ycfg.ticks)

    # tick params
    if xcfg.ticks is not None:
        ax.tick_params(**xcfg.tick_params)

    if ycfg.ticks is not None:
        ax.tick_params(**ycfg.tick_params)


    # formatter
    if xcfg.major_formatter is not None:
        func = axis_formatter[xcfg.major_formatter]
        ax.xaxis.set_major_formatter(FuncFormatter(func))

    if xcfg.minor_formatter is not None:
        func = axis_formatter[xcfg.minor_formatter]
        ax.xaxis.set_minor_formatter(FuncFormatter(func))

    if ycfg.major_formatter is not None:
        func = axis_formatter[ycfg.major_formatter]
        ax.yaxis.set_major_formatter(FuncFormatter(func))

    if ycfg.minor_formatter is not None:
        func = axis_formatter[ycfg.minor_formatter]
        ax.yaxis.set_minor_formatter(FuncFormatter(func))




class FigPost(Observer):
    def notify(self, fig, axs, df_plot, plot_id, plot_config):
        for func in self.observers():
            func(fig, axs, df_plot, plot_id, plot_config)


def fig_legend(fig, axs, df_plot, plot_id, plot_config):

    if plot_config is not None and plot_config.legend_fig_kwargs is not None:

        # collect lables and handles from subplots
        fig_handles, fig_labels = [], []
        for ax in axs.flat:
            handles, labels = ax.get_legend_handles_labels()
            fig_handles += handles
            fig_labels += labels

        # remove duplicates
        unique = [(h, l) for i, (h, l) in enumerate(zip(fig_handles, fig_labels)) if l not in fig_labels[:i]]

        fig.legend(*zip(*unique), **plot_config.legend_fig_kwargs)
