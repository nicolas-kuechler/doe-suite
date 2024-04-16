import typing
from doespy.etl.steps.colcross.colcross import BaseColumnCrossPlotLoader, SubplotConfig
from doespy.etl.steps.colcross.hooks import CcpHooks

from typing import Dict, List, Union

import gossip
from matplotlib import pyplot as plt
import pandas as pd


class MyCustomSubplotConfig(SubplotConfig):

    # INFO: We extend the default config and add a new attribute
    watermark: str = None


class MyCustomColumnCrossPlotLoader(BaseColumnCrossPlotLoader):

    # INFO: We provide a custom subplot config that extends the default config
    #       and override it here
    cum_subplot_config: List[MyCustomSubplotConfig]

    def setup_handlers(self):
        """:meta private:"""

        # NOTE: We can unregister function by name for a hook if needed
        # for x in gossip.get_hook(CcpHooks.SubplotPostChart).get_registrations():
        #    if x.func.__name__ == "ax_title":
        #        x.unregister()

        # NOTE: We can unregister all registered functions for a hook if needed
        # gossip.get_hook(SubplotHooks.SubplotPostChart).unregister_all()

        # install the class specific hooks
        MyCustomColumnCrossPlotLoader.blueprint().install()



@MyCustomColumnCrossPlotLoader.blueprint().register(CcpHooks.SubplotPostChart)
def apply_watermark(
    ax: plt.Axes,
    df_subplot: pd.DataFrame,
    subplot_id: Dict[str, typing.Any],
    plot_config,
    subplot_config,
    loader,
):

   if subplot_config.watermark is not None:
       ax.text(0.5, 0.5, subplot_config.watermark, transform=ax.transAxes,
        fontsize=20, color='gray', alpha=0.5,
        ha='center', va='center', rotation=45)
