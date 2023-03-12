from typing import Dict

import matplotlib.pyplot as plt
import pandas as pd
from doespy.etl.steps.loaders import PlotLoader


class DemoLatencyPlotLoader(PlotLoader):
    def load(self, df: pd.DataFrame, options: Dict, etl_info: Dict) -> None:
        if not df.empty:
            fig = self.plot(df)
            output_dir = self.get_output_dir(etl_info)

            self.save_plot(fig, filename="test", output_dir=output_dir)

    def plot(self, df):

        # for a single entry the std is NaN
        df["latency_std"].fillna(0, inplace=True)

        scale_factor = 2.4
        figsize = [
            scale_factor * 1.618,
            scale_factor * 1,
        ]  # [width, height] based on golden ratio
        fig = plt.figure(figsize=figsize, dpi=100)

        plt.figure(fig.number)

        plt.ylabel("Latency [sec]", labelpad=0)
        plt.xlabel("Payload Size [MB]")

        df_opt = df[df["opt"]]
        df_no_opt = df[df["opt"] == False]  # noqa: E712

        if not df_opt.empty:

            plt.errorbar(
                x=df_opt["payload_size_mb"],
                y=df_opt["latency_mean"],
                yerr=df_opt["latency_std"],
                label="w/ opt",
                capsize=5,
                marker=".",
            )

        if not df_no_opt.empty:
            plt.errorbar(
                x=df_no_opt["payload_size_mb"],
                y=df_no_opt["latency_mean"],
                yerr=df_no_opt["latency_std"],
                label="w/o opt",
                capsize=5,
                marker=".",
            )

        plt.legend()

        return fig


class CoordinateLoader(PlotLoader):
    def load(self, df: pd.DataFrame, options: Dict, etl_info: Dict) -> None:
        if not df.empty:
            fig = self.plot(df)
            output_dir = self.get_output_dir(etl_info)
            self.save_plot(
                fig,
                filename=f"{etl_info['pipeline']}_coord",
                output_dir=output_dir,
                output_filetypes=["png"],
            )

    def plot(self, df):
        fig = self.default_fig()
        plt.scatter(df["x"], df["y"], c=df["color"], alpha=0.3)
        return fig
