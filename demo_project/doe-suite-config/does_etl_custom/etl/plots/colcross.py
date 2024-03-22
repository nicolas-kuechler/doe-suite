from doespy.etl.steps.colcross.loader import DefaultColumnCrossPlotLoader, DataPreMetrics, DefaultSubplotConfig
from doespy.etl.steps.colcross.subplots.bar import GroupedStackedBarChart

from typing import Dict, List, Union

####################################
# How to extend the default config #
####################################

class MySubplotConfig(DefaultSubplotConfig):

    # only support one chart type
    chart: GroupedStackedBarChart = None

    special: str = None

    def create_chart(self, ax, df1, data_id, metric, ctx):
        self.chart.plot(ax=ax, df1=df1, data_id=data_id, metric=metric, subplot_config=self, ctx=ctx)

    def artist_config(self, artist_id) -> Dict:
        if self.cum_artist_config is None or len(self.cum_artist_config) == 0:
            return {}
        return self.cum_artist_config[0].__class__.merge_cumulative(configs=self.cum_artist_config, data_id=artist_id)


    def get_cols(self) -> List[str]:
        if self.chart is not None:
            return self.chart.get_cols()
        return []


    def label(self, lbl, data_id) -> str:
        if self.label_map is None:
            return lbl

        return self.label_map.get(lbl, lbl)


    #special: str = None


def my_novel_handler(df):
    print(f"MY NOVEL SUPER FANCY HANDLER")

class MyColumnCrossPlotLoader(DefaultColumnCrossPlotLoader):

    # NOTE: we can override the type of cum_subplot_config to provide an extended config
    cum_subplot_config: List[MySubplotConfig]


    def setup_handlers(self):

        self.ctx.add_observer(DataPreMetrics, my_novel_handler)

        # TODO [nku] as an example should do something with the `special` field which was newly added to the config

        # self.ctx.remove_observer(DataPreMetrics, demo)