from abc import ABC, abstractmethod
from typing import List, Dict
import pandas as pd
import warnings, yaml, json, csv, os
from dataclasses import dataclass, field, is_dataclass
import matplotlib.pyplot as plt


@dataclass
class Extractor(ABC):

    file_regex: List[str] = field(default=None)

    @property
    def regex(self):
        if self.file_regex:
            return self.file_regex
        else:
            return self.file_regex_default()

    @property
    @abstractmethod
    def file_regex_default(self):
        pass

    @abstractmethod
    def extract(self, path: str, options: Dict) -> List[Dict]:
        pass

class Transformer(ABC):
    @abstractmethod
    def transform(self, df: pd.DataFrame, options: Dict) -> pd.DataFrame:
        pass

class Loader(ABC):
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


########################################################
# Extractors                                           #
########################################################

class YamlExtractor(Extractor):

    def file_regex_default(self):
        return ['.*\.yaml$', '.*\.yml$']

    def extract(self, path: str, options: Dict) -> List[Dict]:
       with open(path, 'r') as f:
           data = yaml.load(f)
       if not isinstance(data, list):
           data = [data]
       return data

class JsonExtractor(Extractor):

    def file_regex_default(self):
        return ['.*\.json$']

    def extract(self, path: str, options: Dict) -> List[Dict]:
        with open(path, 'r') as f:
            data = json.load(f)

        if not isinstance(data, list):
            data = [data]

        return data

class CsvExtractor(Extractor):

    def file_regex_default(self):
        return ['.*\.csv$']

    def extract(self, path: str, options: Dict) -> List[Dict]:
        data = []

        delimiter = options.get("delimiter", ",")
        has_header = options.get("has_header", True)
        fieldnames = options.get("fieldnames", None)

        with open(path, 'r') as f:

            if has_header or fieldnames is not None:
                reader = csv.DictReader(f, delimiter=delimiter, fieldnames=fieldnames)
            else:
                reader = csv.reader(f, delimiter=delimiter)
            for row in reader:
                data.append(row)

        return data


class ErrorExtractor(Extractor):

    def file_regex_default(self):
        return ['^stderr.log$']

    # if the file is present and not empty, then throws a warning
    def extract(self, path: str, options: Dict) -> List[Dict]:
        with open(path, 'r') as f:
            content = f.read().replace('\n', ' ')

        if content.strip() and not content.strip().isspace(): # ignore empty error files
            warnings.warn(f"found error file: {path}")
            warnings.warn(f"   {content}")
        return []


class IgnoreExtractor(Extractor):

    def file_regex_default(self):
        return ['^stdout.log$']

    # ignores a file
    def extract(self, path: str, options: Dict) -> List[Dict]:
        # ignore this file
        return []



########################################################
# Transformers                                         #
########################################################

class RepAggTransformer(Transformer):

    """
    Transformer to aggregate over the repetitions of the same experiment run.

    GroupBy all columns of df except `data_columns` and `rep` column.
    Afterward, apply specified aggregate functions `agg_functions` on the `data_columns`.
    """

    def transform(self, df: pd.DataFrame, options: Dict) -> pd.DataFrame:
        # TODO [nku] test and remove
        #return df
        if df.empty:
            return df

        data_columns = options.get("data_columns")

        ignore_columns = options.get("ignore_columns", [])

        agg_functions = options.get("agg_functions", ['mean', 'min', 'max', 'std', 'count'])

        if not set(data_columns).issubset(df.columns.values):
            raise ValueError(f"RepAggTransformer: data_columns={data_columns} must be in df_columns={df.columns.values}")

        # ensure that all data_columns are numbers
        df[data_columns] = df[data_columns].apply(pd.to_numeric)

        # we need to convert each column into a hashable type (list and dict are converted to string)
        hashable_types={}
        for col in df.columns:
            dtype = df[col].dtype
            if  dtype == "object":
                hashable_types[col] = "str"
            else:
                hashable_types[col] = dtype
        df = df.astype(hashable_types)

        # group_by all except `rep` and `data_columns`
        group_by_cols = [col for col in df.columns.values if col not in data_columns and col != "rep" and col not in ignore_columns]
        agg_d = {data_col: agg_functions for data_col in data_columns}
        df = df.groupby(group_by_cols).agg(agg_d).reset_index()

        # flatten columns
        df.columns = ["_".join(v) if v[1] else v[0] for v in df.columns.values]

        return df


class FactorAggTransformer(Transformer):

    """
    Transformer to aggregate over specified factors of the same experiment run.

    GroupBy `factor_columns` of df.
    Afterward, apply specified aggregate functions `agg_functions` on the `data_columns`.
    """

    def transform(self, df: pd.DataFrame, options: Dict) -> pd.DataFrame:
        # TODO [nku] test and remove
        #return df
        if df.empty:
            return df

        data_columns = options.get("data_columns")
        factor_columns = options.get("factor_columns")

        agg_functions = options.get("agg_functions", ['mean', 'min', 'max', 'std', 'count'])

        # custom agg functions
        custom_agg_methods_available = {
            "custom_tail": self.custom_tail
        }
        for fun in agg_functions.copy():
            for method, call in custom_agg_methods_available.items():
                if fun == method:
                    agg_functions.remove(fun) # is this allowed while in the loop?
                    agg_functions.append(call)


        if not set(data_columns).issubset(df.columns.values):
            return df
            # raise ValueError(f"RepAggTransformer: data_columns={data_columns} must be in df_columns={df.columns.values}")
        if not set(factor_columns).issubset(df.columns.values):
            raise ValueError(f"FactorAggTransformer: factor_columns={factor_columns} must be in df_columns={df.columns.values}")

        # ensure that all data_columns are numbers
        df[data_columns] = df[data_columns].apply(pd.to_numeric)

        # we need to convert each column into a hashable type (list and dict are converted to string)
        hashable_types={}
        for col in df.columns:
            dtype = df[col].dtype
            if  dtype == "object":
                hashable_types[col] = "str"
            else:
                hashable_types[col] = dtype
        df = df.astype(hashable_types)

        # group_by all except `rep` and `data_columns`
        group_by_cols = factor_columns
        agg_d = {data_col: agg_functions for data_col in data_columns}
        df = df.groupby(group_by_cols).agg(agg_d).reset_index()

        # flatten columns
        df.columns = ["_".join(v) if v[1] else v[0] for v in df.columns.values]

        return df

    def custom_tail(self, data):
        # print("data", data, data.tail(5).mean())
        return data.tail(5).mean()



########################################################
# Loaders                                              #
########################################################

class CsvSummaryLoader(Loader):
    def load(self, df: pd.DataFrame, options: Dict, etl_info: Dict) -> None:
        if df.empty:
            print("CsvSummaryLoader: DataFrame is empty so not creating an output file.")
        df.to_csv(os.path.join(etl_info["suite_dir"], f"{etl_info['pipeline']}.csv"))


class LatexTableLoader(Loader):
    """
    Prints dataframe as LaTeX table
    """
    def load(self, df: pd.DataFrame, options: Dict, etl_info: Dict) -> None:
        if df.empty:
            print("LatexTableLoader: DataFrame is empty so not creating an output file.")

        with open(os.path.join(etl_info["suite_dir"], f"{etl_info['pipeline']}.txt")) as file:
            df.to_latex(buf=file)
