from abc import ABC, abstractmethod
from typing import List, Dict

import pandas as pd
import os
import matplotlib.pyplot as plt
import inspect
import sys
from typing import Optional

from pydantic import BaseModel

class Loader(BaseModel, ABC):
    class Config:
        extra = "forbid"

    def get_output_dir(self, etl_info):

        etl_output_dir = etl_info["etl_output_dir"]

        if not os.path.exists(etl_output_dir):
            os.makedirs(etl_output_dir)

        return etl_output_dir

    @abstractmethod
    def load(self, df: pd.DataFrame, options: Dict, etl_info: Dict) -> None:
        # NOTE: Extending classes should not use the `options: Dict` and instead use instance variables for parameters

        pass


# TODO [nku] provide more default implementations for plot styling:
#  [gray scheme vs color scheme, linestyles, figure size: square vs rectangle]
#  -> how can we encapsulate this in a nice modular way?
# TODO [nku] maybe provide some really basic plots based on options:
#  [lineplot, barchart]
class PlotLoader(Loader):

    def save_data(self, df: pd.DataFrame, filename: str, output_dir: str, output_filetypes: List[str] = ["html"]):
        os.makedirs(output_dir, exist_ok=True)

        for ext in output_filetypes:
            if ext == "html":
                html_table = df.to_html()
                path = os.path.join(output_dir, f"{filename}.html")

                with open(path, 'w') as file:
                    file.write(html_table)
            else:
                raise ValueError(f"PlotLoader: Unknown file type {ext}")


    def save_plot(
        self,
        fig: plt.Figure,
        filename: str,
        output_dir: str,
        use_tight_layout: bool = True,
        output_filetypes: List[str] = ["pdf", "png"],
    ):

        os.makedirs(output_dir, exist_ok=True)


        for ext in output_filetypes:
            full_filename = f"{output_dir}/{filename}.{ext}"

            bbox_inches = "tight" if (use_tight_layout and ext == "pdf") else None
            pad_inches = 0 if (use_tight_layout and ext == "pdf") else 0.1
            dpi = 300
            fig.savefig(
                full_filename,
                format=ext,
                bbox_inches=bbox_inches,
                pad_inches=pad_inches,
                dpi=dpi,
            )

    def default_fig(self):
        scale_factor = 2.4
        figsize = [
            scale_factor * 1.618,
            scale_factor * 1,
        ]  # [width, height] based on golden ratio
        fig = plt.figure(figsize=figsize, dpi=100)
        plt.figure(fig.number)
        return fig


class CsvSummaryLoader(Loader):

    skip_empty: bool = False

    r"""The `CsvSummaryLoader` creates a CSV file of the data frame from the `Transformer` stage.

    :param skip_empty: ignore empty df.

    .. code-block:: yaml
       :caption: Example ETL Pipeline Design

        $ETL$:
            loaders:
                CsvSummaryLoader: {}     # with default output dir
                CsvSummaryLoader:        # with skip empty df
                    skip_empty: True
    """

    def load(self, df: pd.DataFrame, options: Dict, etl_info: Dict) -> None:

        if self.skip_empty and df.empty:
            return
        elif df.empty:
            raise ValueError("CsvSummaryLoader: DataFrame is empty so not creating an output file.")
        else:
            output_dir = self.get_output_dir(etl_info)
            df.to_csv(os.path.join(output_dir, f"{etl_info['pipeline']}.csv"))


class PickleSummaryLoader(Loader):

    skip_empty: bool = False

    r"""The `PickleSummaryLoader` creates a Pickle file of the data frame from the `Transformer` stage.

    :param skip_empty: ignore empty df.

    .. code-block:: yaml
       :caption: Example ETL Pipeline Design

        $ETL$:
            loaders:
                PickleSummaryLoader: {}     # with default output dir
                PickleSummaryLoader:        # with skip empty dir
                    skip_empty: True
    """

    def load(self, df: pd.DataFrame, options: Dict, etl_info: Dict) -> None:

        if self.skip_empty and df.empty:
            return
        elif df.empty:
            raise ValueError("PickleSummaryLoader: DataFrame is empty so not creating an output file.")
        else:
            output_dir = self.get_output_dir(etl_info)
            df.to_pickle(os.path.join(output_dir, f"{etl_info['pipeline']}.pkl"))


class LatexTableLoader(Loader):

    r"""The `LatexTableLoader` creates a tex file of the data frame from the `Transformer` stage formatted as a Latex table.

    :param output_dir: path relative to the etl output directory to store the csv.

    .. code-block:: yaml
       :caption: Example ETL Pipeline Design

        $ETL$:
            loaders:
                LatexTableLoader: {}     # with default output dir
                LatexTableLoader:        # with custom output dir
                    output_dir: dir1
    """

    def load(self, df: pd.DataFrame, options: Dict, etl_info: Dict) -> None:
        if df.empty:
            print(
                "LatexTableLoader: DataFrame is empty so not creating an output file."
            )

        output_dir = self.get_output_dir(etl_info)
        with open(
            os.path.join(output_dir, f"{etl_info['pipeline']}.tex"), "w"
        ) as file:
            df.to_latex(buf=file)

__all__ = [name for name, cl in inspect.getmembers(sys.modules[__name__], inspect.isclass) if name!="Loader" and issubclass(cl, Loader) ]