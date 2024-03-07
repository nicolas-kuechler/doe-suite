

from doespy.design.etl_design import MyETLBaseModel

import abc
import typing
import jmespath
import pandas as pd
from typing import Dict,  List, Union

from doespy.design.etl_design import MyETLBaseModel

from pydantic import Field, validator

class Metric(MyETLBaseModel):

    value_cols: Union[str, List[str]]
    error_cols: Union[str, List[str]] = None

    @validator('value_cols', 'error_cols', pre=True)
    def ensure_list(cls, v):
        if isinstance(v, str):
            return [v]
        return v


    @classmethod
    def convert_metrics(cls, metrics: Dict[str, 'Metric'], df: pd.DataFrame):
        """
        Introduce a duplicate of the df for each metric and mark it with a new column $metrics$.
        -> this allows to use $metrics$ as a column to generate different plots / subplots / groups / etc.
        """

        df1 = None
        metric_cols = set()
        for m in metrics.values():
            metric_cols.update(m.value_cols)
            if m.error_cols is not None:
                metric_cols.update(m.error_cols)



        # ensure that the metric columns are numeric
        # NOTE: If a column is both a metric and a group column, then it will not remain numeric
        # TODO [nku] could add a check for this
        metric_cols = list(metric_cols)
        df[metric_cols] = df[metric_cols].apply(pd.to_numeric)



        for metric_name, metric in metrics.items():

            df_copy = df.copy()
            df_copy["$metrics$"] = metric_name

            assert set(metric.value_cols).issubset(df.columns), f"Metric Value Columns: Some columns not found in DataFrame. Missing: {set(metric.value_cols) - set(df.columns)}"
            if metric.error_cols is not None:
                assert set(metric.error_cols).issubset(df.columns), f"Metric Error Columns: Some columns not found in DataFrame. Missing: {set(metric.error_cols) - set(df.columns)}"

            df1 = pd.concat([df1, df_copy], axis=0) if df1 is not None else df_copy

        return df1



class DataFilter(MyETLBaseModel):

     allowed: Dict[str, List[str]]

     def apply(self, cols: List[str], df: pd.DataFrame) -> pd.DataFrame:

        n_rows_intial = len(df)
        df_filtered = df.copy()

        cols_values = [(col, self.allowed.get(col, None)) for col in cols]

        # filter out non-relevant results
        for col, allowed in cols_values:

            # convert column to string for filtering
            try:
                df_filtered[col] = df_filtered[col].astype(str)
            except KeyError:
                raise KeyError(f"col={col} not in df.columns={df.columns}")

            all_values = df_filtered[col].unique().tolist()

            if allowed is None:
                allowed = all_values

            # filter out non-relevant results
            df_filtered = df_filtered[df_filtered[col].isin(allowed)]

            remaining_values = set(df_filtered[col].unique().tolist())

            removed_values =  set(all_values) - remaining_values

            if removed_values:
                print(f"Filtering {col} to {allowed}   (remaining values: {remaining_values}  |  removed values: {removed_values})")

            # convert to categorical
            df_filtered[col] = pd.Categorical(df_filtered[col], ordered=True, categories=allowed)
        df_filtered.sort_values(by=cols, inplace=True)

        print(f"Filtered out {n_rows_intial - len(df_filtered)} rows, now there are {len(df_filtered)} remaining rows")

        return df_filtered



class LabelFormatter(MyETLBaseModel):

    template: str
    """A template string that can contain placeholders in the form "{placeholder}".
    The placehold correspond to column names (which are presend in the data_id)
    """

    kwargs: Dict[str, str] = Field(default_factory=dict)
    """Additional keyword arguments that will be passed to the matplotlib function that is used to set the labels.
    """

    def apply(self, data_id: Dict[str, str], subplot_config: 'BaseSubplotConfig', info: str) -> str:

        #template string: "Hello {name}"
        labels = {k: subplot_config.label(lbl, data_id) for k, lbl in data_id.items()}

        try:
            lbl = self.template.format(**labels)
        except KeyError as e:
            raise KeyError(f"LabelFormatter: {info}: Could not find all keys in data_id: {data_id}") from e
        return lbl



class ColsForEach(MyETLBaseModel):

    cols: List[str]

    jp_except: str = None
    """Skip certain combinations based on the data id (and parent data_id)
    """

    label: LabelFormatter = None

    def get_cols(self):
        return self.cols.copy()

    def for_each(self, df: pd.DataFrame, parent_id: Dict[str, str]):

        if not self.cols: # is empty
            yield 0, df, {}
        else:
            cols = self.cols[0] if len(self.cols) == 1 else self.cols

            i = 0
            for idx, df1 in df.groupby(cols, dropna=False):
                idx = (idx, ) if not isinstance(idx, tuple) else idx
                data_id = {k: v for k, v in zip(self.cols, list(idx), strict=True)}
                all_id = {**parent_id, **data_id}
                if self.jp_except is None or not is_match(self.jp_except, all_id, info="jp_except"):
                    yield i, df1, data_id
                    i += 1
                else:
                    print(f"Skipping {all_id} due to jp_except={self.jp_except}")



def is_match(jp_query, data_id, info) -> bool:

    if jp_query is None:
        #print(f"JmesPathFilter: {info}: query is None")
        return True

    #print(f"JmesPathFilter: {info}: query={self.jp_query}  data_id={data_id}")

    result = jmespath.search(jp_query, data_id)
    #print(f"JmesPathFilter: {info}: query is {result}    {jp_query=}")
    assert isinstance(result, bool), f"JmesPathFilter: {info}: query={jp_query} returned non-boolean result: {result}"
    return result




class ArtistConfig(MyETLBaseModel):

    jp_query: str = None

    class Config:
        extra = "allow"

    @classmethod
    def merge_cumulative(cls, configs: List['ArtistConfig'], data_id: Dict, info="artist_config") -> Dict:
        config = None

        # loop in reverse order to give the first filter the highest priority
        for cfg in reversed(configs):

            if config is None:
                config = {}

            if is_match(cfg.jp_query, data_id, info):
                config.update(cfg.__dict__)

        del config["jp_query"]

        return config





class BaseSubplotConfig(MyETLBaseModel, abc.ABC):

    jp_query: str = None

    @classmethod
    def merge_cumulative(cls, configs: List['BaseSubplotConfig'], data_id: Dict, info="subplot_config"):

        # for each ax (i.e., subplot) determine the config by merging the configs where the filter matches
        config = None
        for cfg in configs:
            if is_match(cfg.jp_query, data_id, info):
                if config is None:
                    config = cfg
                else:
                    config.fill_missing(cfg)
        return config

    def fill_missing(self, other):
        for k, v in self.dict().items():
            if v is None:
                setattr(self, k, getattr(other, k))

    @abc.abstractmethod
    def get_cols(self) -> List[str]:
        pass

    @abc.abstractmethod
    def artist_config(self, artist_id) -> Dict:
        pass

    @abc.abstractmethod
    def create_chart(self, ax, df1, data_id, metric, ctx):
        pass

    def label(self, lbl, data_id) -> str:
        return lbl






class ObserverContext(MyETLBaseModel):

    observers: Dict[str, typing.Any] = Field(default_factory=dict)

    def _ensure_init_stage(self, stage_cls):
        assert issubclass(stage_cls, Observer), f"{stage_cls=}  must be of a subclass of Observer"
        if stage_cls.__name__ not in self.observers:
            # init if not exists
            self.observers[stage_cls.__name__] = stage_cls()

    def add_observer(self, stage_cls, func):
        self._ensure_init_stage(stage_cls)
        self.observers[stage_cls.__name__].register(func)

    def remove_observer(self, stage_cls, func):
        self._ensure_init_stage(stage_cls)
        self.observers[stage_cls.__name__].unregister(func)

    def stage(self, stage_cls, defaults=None):
        self._ensure_init_stage(stage_cls=stage_cls)
        return self.observers[stage_cls.__name__].with_defaults(defaults)


class Observer(abc.ABC):

    def __init__(self):
        self.registered = []
        self.defaults = []
        self.deleted = set()

    def observers(self):
        return [o for o in self.defaults + self.registered if o.__name__ not in self.deleted]

    def with_defaults(self, defaults):
        if defaults is not None:
            self.defaults = defaults
        return self

    def register(self, func):
        self.registered.append(func)

    def unregister(self, func):
        # unregister by function name
        self.deleted.add(func.__name__)
