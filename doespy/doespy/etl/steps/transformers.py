from abc import ABC, abstractmethod
from typing import Dict, Any, List

import pandas as pd
import inspect
import sys

from pydantic import BaseModel, validator

import pandas as pd

from doespy.etl.etl_util import expand_factors


class Transformer(BaseModel, ABC):

    name: str = None

    class Config:
        extra = "forbid"

    @validator("name", pre=True, always=True)
    def set_name(cls, value):
        return cls.__name__

    @abstractmethod
    def transform(self, df: pd.DataFrame, options: Dict) -> pd.DataFrame:

        # NOTE: Extending classes should not use the `options: Dict` and instead use instance variables for parameters

        pass


class DfTransformer(Transformer):

    def transform(self, df: pd.DataFrame, options: Dict) -> pd.DataFrame:

        # TODO [nku] here I could define the different things for the df.x -> at the moment unused
        pass

class ConditionalTransformer(Transformer):
    """
    The `ConditionalTransformer` replaces the value in the ``dest`` column with a
    value from the ``value`` dict, if the value in the ``col`` column is equal to the key.

    .. code-block:: yaml
       :caption: Example ETL Pipeline Design

        $ETL$:
            transformers:
              - name: ConditionalTransformer:
                col: Country
                dest: Code
                value:
                    Switzerland: CH
                    Germany: DE

    Example

    .. container:: twocol

        .. container:: leftside

            ============  ====
            Country       Code
            ============  ====
            Germany
            Switzerland
            France
            ============  ====

        .. container:: middle

            |:arrow_right:|

        .. container:: rightside

            ============  ====
            Country       Code
            ============  ====
            Germany       DE
            Switzerland   CH
            France
            ============  ====

    """

    col: str
    """Name of condition column in data frame."""

    dest: str
    """Name of destination column in data frame."""

    value: Dict[Any, Any]
    """Dictionary of replacement rules:
        The dict key is the entry in the condition ``col`` and
        the value is the replacement used in the ``dest`` column."""


    def transform(self, df: pd.DataFrame, options: Dict) -> pd.DataFrame:

        col = self.col
        value = self.value
        dest = self.dest

        for cur, repl in value.items():
            df.loc[df[col] == cur, dest] = repl

        return df


class RepAggTransformer(Transformer):

    r"""The `RepAggTransformer` aggregates over the repetitions of the same experiment run.
    GroupBy all columns of df except ``data_columns`` and ``rep`` column.
    Afterward, apply specified aggregate functions ``agg_functions`` on the ``data_columns``.

    :param ignore_columns: List of columns to ignore within group_by condition (apart from repetition column ``rep``), defaults to ``[]``

    :param data_columns: The columns that contain the data to aggregate, see ``agg_function``.

    :param agg_functions: List of aggregate function to apply on ``data_columns``, defaults to ``["mean", "min", "max", "std", "count"]``

    .. code-block:: yaml
       :caption: Example ETL Pipeline Design

        $ETL$:
            transformers:
              - name: RepAggTransformer:
                ignore_columns: [$CMD$]
                data_columns: [Lat]
                agg_functions: [mean]

    Example

    .. container:: twocol

        .. container:: leftside

            ===  ==== === ===== ===
            Run  ...  Rep $CMD$ Lat
            ===  ==== === ===== ===
            0         0   xyz   0.1
            0         1   xyz   0.3
            1         0   xyz   0.5
            1         1   xyz   0.5
            ===  ==== === ===== ===

        .. container:: middle

            |:arrow_right:|

        .. container:: rightside

            ===  ==== ========
            Run  ...  Lat_mean
            ===  ==== ========
            0         0.2
            1         0.5
            ===  ==== ========

    """

    ignore_columns: List[str] = []

    data_columns: List[str]

    agg_functions: List[str] = ["mean", "min", "max", "std", "count"]

    # TODO [nku] can we remove this transformer by unifying it with GroupByAggTransformer? -> I think we could remove this here and replace it only with the GroupByAggTransformer and include rep in Groupby cols

    def transform(self, df: pd.DataFrame, options: Dict) -> pd.DataFrame:
        if df.empty:
            return df

        data_columns = self.data_columns

        ignore_columns = self.ignore_columns

        agg_functions = self.agg_functions

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
    The `GroupByAggTransformer` performs a group by followed
    by a set of aggregate functions applied to the ``data_columns``.

    .. code-block:: yaml
       :caption: Example ETL Pipeline Design

        $ETL$:
            transformers:
              - name: GroupByAggTransformer:
                groupby_columns: [Run, $FACTORS$]
                data_columns: [Lat]
                agg_functions: [mean]

    Example

    .. container:: twocol

        .. container:: leftside

            ===  ==== === ===== ===
            Run  ...  Rep $CMD$ Lat
            ===  ==== === ===== ===
            0         0   xyz   0.1
            0         1   xyz   0.3
            1         0   xyz   0.5
            1         1   xyz   0.5
            ===  ==== === ===== ===

        .. container:: middle

            |:arrow_right:|

        .. container:: rightside

            ===  ==== ========
            Run  ...  Lat_mean
            ===  ==== ========
            0         0.2
            1         0.5
            ===  ==== ========

    """

    data_columns: List[str]
    """ The columns that contain the data to aggregate, see ``agg_function``."""

    groupby_columns: List[str]
    """The columns to perform the group by.
        The list can contain the magic entry `$FACTORS$` that expands to all factors of the experiment.
        e.g., [exp_name, host_type, host_idx, $FACTORS$] would perform a group by of each run.
    """

    agg_functions: List[str] = ["mean", "min", "max", "std", "count"]
    """List of aggregate function to apply on ``data_columns``"""

    custom_tail_length: int =  5
    """"custom_tail" is a custom aggregation function that calculates the mean over the last `custom_tail_length` entries of a column."""

    def custom_tail_build(self, custom_tail_length):

        def custom_tail(data):
            return data.tail(custom_tail_length).mean()

        return custom_tail

    def transform(self, df: pd.DataFrame, options: Dict) -> pd.DataFrame:
        if df.empty:
            return df

        data_columns = self.data_columns
        # here, we get factor_columns
        groupby_columns = expand_factors(df, self.groupby_columns)
        agg_functions = self.agg_functions

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


class FilterColumnTransformer(Transformer):

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

    filters: Dict[str, Any] = {}
    allow_empty_result: bool = False

    def transform(self, df: pd.DataFrame, options: Dict) -> pd.DataFrame:

        import warnings

        warnings.warn(
            """FilterColumnTransformer is deprecated, instead you can directly use
            df.query(col == 'A') in the etl definition
            i.e., transformers: [df.query: {expr: col == 'A'}]""",
            DeprecationWarning
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



__all__ = [name for name, cl in inspect.getmembers(sys.modules[__name__], inspect.isclass) if name!="Transformer" and issubclass(cl, Transformer) ]