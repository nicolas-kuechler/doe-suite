from doespy.etl.steps.colcross.components import AxisConfig, Metric, axis_formatter
from doespy.etl.steps.colcross.hooks import default_hooks
import gossip
import typing
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from enum import Enum

from matplotlib import pyplot as plt


class BoxHooks(str, Enum):

    SubplotPre = "BoxSubplotPre"

    ArtistPre = "BoxArtistPre"

    ArtistPost = "BoxArtistPost"

    SubplotPost = "BoxSubplotPost"


##################################


# TODO [nku] for each can write a docstring to explain the arguments
@default_hooks.register(BoxHooks.SubplotPre)
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


@default_hooks.register(BoxHooks.ArtistPre)
def demo(
    ax: plt.Axes,
    part_values: List[float],
    position,
    box_id: Dict[str, typing.Any],
    box_config: Dict[str, typing.Any],
    metric: Metric,
    plot_config,
    subplot_config,
    chart,
):
    # nop hook
    pass


@default_hooks.register(BoxHooks.ArtistPost)
def demo(
    ax: plt.Axes,
    part_values: List[float],
    position,
    box_id: Dict[str, typing.Any],
    box_config: Dict[str, typing.Any],
    metric: Metric,
    plot_config,
    subplot_config,
    chart,
):
    # nop hook
    pass


@default_hooks.register(BoxHooks.SubplotPost)
def demo(
    ax: plt.Axes,
    df_subplot: pd.DataFrame,
    subplot_id: Dict[str, typing.Any],
    metric: Metric,
    plot_config,
    subplot_config,
    chart,
    group_ticks: List[Tuple[float, str]],
    box_ticks: List[Tuple[float, str]],
):
    # nop hook
    pass


######################################


@default_hooks.register(BoxHooks.SubplotPost)
def group_box_ticks(
    ax: plt.Axes,
    df_subplot: pd.DataFrame,
    subplot_id: Dict[str, typing.Any],
    metric: Metric,
    plot_config,
    subplot_config,
    chart,
    group_ticks: List[Tuple[float, str]],
    box_ticks: List[Tuple[float, str]],
):
    if group_ticks:
        group_xticks, group_labels = zip(*group_ticks)
        ax.set_xticks(
            group_xticks, labels=group_labels, **chart.group_foreach.label.kwargs
        )

    if box_ticks:
        is_minor = group_ticks
        inner_xticks, inner_labels = zip(*box_ticks)
        kwargs = chart.box_foreach.label.kwargs
        ax.set_xticks(inner_xticks, labels=inner_labels, minor=is_minor, **kwargs)
