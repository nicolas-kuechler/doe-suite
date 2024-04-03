from doespy.etl.steps.colcross.components import (
    BasePlotConfig,
    ColsForEach,
    BaseSubplotConfig,
    Metric,
)
from doespy.etl.steps.colcross.subplots.bar import calc_positions
from doespy.etl.steps.colcross.subplots.box_hooks import BoxHooks
from matplotlib import pyplot as plt
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union

from doespy.design.etl_design import MyETLBaseModel
from dataclasses import dataclass

from pydantic import Field

import gossip


class GroupedBoxplotChart(MyETLBaseModel):

    group_foreach: ColsForEach = Field(default_factory=ColsForEach.empty)

    box_foreach: ColsForEach

    part_foreach: ColsForEach = Field(default_factory=ColsForEach.empty)

    box_width: float = 0.6
    box_padding: float = 0.0

    group_padding: float = 0.1

    @dataclass
    class Position:
        group_center_pos: float
        box_left_pos: float
        box_center_pos: float

    def get_cols(self):
        return (
            self.group_foreach.get_cols()
            + self.box_foreach.get_cols()
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
        box_ticks = set()

        gossip.trigger(
            BoxHooks.SubplotPre,
            ax=ax,
            df_subplot=df1,
            subplot_id=data_id,
            metric=metric,
            plot_config=plot_config,
            subplot_config=subplot_config,
            chart=self,
        )

        for part_values, position, box_group_id, box_id, box_part_id in self.for_each(
            df1, metric=metric, subplot_id=data_id
        ):

            full_id = {**data_id, **box_group_id, **box_id, **box_part_id}

            box_config = subplot_config.artist_config(full_id, plot_config)

            gossip.trigger(
                BoxHooks.ArtistPre,
                ax=ax,
                part_values=part_values,
                position=position,
                box_id=full_id,
                box_config=box_config,
                metric=metric,
                plot_config=plot_config,
                subplot_config=subplot_config,
                chart=self,
            )

            label = box_config.pop("label", None)

            ax.boxplot(
                x=part_values,
                positions=[position.box_center_pos],
                widths=[self.box_width],
                labels=[label],
                **box_config,
            )

            gossip.trigger(
                BoxHooks.ArtistPost,
                ax=ax,
                part_values=part_values,
                position=position,
                box_id=full_id,
                box_config=box_config,
                metric=metric,
                plot_config=plot_config,
                subplot_config=subplot_config,
                chart=self,
            )

            # keep track of the labels for each artist
            if self.group_foreach.label is not None:
                group_lbl = self.group_foreach.label.apply(
                    {**data_id, **box_group_id},
                    subplot_config=subplot_config,
                    info="group_label",
                )
                group_ticks.add((position.group_center_pos, group_lbl))

            if self.box_foreach.label is not None:
                box_lbl = self.box_foreach.label.apply(
                    {**data_id, **box_group_id, **box_id},
                    subplot_config=subplot_config,
                    info="box_label",
                )
                box_ticks.add((position.box_center_pos, box_lbl))

        gossip.trigger(
            BoxHooks.SubplotPost,
            ax=ax,
            df_subplot=df1,
            subplot_id=data_id,
            metric=metric,
            plot_config=plot_config,
            subplot_config=subplot_config,
            chart=self,
            group_ticks=group_ticks,
            box_ticks=box_ticks,
        )

    def for_each(self, df1: pd.DataFrame, metric: Metric, subplot_id: Dict[str, str]):

        assert (
            metric.error_cols is None
        ), f"BoxplotChart: cannot have error cols in {metric=}"

        box_left_pos, box_center_pos, group_center_pos = calc_positions(
            group_foreach=self.group_foreach,
            inner_foreach=self.box_foreach,
            df1=df1,
            subplot_id=subplot_id,
            inner_width=self.box_width,
            inner_padding=self.box_padding,
            group_padding=self.group_padding,
        )

        i_box = 0

        for i_group, df_box_group, box_group_id in self.group_foreach.for_each(
            df1, parent_id=subplot_id
        ):

            print(f"    group_id={dict(**subplot_id, **box_group_id)}")

            for _i_box, df_box, box_id in self.box_foreach.for_each(
                df_box_group, parent_id={**subplot_id, **box_group_id}
            ):

                for _i_part, df_box_part, part_id in self.part_foreach.for_each(
                    df_box, parent_id={**subplot_id, **box_group_id, **box_id}
                ):

                    for value_col in metric.value_cols:

                        box_part_id = {**part_id, "value_col": value_col}

                        part_values = df_box_part[value_col]

                        position = GroupedBoxplotChart.Position(
                            group_center_pos=group_center_pos[i_group],
                            box_left_pos=box_left_pos[i_box],
                            box_center_pos=box_center_pos[i_box],
                        )

                        yield part_values, position, box_group_id, box_id, box_part_id

                i_box += 1
