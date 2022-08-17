from abc import ABC, abstractmethod
from typing import Dict, Any

import pandas as pd

from doespy.etl.etl_util import expand_factors


class Transformer(ABC):
    @abstractmethod
    def transform(self, df: pd.DataFrame, options: Dict) -> pd.DataFrame:
        pass


class ConditionalTransformer(Transformer):
    def transform(self, df: pd.DataFrame, options: Dict) -> pd.DataFrame:
        # TODO [nku] docstring
        col = options["col"]
        value = options["value"]
        dest = options.get("dest", col)

        for cur, repl in value.items():
            df.loc[df[col] == cur, dest] = repl

        return df


class RepAggTransformer(Transformer):

    """
    Transformer to aggregate over the repetitions of the same experiment run.

    GroupBy all columns of df except `data_columns` and `rep` column.
    Afterward, apply specified aggregate functions
     `agg_functions` on the `data_columns`.
    """

    def transform(self, df: pd.DataFrame, options: Dict) -> pd.DataFrame:
        # TODO [nku] test and remove
        # return df
        if df.empty:
            return df

        data_columns = options.get("data_columns")

        ignore_columns = options.get("ignore_columns", [])

        agg_functions = options.get(
            "agg_functions", ["mean", "min", "max", "std", "count"]
        )

        if not set(data_columns).issubset(df.columns.values):
            raise ValueError(
                "RepAggTransformer: ",
                f"data_columns={data_columns} must be in df_columns={df.columns.values}"
            )

        # ensure that all data_columns are numbers
        df[data_columns] = df[data_columns].apply(pd.to_numeric)

        # we need to convert each column into a hashable type
        # (list and dict are converted to string)
        hashable_types = {}
        for col in df.columns:
            dtype = df[col].dtype
            if dtype == "object":
                hashable_types[col] = "str"
            else:
                hashable_types[col] = dtype
        df = df.astype(hashable_types)

        # group_by all except `rep` and `data_columns`
        group_by_cols = [
            col
            for col in df.columns.values
            if col not in data_columns and col != "rep" and col not in ignore_columns
        ]
        agg_d = {data_col: agg_functions for data_col in data_columns}
        df = df.groupby(group_by_cols).agg(agg_d).reset_index()

        # flatten columns
        df.columns = ["_".join(v) if v[1] else v[0] for v in df.columns.values]

        return df


class GroupByAggTransformer(Transformer):

    """
    Transformer to aggregate over specified factors of the same experiment run.

    GroupBy `groupby_columns` of df.
    Afterward, apply specified aggregate functions `agg_functions` on the `data_columns`
    """

    def transform(self, df: pd.DataFrame, options: Dict) -> pd.DataFrame:
        if df.empty:
            return df

        data_columns = options.get("data_columns")
        # here, we get factor_columns
        groupby_columns = expand_factors(df, options.get("groupby_columns"))
        agg_functions = options.get(
            "agg_functions", ["mean", "min", "max", "std", "count"]
        )

        # To configure size of the 'tail' to calculate the mean over
        custom_tail_length = options.get("custom_tail_length", 5)

        # custom agg functions
        custom_agg_methods_available = {
            "custom_tail": self.custom_tail_build(custom_tail_length)
        }
        for fun in agg_functions.copy():
            for method, call in custom_agg_methods_available.items():
                if fun == method:
                    agg_functions.remove(fun)  # is this allowed while in the loop?
                    agg_functions.append(call)

        if not set(data_columns).issubset(df.columns.values):
            return df
            # raise ValueError(f"RepAggTransformer: data_columns={data_columns}
            # must be in df_columns={df.columns.values}")
        if not set(groupby_columns).issubset(df.columns.values):
            raise ValueError(
                f"GroupByAggTransformer: groupby_columns={groupby_columns} "
                f"must be in df_columns={df.columns.values}"
            )

        # ensure that all data_columns are numbers
        df[data_columns] = df[data_columns].apply(pd.to_numeric)

        # we need to convert each column into a hashable type
        # (list and dict are converted to string)
        hashable_types = {}
        for col in df.columns:
            dtype = df[col].dtype
            if dtype == "object":
                hashable_types[col] = "str"
            else:
                hashable_types[col] = dtype
        df = df.astype(hashable_types)

        # group_by all except `rep` and `data_columns`
        group_by_cols = groupby_columns
        agg_d = {data_col: agg_functions for data_col in data_columns}
        df = df.groupby(group_by_cols, dropna=False).agg(agg_d).reset_index()

        # flatten columns
        df.columns = ["_".join(v) if v[1] else v[0] for v in df.columns.values]

        return df

    def custom_tail_build(self, custom_tail_length):
        def custom_tail(data):
            return data.tail(custom_tail_length).mean()

        return custom_tail


class FilterColumnTransformer(Transformer):
    # TODO []
    """
    Simple transformer to filter rows out of a dataframe by column values.

    Accepts key-value pairs in `filters` option.

    This transformer is simple for now, only accepts discrete values and
    does not do any type handling.
    Options:
        - filters: dict of filters
        - allow_empty_result: bool whether to throw an error when the dataframe
            becomes empty as result of the filter.
            Defaults to False.
    """

    def transform(self, df: pd.DataFrame, options: Dict) -> pd.DataFrame:

        import warnings

        warnings.warn(
            "FilterColumnTransformer is deprecated, instead you can directly use",
            "df.query(col == 'A') in the etl definition ",
            "i.e., transformers: [df.query: {expr: col == 'A'}]",
            DeprecationWarning,
        )

        filters: dict[str, Any] = options.get("filters", {})
        allow_empty_result: bool = options.get("allow_empty_result", False)

        if len(filters.keys()) == 0:
            return df
        if not set(filters.keys()).issubset(df.columns.values):
            raise ValueError(
                f"FilterColumnTransformer: filters={filters.keys()}",
                f"must be in df_columns={df.columns.values}"
            )

        for key, value in filters.items():
            df = df[df[key] == value]

        if df.empty and not allow_empty_result:
            raise ValueError(
                "FilterColumnTransformer: resulting dataframe after filters is empty!",
                "This is probably not supposed to happen"
            )
        return df
