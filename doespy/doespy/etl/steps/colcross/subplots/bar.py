from doespy.etl.steps.colcross.components import (
    BasePlotConfig,
    ColsForEach,
    BaseSubplotConfig,
    Metric,
)
from doespy.etl.steps.colcross.subplots.bar_hooks import BarHooks
from matplotlib import pyplot as plt
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union

from doespy.design.etl_design import MyETLBaseModel
from dataclasses import dataclass

from pydantic import Field

import gossip


class GroupedStackedBarChart(MyETLBaseModel):

    group_foreach: ColsForEach = Field(default_factory=ColsForEach.empty)

    bar_foreach: ColsForEach

    part_foreach: ColsForEach = Field(default_factory=ColsForEach.empty)
    """
    "
    if part_foreach is None, i.e., default, then only the $metrics$ columns will be used as bar parts
    """

    bar_width: float = 0.6
    bar_padding: float = 0.0

    group_padding: float = 0.1

    @dataclass
    class BarPartPosition:

        group_center_pos: float

        bar_left_pos: float
        bar_center_pos: float

        bar_part_bottom: float

    def get_cols(self):
        return (
            self.group_foreach.get_cols()
            + self.bar_foreach.get_cols()
            + self.part_foreach.get_cols()
        )

    def plot(
        self,
        ax: plt.Axes,
        df1: pd.DataFrame,
        data_id: Dict[str, str],
        metric: Metric,
        subplot_config: BaseSubplotConfig,
        plot_config: BasePlotConfig,
    ):
        group_ticks = set()
        bar_ticks = set()

        gossip.trigger(
            BarHooks.SubplotPre,
            ax=ax,
            df_subplot=df1,
            subplot_id=data_id,
            metric=metric,
            plot_config=plot_config,
            subplot_config=subplot_config,
            chart=self,
        )

        for (
            part_value,
            part_error,
            position,
            bar_group_id,
            bar_id,
            bar_part_id,
        ) in self.for_each(df1, metric=metric, subplot_id=data_id):

            full_id = {**data_id, **bar_group_id, **bar_id, **bar_part_id}
            # print(f"{full_id=}")

            bar_part_config = subplot_config.artist_config(full_id, plot_config)

            # TODO [nku] for the printing, it would be nice to be able to generally format this as a tree
            print(f"          {bar_part_config=}")

            gossip.trigger(
                BarHooks.ArtistPre,
                ax=ax,
                part_value=part_value,
                part_error=part_error,
                position=position,
                bar_part_id=full_id,
                bar_part_config=bar_part_config,
                metric=metric,
                plot_config=plot_config,
                subplot_config=subplot_config,
                chart=self,
            )

            label = bar_part_config.pop("label", None)

            ax.bar(
                position.bar_center_pos,
                part_value,
                width=self.bar_width,
                label=label,
                yerr=part_error,
                bottom=position.bar_part_bottom,
                **bar_part_config,
            )

            gossip.trigger(
                BarHooks.ArtistPost,
                ax=ax,
                part_value=part_value,
                part_error=part_error,
                position=position,
                bar_part_id=full_id,
                bar_part_config=bar_part_config,
                metric=metric,
                plot_config=plot_config,
                subplot_config=subplot_config,
                chart=self,
            )

            # keep track of the labels for each artist
            if self.group_foreach.label is not None:
                group_lbl = self.group_foreach.label.apply(
                    {**data_id, **bar_group_id},
                    subplot_config=subplot_config,
                    info="group_label",
                )
                group_ticks.add((position.group_center_pos, group_lbl))

            if self.bar_foreach.label is not None:
                bar_lbl = self.bar_foreach.label.apply(
                    {**data_id, **bar_group_id, **bar_id},
                    subplot_config=subplot_config,
                    info="bar_label",
                )
                bar_ticks.add((position.bar_center_pos, bar_lbl))

        gossip.trigger(
            BarHooks.SubplotPost,
            ax=ax,
            df_subplot=df1,
            subplot_id=data_id,
            metric=metric,
            plot_config=plot_config,
            subplot_config=subplot_config,
            chart=self,
            group_ticks=group_ticks,
            bar_ticks=bar_ticks,
        )

    def for_each(self, df1: pd.DataFrame, metric: Metric, subplot_id: Dict[str, str]):

        bar_left_pos, bar_center_pos, group_center_pos = calc_positions(
            group_foreach=self.group_foreach,
            inner_foreach=self.bar_foreach,
            df1=df1,
            subplot_id=subplot_id,
            inner_width=self.bar_width,
            inner_padding=self.bar_padding,
            group_padding=self.group_padding,
        )

        i_bar = 0

        for i_group, df_bar_group, bar_group_id in self.group_foreach.for_each(
            df1, parent_id=subplot_id
        ):

            # TODO [nku] THE logging of id's is not very nice
            print(f"    group_id={bar_group_id}")

            for _i_bar, df_bar, bar_id in self.bar_foreach.for_each(
                df_bar_group, parent_id={**subplot_id, **bar_group_id}
            ):

                bottom = 0

                print(f"      bar_id={bar_id}")

                for _i_part, df_bar_part, part_id in self.part_foreach.for_each(
                    df_bar, parent_id={**subplot_id, **bar_group_id, **bar_id}
                ):

                    if len(df_bar_part) < 1:
                        continue

                    assert (
                        len(df_bar_part) == 1
                    ), f"Dataframe must have only one row to be used as a bar part by columns  (df={df_bar_part})  ({bar_group_id=}, {bar_id=}, {part_id=})"

                    error_cols = (
                        metric.error_cols
                        if metric.error_cols is not None
                        else [None] * len(metric.value_cols)
                    )

                    for value_col, error_col in zip(
                        metric.value_cols, error_cols, strict=True
                    ):

                        bar_part_id = {
                            **part_id,
                            "value_col": value_col,
                            "error_col": error_col,
                        }

                        part_value = df_bar_part[value_col].iloc[0]
                        part_error = (
                            df_bar_part[error_col].iloc[0]
                            if error_col is not None
                            else None
                        )

                        position = GroupedStackedBarChart.BarPartPosition(
                            group_center_pos=group_center_pos[i_group],
                            bar_left_pos=bar_left_pos[i_bar],
                            bar_center_pos=bar_center_pos[i_bar],
                            bar_part_bottom=bottom,
                        )

                        bottom += part_value

                        print(f"        part_id={bar_part_id}")

                        yield part_value, part_error, position, bar_group_id, bar_id, bar_part_id

                i_bar += 1


def calc_positions(
    group_foreach: ColsForEach,
    inner_foreach: ColsForEach,
    df1: pd.DataFrame,
    subplot_id: Dict[str, str],
    inner_width: float,
    inner_padding: float,
    group_padding: float,
):

    # positioning
    bar_info = []  # [3, 2, 3] -> 3 bars in first group, 2 in second, 3 in third

    inner_center_pos = []
    group_center_pos = []  # the center of each group

    pos = 0

    for _i_group, df_bar_group, bar_group_id in group_foreach.for_each(
        df1, parent_id=subplot_id
    ):
        n_inner_per_group = 0

        group_start_pos = pos
        group_end_pos = pos

        for _i_inner, _df_inner, _inner_id in inner_foreach.for_each(
            df_bar_group, parent_id={**subplot_id, **bar_group_id}
        ):
            n_inner_per_group += 1

            inner_center_pos.append(pos)
            group_end_pos = pos
            pos += inner_width + inner_padding

        # [2, 2.5, 3, 3.5] => 5.5 / 2 = 2.75
        # [2, 2.5, 3, 3.5, 4] => 6 / 2 = 3
        group_center_pos.append((group_start_pos + group_end_pos) / 2)

        pos += group_padding

        bar_info.append(n_inner_per_group)

    inner_left_pos = [
        x - inner_width / 2 for x in inner_center_pos
    ]  # + self.bar_width / 2

    return inner_left_pos, inner_center_pos, group_center_pos
