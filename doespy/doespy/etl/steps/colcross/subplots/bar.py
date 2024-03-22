
from doespy.etl.steps.colcross.components import BasePlotConfig, ColsForEach, BaseSubplotConfig, Metric, Observer, ObserverContext
from matplotlib import pyplot as plt
import pandas as pd
from typing import Dict, List, Optional, Tuple

from doespy.design.etl_design import MyETLBaseModel
from dataclasses import dataclass




class GroupedStackedBarChart(MyETLBaseModel):

    group_foreach: ColsForEach = ColsForEach(cols=[])

    bar_foreach: ColsForEach

    part_foreach: ColsForEach = ColsForEach(cols=[])
    """
    "
    if part_foreach is None, i.e., default, then only the $metrics$ columns will be used as bar parts
    """

    bar_width: float = 0.6
    group_padding: float = 0.1


    @dataclass
    class BarPartPosition:

        group_center_pos: float

        bar_left_pos: float
        bar_center_pos: float

        bar_part_bottom: float


    def get_cols(self):
        return self.group_foreach.get_cols() + self.bar_foreach.get_cols() + self.part_foreach.get_cols()


    def plot(self, ax: plt.Axes, df1: pd.DataFrame, data_id: Dict[str, str], metric: Metric, subplot_config: BaseSubplotConfig, plot_config: BasePlotConfig, ctx: ObserverContext):
        group_ticks = set()
        bar_ticks = set()

        ctx.stage(BarSubplotPre).notify(ax=ax, df1=df1, data_id=data_id, metric=metric, subplot_config=subplot_config)

        for part_value, part_error, position, bar_group_id, bar_id, bar_part_id in self.for_each(df1, metric=metric, subplot_id=data_id):

            full_id = {**data_id, **bar_group_id, **bar_id, **bar_part_id}
            # print(f"{full_id=}")

            bar_config = subplot_config.artist_config(full_id)

            ctx.stage(BarArtistPre).notify(ax, part_value, part_error, position, full_id, bar_config)

            label = bar_config.pop("label", None)

            ax.bar(position.bar_center_pos, part_value, width=self.bar_width, label=label, yerr=part_error,  bottom=position.bar_part_bottom, **bar_config)

            ctx.stage(BarArtistPost).notify(ax, part_value, part_error, position, full_id, bar_config)

            # keep track of the labels for each artist
            if self.group_foreach.label is not None:
                group_lbl = self.group_foreach.label.apply({**data_id, **bar_group_id}, subplot_config=subplot_config, info="group_label")
                group_ticks.add((position.group_center_pos, group_lbl))

            if self.bar_foreach.label is not None:
                bar_lbl = self.bar_foreach.label.apply({**data_id, **bar_group_id, **bar_id}, subplot_config=subplot_config, info="bar_label")
                bar_ticks.add((position.bar_center_pos, bar_lbl))


        ctx.stage(BarSubplotPost, defaults=[group_bar_ticks]).notify(ax=ax, df_subplot=df1, data_id=data_id, metric=metric, subplot_config=subplot_config, chart=self, group_ticks=group_ticks, bar_ticks=bar_ticks)


    def for_each(self, df1: pd.DataFrame, metric: Metric, subplot_id: Dict[str, str]):

        bar_left_pos, bar_center_pos, group_center_pos = self._calc_positions(df1, subplot_id=subplot_id)

        i_bar = 0

        for i_group, df_bar_group, bar_group_id in self.group_foreach.for_each(df1, parent_id=subplot_id):

            for _i_bar, df_bar, bar_id in self.bar_foreach.for_each(df_bar_group, parent_id={**subplot_id, **bar_group_id}):

                bottom = 0

                for _i_part, df_bar_part, part_id in self.part_foreach.for_each(df_bar, parent_id={**subplot_id, **bar_group_id, **bar_id}):

                    if len(df_bar_part) < 1:
                        continue

                    assert len(df_bar_part) == 1, f"Dataframe must have only one row to be used as a bar part by columns  (df={df_bar_part})  ({bar_group_id=}, {bar_id=}, {part_id=})"

                    error_cols = metric.error_cols if metric.error_cols is not None else [None] * len(metric.value_cols)

                    for value_col, error_col in zip(metric.value_cols, error_cols, strict=True):

                        bar_part_id = {**part_id, "value_col": value_col, "error_col": error_col}

                        part_value = df_bar_part[value_col].iloc[0]
                        part_error = df_bar_part[error_col].iloc[0] if error_col is not None else None

                        position = GroupedStackedBarChart.BarPartPosition(
                            group_center_pos=group_center_pos[i_group],
                            bar_left_pos=bar_left_pos[i_bar],
                            bar_center_pos=bar_center_pos[i_bar],
                            bar_part_bottom=bottom
                        )

                        bottom += part_value

                        yield part_value, part_error, position, bar_group_id, bar_id, bar_part_id

                i_bar += 1




    def _calc_positions(self, df1: pd.DataFrame, subplot_id: Dict[str, str]):

        # positioning
        bar_info = [] # [3, 2, 3] -> 3 bars in first group, 2 in second, 3 in third

        bar_center_pos = []
        group_center_pos = [] # the center of each group

        pos = 0

        for _i_group, df_bar_group, bar_group_id in self.group_foreach.for_each(df1, parent_id=subplot_id):
            n_bars_per_group = 0

            group_start_pos = pos
            group_end_pos = pos

            for _i_bar, _df_bar, _bar_id in self.bar_foreach.for_each(df_bar_group, parent_id={**subplot_id, **bar_group_id}):
                n_bars_per_group += 1

                bar_center_pos.append(pos)
                group_end_pos = pos
                pos += self.bar_width

            # [2, 2.5, 3, 3.5] => 5.5 / 2 = 2.75
            # [2, 2.5, 3, 3.5, 4] => 6 / 2 = 3
            group_center_pos.append((group_start_pos + group_end_pos) / 2)

            pos += self.group_padding

            bar_info.append(n_bars_per_group)

        bar_left_pos = [x - self.bar_width / 2 for x in bar_center_pos] # + self.bar_width / 2

        return bar_left_pos, bar_center_pos, group_center_pos




class BarSubplotPre(Observer):
    def notify(self, ax: plt.Axes, df1: pd.DataFrame, data_id: Dict[str, str], metric: Metric, subplot_config: BaseSubplotConfig):
        for func in self.observers():
            func(ax, df1, data_id, metric, subplot_config)


class BarArtistPre(Observer):
    def notify(self, ax: plt.Axes, part_value: float, part_error: Optional[float], position: GroupedStackedBarChart.BarPartPosition, full_id: Dict[str, str], bar_config: Dict):
        for func in self.observers():
            func(ax, part_value, part_error, position, full_id, bar_config)

class BarArtistPost(Observer):

    def notify(self, ax: plt.Axes, part_value: float, part_error: Optional[float], position: GroupedStackedBarChart.BarPartPosition, full_id: Dict[str, str], bar_config: Dict):
        for func in self.observers():
            func(ax, part_value, part_error, position, full_id, bar_config)


class BarSubplotPost(Observer):
    def notify(self, ax: plt.Axes, df_subplot: pd.DataFrame, data_id: Dict, metric: Metric, subplot_config:  BaseSubplotConfig, chart: GroupedStackedBarChart, group_ticks: List[Tuple[float, str]], bar_ticks: List[Tuple[float, str]]):
        for func in self.observers():
            func(ax=ax, df_subplot=df_subplot, data_id=data_id, metric=metric, subplot_config=subplot_config, chart=chart, group_ticks=group_ticks, bar_ticks=bar_ticks)


def group_bar_ticks(ax: plt.Axes, df_subplot: pd.DataFrame, data_id: Dict, metric: Metric, subplot_config:  BaseSubplotConfig, chart: GroupedStackedBarChart, group_ticks: List[Tuple[float, str]], bar_ticks: List[Tuple[float, str]]):
    if group_ticks:
        group_xticks, group_labels = zip(*group_ticks)
        ax.set_xticks(group_xticks, labels=group_labels, **chart.group_foreach.label.kwargs)

    if bar_ticks:
        is_minor = group_ticks
        bar_xticks, bar_labels = zip(*bar_ticks)
        ax.set_xticks(bar_xticks, labels=bar_labels, minor=is_minor, **chart.bar_foreach.label.kwargs)