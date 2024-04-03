from doespy.etl.steps.colcross.components import AxisConfig, axis_formatter
import gossip
import typing
from typing import Dict, List

import numpy as np
import pandas as pd
from enum import Enum

from matplotlib import pyplot as plt

from gossip import Blueprint
from matplotlib.ticker import FuncFormatter


default_hooks = Blueprint()


class CcpHooks(str, Enum):

    DataPreMetrics = "DataPreMetrics"
    DataPreFilter = "DataPreFilter"
    DataPreGroup = "DataPreGroup"

    FigPreInit = "FigPreInit"
    FigPreGroup = "FigPreGroup"

    SubplotPreConfigMerge = "SubplotPreConfigMerge"
    SubplotPreChart = "SubplotPreChart"
    SubplotPostChart = "SubplotPostChart"

    FigPost = "FigPost"


##############################


# TODO [nku] for each can write a docstring to explain the arguments
@default_hooks.register(CcpHooks.DataPreMetrics)
def demo(df: pd.DataFrame, loader):
    # nop hook
    pass


@default_hooks.register(CcpHooks.DataPreFilter)
def demo(df: pd.DataFrame, loader):
    # nop hook
    pass


@default_hooks.register(CcpHooks.DataPreGroup)
def demo(df: pd.DataFrame, loader):
    # nop hook
    pass


@default_hooks.register(CcpHooks.FigPreInit)
def demo(df_plot: pd.DataFrame, plot_id: Dict[str, typing.Any], loader):
    # nop hook
    pass


@default_hooks.register(CcpHooks.FigPreGroup)
def demo(
    fig: plt.Figure,
    axs: List[List[plt.Axes]],
    df_plot: pd.DataFrame,
    plot_id: Dict[str, typing.Any],
    plot_config,
    loader,
):
    # nop hook
    pass


@default_hooks.register(CcpHooks.SubplotPreConfigMerge)
def demo(
    df_subplot: pd.DataFrame,
    subplot_id: Dict[str, typing.Any],
    plot_config,
    cum_subplot_config: List,
    loader,
):
    # nop hook
    # can be used to modify `cum_subplot_config` before it's merged into `subplot_config`
    pass


@default_hooks.register(CcpHooks.SubplotPreChart)
def demo(
    ax: plt.Axes,
    df_subplot: pd.DataFrame,
    subplot_id: Dict[str, typing.Any],
    plot_config,
    subplot_config,
    loader,
):
    # nop hook
    pass


@default_hooks.register(CcpHooks.SubplotPostChart)
def demo(
    ax: plt.Axes,
    df_subplot: pd.DataFrame,
    subplot_id: Dict[str, typing.Any],
    plot_config,
    subplot_config,
    loader,
):
    # nop hook
    pass


@default_hooks.register(CcpHooks.FigPost)
def demo(
    fig: plt.Figure,
    axs: List[List[plt.Axes]],
    df_plot: pd.DataFrame,
    plot_id: Dict[str, typing.Any],
    plot_config,
    loader,
):
    # nop hook
    pass


#################################


@default_hooks.register(CcpHooks.SubplotPostChart)
def ax_title(ax, df_subplot, subplot_id, plot_config, subplot_config, loader):
    if subplot_config.ax_title is not None:

        title = subplot_config.ax_title.apply(
            subplot_id, subplot_config=subplot_config, info="ax_title"
        )
        ax.set_title(title)


@default_hooks.register(CcpHooks.SubplotPostChart)
def ax_legend(ax, df_subplot, subplot_id, plot_config, subplot_config, loader):
    if subplot_config.legend_ax is not None:

        handles, labels = ax.get_legend_handles_labels()

        # remove duplicates
        unique = [
            (h, l)
            for i, (h, l) in enumerate(zip(handles, labels))
            if l not in labels[:i]
        ]

        ax.legend(*zip(*unique), **subplot_config.legend_ax.kwargs)


@default_hooks.register(CcpHooks.SubplotPostChart)
def axis(ax, df_subplot, subplot_id, plot_config, subplot_config, loader):

    xcfg = AxisConfig() if subplot_config.xaxis is None else subplot_config.xaxis
    ycfg = AxisConfig() if subplot_config.yaxis is None else subplot_config.yaxis

    # scale
    if xcfg.scale is not None:
        ax.set_xscale(xcfg.scale)

    if ycfg.scale is not None:
        ax.set_yscale(ycfg.scale)

    # label
    if xcfg.label is not None:
        label = xcfg.label.apply(
            subplot_id, subplot_config=subplot_config, info="xaxis.label"
        )
        ax.set_xlabel(label)

    if ycfg.label is not None:
        label = ycfg.label.apply(
            subplot_id, subplot_config=subplot_config, info="yaxis.label"
        )
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
    if xcfg.tick_params is not None:
        if not isinstance(xcfg.tick_params, list):
            xcfg.tick_params = [xcfg.tick_params]
        for tp in xcfg.tick_params:
            ax.tick_params(**tp)

    if ycfg.tick_params is not None:
        if not isinstance(ycfg.tick_params, list):
            ycfg.tick_params = [ycfg.tick_params]
        for tp in ycfg.tick_params:
            ax.tick_params(**tp)

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


@default_hooks.register(CcpHooks.FigPost)
def fig_legend(fig, axs, df_plot, plot_id, plot_config, loader):

    if plot_config is not None and plot_config.legend_fig is not None:

        # collect lables and handles from subplots
        fig_handles, fig_labels = [], []
        for ax in axs.flat:
            handles, labels = ax.get_legend_handles_labels()
            fig_handles += handles
            fig_labels += labels

        # remove duplicates
        unique = [
            (h, l)
            for i, (h, l) in enumerate(zip(fig_handles, fig_labels))
            if l not in fig_labels[:i]
        ]

        fig.legend(*zip(*unique), **plot_config.legend_fig.kwargs)
