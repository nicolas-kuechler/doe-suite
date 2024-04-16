from doespy.etl.steps.colcross.base import BasePlotConfig, BaseSubplotConfig
from doespy.etl.steps.colcross.components import (
    ColsForEach,
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
    """Generate an indiviudal group (of boxes) for each unique combination of values found within the given columns.

    If missing, then only a single group is formed (i.e., no groups).

    .. code-block:: yaml
       :caption: Example

        group_foreach:
          cols: [col1, col2] # create a group for each unique combination of values in col1 and col2
          jp_except: "(col1 == 'A') && (col2 == 'B')"  # optional: exclude specific combinations
    """


    box_foreach: ColsForEach
    """Within a group (of boxes), generate a box for each unique combination of values found within the given columns.

    .. code-block:: yaml
       :caption: Example

        box_foreach:
          cols: [col3, col4] # create a box for each unique combination of values in col3 and col4
          # optional: exclude specific combinations (can also use cols from group_foreach, fig_foreach, etc.)
          jp_except: "(col1 == 'A') && (col3 == 'B')"
    """

    part_foreach: ColsForEach = Field(default_factory=ColsForEach.empty)
    """Create multiple boxes in the same x-axis position for each unique combination of values found within the given columns.
    In addition, the columns of the ``Metric`` (i.e., $metrics$) will also result in multiple parts.

    If missing, only the ``Metric`` columns will be used.
    If the ``Metric`` only has a single column and ``part_foreach`` is missing, then a single box (per-x-axis position) is created.

    .. code-block:: yaml
       :caption: Example

       # the columns under metrics also result in parts

        part_foreach:
          cols: [col5, col6] # create a box part for each unique combination of values in col5 and col6
          # optional: exclude specific combinations (can also use cols from group_foreach, box_foreach, etc.)
          jp_except: "(col1 == 'A') && (col5 == 'B')"
    """

    box_width: float = 0.6
    """The width of each box."""

    box_padding: float = 0.0
    """The space between boxes within a group."""

    group_padding: float = 0.1
    """The space between groups."""

    @dataclass
    class Position:
        """:meta private:"""
        group_center_pos: float
        box_left_pos: float
        box_center_pos: float

    def get_cols(self):
        """:meta private:"""
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
        """:meta private:"""
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
        """:meta private:"""

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
