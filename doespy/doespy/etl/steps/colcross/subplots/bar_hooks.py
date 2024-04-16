from doespy.etl.steps.colcross.components import AxisConfig, Metric, axis_formatter
from doespy.etl.steps.colcross.hooks import default_hooks
import gossip
import typing
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from enum import Enum

from matplotlib import pyplot as plt


class BarHooks(str, Enum):

    SubplotPre = "BarSubplotPre"

    ArtistPre = "BarArtistPre"

    ArtistPost = "BarArtistPost"

    SubplotPost = "BarSubplotPost"


##################################


# TODO [nku] for each can write a docstring to explain the arguments
@default_hooks.register(BarHooks.SubplotPre)
def demo(
    ax: plt.Axes,
    df_subplot: pd.DataFrame,
    subplot_id: Dict[str, typing.Any],
    metric: Metric,
    plot_config,
    subplot_config,
    chart,
):
    # nop hook
    pass


@default_hooks.register(BarHooks.ArtistPre)
def demo(
    ax: plt.Axes,
    part_value: float,
    part_error: Optional[float],
    position,
    bar_part_id: Dict[str, typing.Any],
    bar_part_config: Dict[str, typing.Any],
    metric: Metric,
    plot_config,
    subplot_config,
    chart,
):
    # nop hook
    pass


@default_hooks.register(BarHooks.ArtistPost)
def demo(
    ax: plt.Axes,
    part_value: float,
    part_error: Optional[float],
    position,
    bar_part_id: Dict[str, typing.Any],
    bar_part_config: Dict[str, typing.Any],
    metric: Metric,
    plot_config,
    subplot_config,
    chart,
):
    # nop hook
    pass


@default_hooks.register(BarHooks.SubplotPost)
def demo(
    ax: plt.Axes,
    df_subplot: pd.DataFrame,
    subplot_id: Dict[str, typing.Any],
    metric: Metric,
    plot_config,
    subplot_config,
    chart,
    group_ticks: List[Tuple[float, str]],
    bar_ticks: List[Tuple[float, str]],
):
    # nop hook
    pass


######################################


@default_hooks.register(BarHooks.SubplotPost)
def group_bar_ticks(
    ax: plt.Axes,
    df_subplot: pd.DataFrame,
    subplot_id: Dict[str, typing.Any],
    metric: Metric,
    plot_config,
    subplot_config,
    chart,
    group_ticks: List[Tuple[float, str]],
    bar_ticks: List[Tuple[float, str]],
):
    if group_ticks:
        group_xticks, group_labels = zip(*group_ticks)
        ax.set_xticks(
            group_xticks, labels=group_labels, **chart.group_foreach.label.kwargs
        )

    if bar_ticks:
        is_minor = group_ticks
        inner_xticks, inner_labels = zip(*bar_ticks)
        kwargs = chart.bar_foreach.label.kwargs
        ax.set_xticks(inner_xticks, labels=inner_labels, minor=is_minor, **kwargs)
