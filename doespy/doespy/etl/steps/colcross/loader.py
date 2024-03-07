

import abc
from doespy.etl.steps.colcross.components import ArtistConfig, BaseSubplotConfig, ColsForEach, DataFilter, LabelFormatter, Metric, Observer, ObserverContext
from doespy.etl.steps.colcross.subplots.bar import GroupedStackedBarChart
from matplotlib import pyplot as plt
import pandas as pd
from typing import Dict, List, Literal,Tuple,  Union

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

    def init(self, df: pd.DataFrame, parent_id: Dict[str, str], subplot_size: Tuple[float, float]): # Tuple[width, height] ?

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

        # due to squeeze=False -> axs is always 2D array
        fig, axs = plt.subplots(nrows=n_rows, ncols=n_cols, figsize=(n_cols * subplot_size[0], n_rows * subplot_size[1]), sharex=self.share_x, sharey=self.share_y, squeeze=False)

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



class DefaultSubplotConfig(BaseSubplotConfig):

    # select chart type
    chart: Union[GroupedStackedBarChart] = None # TODO: could add others laters

    label_map: Dict[str, str] = None

    ax_title: LabelFormatter = None

    legend_label: LabelFormatter = None

    cum_artist_config: List[ArtistConfig] = None


    def get_cols(self) -> List[str]:
        if self.charts is not None:
            return self.chart.get_cols()
        else:
            return []


    def create_chart(self, ax, df1, data_id, metric, ctx):
        self.chart.plot(ax=ax, df1=df1, data_id=data_id, metric=metric, subplot_config=self, ctx=ctx)


    def artist_config(self, artist_id) -> Dict:
        return self.cum_artist_config.apply(artist_id, info="cum_artist_config")

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

        for _i_plot, df_plot, plot_id in self.fig_foreach.for_each(df, parent_id={}):

            print(f"{plot_id=}")

            self.ctx.stage(FigPreInit).notify(df_plot, plot_id)

            # TODO [nku] make subplot_size configurable
            fig, axs = self.subplot_grid.init(df=df_plot, parent_id=plot_id, subplot_size=(6, 4))

            self.ctx.stage(FigPreGroup).notify(fig, axs, df_plot, plot_id)


            for subplot_idx, df_subplot, subplot_id in self.subplot_grid.for_each(axs, df=df_plot, parent_id=plot_id):

                data_id = {**plot_id, **subplot_id, "subplot_row_idx": subplot_idx[0], "subplot_col_idx": subplot_idx[1]}

                self.ctx.stage(SubplotPreConfigMerge).notify(df_subplot, subplot_id, self.cum_subplot_config)

                assert self.cum_subplot_config is not None and len(self.cum_subplot_config) > 0, "cum_subplot_config is missing or empty"

                config = self.cum_subplot_config[0].__class__.merge_cumulative(configs=self.cum_subplot_config, data_id=data_id)

                ax = axs[subplot_idx]

                self.ctx.stage(SubplotPreChart).notify(ax, df, data_id, config)

                metric = self.metrics[subplot_id["$metrics$"]]

                config.create_chart(ax=ax, df1=df_subplot, data_id=data_id, metric=metric, ctx=self.ctx)

                self.ctx.stage(SubplotPostChart, defaults=[ax_title, ax_legend]).notify(ax, df, data_id, config)

            self.ctx.stage(FigPost).notify(fig, axs, df_plot, plot_id)


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
    def notify(self, fig, axs, df_plot, plot_id):
        for func in self.observers():
            func(fig, axs, df_plot, plot_id)

class SubplotPreConfigMerge(Observer):
    def notify(self, df_subplot, subplot_id, cum_subplot_config):
        for func in self.observers():
            func(df_subplot, subplot_id, cum_subplot_config)

class SubplotPreChart(Observer):
    def notify(self, ax, df_subplot, subplot_id, config):
        for func in self.observers():
            func(ax, df_subplot, subplot_id, config)

class SubplotPostChart(Observer):
    def notify(self, ax, df_subplot, subplot_id, config):
        for func in self.observers():
            func(ax, df_subplot, subplot_id, config)


def ax_title(ax, df_subplot, subplot_id, config):
    if config.ax_title is not None:
        title = config.ax_title.apply(subplot_id, subplot_config=config, info="ax_title")
        ax.set_title(title)

def ax_legend(ax, df_subplot, subplot_id, config):
    if config.legend_label is not None:
        handles, labels = ax.get_legend_handles_labels()
        # remove duplicates
        unique = [(h, l) for i, (h, l) in enumerate(zip(handles, labels)) if l not in labels[:i]]

        ax.legend(*zip(*unique), **config.legend_label.kwargs)


class FigPost(Observer):
    def notify(self, fig, axs, df_plot, plot_id):
        for func in self.observers():
            func(fig, axs, df_plot, plot_id)