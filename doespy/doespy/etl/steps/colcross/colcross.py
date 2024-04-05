
from doespy.etl.steps.colcross.base import BasePlotConfig, BaseSubplotConfig
from doespy.etl.steps.colcross.hooks import CcpHooks
import gossip
from doespy.etl.steps.colcross.hooks import default_hooks
import abc
import os
from doespy.etl.etl_util import escape_dict_str
from doespy.etl.steps.colcross.components import (
    LegendConfig,
    SubplotGrid,
    axis_formatter,
    AxisConfig,
    ArtistConfig,
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
from doespy.etl.steps.loaders import PlotLoader

from pydantic import Field

blueprints = {}


class PlotConfig(BasePlotConfig):
    """
    The `PlotConfig` class is used to configure the appearance of figure-level aspects.
    """

    legend_fig: LegendConfig = None
    """Configuring a figure-wide legend (refer to ``legend_ax`` for subplot-specific legends)."""

    # TODO: could add other logic other than a figure legend


class SubplotConfig(BaseSubplotConfig):
    """
    The `SubplotConfig` class is used to configure the appearance of a subplot within a figure.
    """

    # select chart type
    chart: Union[GroupedStackedBarChart, GroupedBoxplotChart] = (
        None  # TODO: could add others laters
    )
    """The type of chart used within the subplot."""

    label_map: Dict[str, str] = None
    """A dictionary mapping original data values to labels formatted for the plot.

    Whenever a label is displayed, the original data value is replaced with the corresponding label (if a matching entry exists).
    """

    ax_title: LabelFormatter = None
    """Assign a title to the subplot."""

    legend_ax: LegendConfig = None
    """Assign a subplot-specific legend."""

    xaxis: AxisConfig = None
    """Configure the x-axis of the subplot."""

    yaxis: AxisConfig = None
    """Configure the y-axis of the subplot."""

    cum_artist_config: List[ArtistConfig] = None
    """"This list contains artist configurations that are merged to create one artist configuration for each artist (e.g., a bar part, a line, etc.).

    The configurations are merged cumulatively, giving priority to those listed earlier in case of conflicts.

    By utilizing the ``jp_query`` in list entries, you can create artist-specific configurations based on the data used to generate them.
    For example, the color of one of the bars should be different in a specific subplot.
    """

    def get_cols(self) -> List[str]:
        """:meta private:"""

        if self.chart is not None:
            return self.chart.get_cols()
        else:
            return []

    def create_chart(self, ax, df1, data_id, metric, plot_config):
        """:meta private:"""

        self.chart.plot(
            ax=ax,
            df1=df1,
            data_id=data_id,
            metric=metric,
            subplot_config=self,
            plot_config=plot_config,
        )

    def artist_config(self, artist_id, plot_config) -> Dict:
        """:meta private:"""

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
        """:meta private:"""

        if self.label_map is None:
            return lbl
        return self.label_map.get(lbl, lbl)


class BaseColumnCrossPlotLoader(PlotLoader):

    data_filter: DataFilter = Field(default_factory=DataFilter.empty)
    """Filter the DataFrame to include only the specified values from a predefined list and establish a sorting order.

    .. code-block:: yaml
       :caption: Example

        data_filter:
          allowed:
            col1: [val1, val2]          # filter out rows where col1 is not val1 or val2 + sort col1 (in that order)
            col2: [val3, val4, val5]    # filter out rows where col2 is not val3, val4, or val5 + sort col2
            # col3 is not present, so all values are allowed
    """

    fig_foreach: ColsForEach = Field(default_factory=ColsForEach.empty)
    """Generate an indiviudal figure (file) for each unique combination of values found within the given columns.

    .. code-block:: yaml
       :caption: Example

        fig_foreach:
          cols: [col1, col2] # create a figure for each unique combination of values in col1 and col2
          jp_except: "(col1 == 'A') && (col2 == 'B')"  # optional: exclude specific combinations

    """



    subplot_grid: SubplotGrid = Field(default_factory=SubplotGrid.empty)
    """Create a grid of subplots within a single figure, where each subplot corresponds
    to a unique combination of values from specified row and column columns.

    .. code-block:: yaml
       :caption: Example

        # grid has a row for every unique value in col1 and
        # a column for every unique combination of values in col2 and col3
        # (except for the excluded combination)
        subplot_grid:
          rows: [col1]
          cols: [col2, col3]
          jp_except: "(col1 == 'A') && (col2 == 'B')"  # optional: exclude specific combinations


    """

    # NOTE: each subplot and thus each artist has one metric
    metrics: Dict[str, Metric]
    """A dictionary containing metrics that describe the format of measurement data (i.e., what you typically would visualize on the y-axis of a plot).

    Each entry comprises a key-value pair, with the key representing the metric name and the value denoting its configuration.
    The metric configuration specifies the columns in the dataframe where the data is stored, along with details such as units.
    Additionally, it enables conversion to other units as needed.

    Each subplot will be built based on exactly one metric.
    Use the special key ``$metrics$`` in e.g.,  ``plot_foreach`` and ``subplot_grid``
    to create a plot / subplot for every metric.

    .. code-block:: yaml
       :caption: Example

        metrics:
          time:
            value_cols: [col1_ms] # col1_ms contains the data
            value_divider: 1000 # convert from ms to sec
            unit_label: "sec"
          # could have further metrics
    """


    cum_plot_config: Optional[List[PlotConfig]]
    """"This list contains plot configurations that are merged to create one plot configuration for each figure (refer to 'fig_foreach').

    The configurations are merged cumulatively, giving priority to those listed earlier in case of conflicts.

    By utilizing the ``jp_query`` in list entries, you can create figure-specific configurations based on the data used to generate them (i.e., the columns specified in 'fig_foreach').


    .. code-block:: yaml
       :caption: Example

        cum_plot_config:
        - jp_query: "(col1 == 'A')"
          legend_fig: {label: {template: "{col2}"}} # show a legend in figure where col1 == 'A'
        - # could have further configs
    """

    cum_subplot_config: List[SubplotConfig]
    """This list contains subplot configurations that are merged to create one configuration for each subplot in all figures (refer to ``fig_foreach``, and ``subplot_grid``).

    The configurations are merged cumulatively, giving priority to those listed earlier in case of conflicts.

    By utilizing the ``jp_query`` in list entries, you can create subplot-specific configurations based on the data used to generate them (i.e., the columns specified in 'fig_foreach', and ``subplot_grid``).
    For example, this allows you to use different chart types (bar, line, etc.) or a different color scheme for different subplots.


    .. code-block:: yaml
       :caption: Example

        cum_subplot_config:
        - jp_query: "(col1 == 'A')" # only for subplots where col1 == 'A'
          legend_ax: {label: {template: "{col2}"}}
          ...
        - chart: ... # in all subplots have the same chart type
          ...

        # check SubplotConfig for more options
    """

    @abc.abstractmethod
    def setup_handlers():
        """:meta private:"""
        # NOTE: option to add custom handlers or remove them
        pass

    @classmethod
    def blueprint(cls):
        """:meta private:"""
        if cls not in blueprints:
            blueprints[cls] = gossip.Blueprint()
        return blueprints[cls]

    def collect_cols(self):
        """:meta private:"""
        cols = self.fig_foreach.get_cols()
        cols += self.subplot_grid.get_cols()
        for cfg in self.cum_subplot_config:
            cols += cfg.get_cols()
        return cols

    def load(self, df: pd.DataFrame, options: Dict, etl_info: Dict) -> None:
        """:meta private:"""
        if not df.empty:

            output_dir = self.get_output_dir(etl_info)

            for plot_id, df1, fig in self.plot(df):
                if plot_id is not None and len(plot_id) > 0:
                    filename = escape_dict_str(plot_id)
                else:
                    filename = "out"

                if output_dir is not None:
                    self.save_data(df1, filename=filename, output_dir=output_dir)
                    self.save_plot(
                        fig,
                        filename=filename,
                        output_dir=output_dir,
                        use_tight_layout=True,
                        output_filetypes=["pdf"],
                    )

    def plot(self, df: pd.DataFrame) -> List:
        """:meta private:"""
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
    """
    The `ColumnCrossPlotLoader` facilitates the creation of multiple figures, each potentially containing a subplot grid (e.g., a 2-by-3 grid) derived from the DataFrame's data.

    The use of cumulative configurations (e.g., `cum_plot_config`, `cum_subplot_config`, `cum_artist_config`)
    enables to individually control the appearance of each figure, subplot, and artist (e.g., bar, line) appearing in a subplot.

    The `ColumnCrossPlotLoader` is intentionally designed to be extensible and adaptable, facilitating the integration of custom code.
    This can be achieved by creating a new project-specific Loader that inherits the base functionality.
    """

    def setup_handlers(self):
        """:meta private:"""
        pass