from abc import ABC, abstractmethod
from typing import List, Dict

import pandas as pd
import os
import matplotlib.pyplot as plt



class Loader(ABC):

    # TODO [nku]: this is a breaking change
    #def get_output_dir(self, options, suite_dir, etl_output_dir=None):
    def get_output_dir(self, options, etl_info):

        suite_dir = etl_info["suite_dir"]
        etl_output_dir = etl_info["etl_output_dir"]

        output_dir_relative_to_suite_dir = bool(options.get("output_dir_relative_to_suite_dir", True))
        output_dir = options.get("output_dir")



        if output_dir is None:
            # put everything relative to `etl_output_dir`,` e.g., `etl_results`
            path = os.path.join(suite_dir, etl_output_dir) if etl_output_dir is not None else suite_dir
        elif output_dir_relative_to_suite_dir:
             # put everything relative to `etl_output_dir` (if not None), e.g., `etl_results`
            path = os.path.join(suite_dir, etl_output_dir, output_dir) if etl_output_dir is not None else os.path.join(suite_dir, output_dir)
        else:
            path = output_dir

        if not os.path.exists(path):
            os.makedirs(path)

        return path


    @abstractmethod
    def load(self, df: pd.DataFrame, options: Dict, etl_info: Dict) -> None:
        pass


# TODO [nku] provide more default implementations for plot styling: [gray scheme vs color scheme, linestyles, figure size: square vs rectangle] -> how can we encapsulate this in a nice modular way?
# TODO [nku] maybe provide some really basic plots based on options: [lineplot, barchart]
class PlotLoader(Loader):

    def save_plot(self, fig: plt.Figure, filename: str, output_dir: str, use_tight_layout: bool = True, output_filetypes: List[str] = ['pdf', 'png']):
        for ext in output_filetypes:
            full_filename = f"{output_dir}/{filename}.{ext}"

            bbox_inches = 'tight' if (use_tight_layout and ext == 'pdf') else None
            pad_inches = 0 if (use_tight_layout and ext == 'pdf') else 0.1
            dpi = 300
            fig.savefig(full_filename, format=ext, bbox_inches=bbox_inches, pad_inches=pad_inches, dpi=dpi)



class CsvSummaryLoader(Loader):

    def load(self, df: pd.DataFrame, options: Dict, etl_info: Dict) -> None:
        if df.empty:
            print("CsvSummaryLoader: DataFrame is empty so not creating an output file.")
        output_dir = self.get_output_dir(options, etl_info)
        df.to_csv(os.path.join(output_dir, f"{etl_info['pipeline']}.csv"))


class LatexTableLoader(Loader):
    """
    Prints dataframe as LaTeX table
    """
    def load(self, df: pd.DataFrame, options: Dict, etl_info: Dict) -> None:
        if df.empty:
            print("LatexTableLoader: DataFrame is empty so not creating an output file.")

        with open(os.path.join(etl_info["suite_dir"], f"{etl_info['pipeline']}.txt"), 'w') as file:
            df.to_latex(buf=file)
