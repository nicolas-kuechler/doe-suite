
import abc
import jmespath
from typing import Dict, List
from doespy.design.etl_design import MyETLBaseModel


def is_match(jp_query, data_id, info) -> bool:

    if jp_query is None:
        # print(f"JmesPathFilter: {info}: query is None")
        return True

    # print(f"JmesPathFilter: {info}: query={self.jp_query}  data_id={data_id}")
    # print(f"JmesPathFilter: {info}: query={jp_query}  data_id={data_id}")
    result = jmespath.search(jp_query, data_id)

    # print(f"    -> is match: {result}")
    # print(f"JmesPathFilter: {info}: query is {result}    {jp_query=}")
    assert isinstance(
        result, bool
    ), f"JmesPathFilter: {info}: query={jp_query} returned non-boolean result: {result}"
    return result

class BasePlotConfig(MyETLBaseModel, abc.ABC):

    jp_query: str = None
    """The JMESPath query is applied to the plot_id (i.e., dict of col:data pairs) to determine whether this configuration entry applies or not.
    If the jp_query matches, then this configuration applies.
    If None, then this config applies to all plot_ids."""

    @classmethod
    def merge_cumulative(
        cls, configs: List["BasePlotConfig"], plot_id: Dict, info="plot_config"
    ):
        """:meta private:"""

        # for each ax (i.e., subplot) determine the config by merging the configs where the filter matches
        config = None
        for cfg in configs:
            if is_match(cfg.jp_query, plot_id, info):
                if config is None:
                    config = cfg.copy()
                else:
                    config.fill_missing(cfg)
        return config


class BaseSubplotConfig(MyETLBaseModel, abc.ABC):

    jp_query: str = None
    """The JMESPath query is applied to the subplot_id (i.e., dict of col:data pairs) to determine whether this configuration entry applies or not.
    If the jp_query matches, then this configuration applies.
    If None, then this config applies to all subplot_ids."""

    @classmethod
    def merge_cumulative(
        cls, configs: List["BaseSubplotConfig"], data_id: Dict, info="subplot_config"
    ):
        """:meta private:"""

        # for each ax (i.e., subplot) determine the config by merging the configs where the filter matches
        config = None
        for cfg in configs:

            if is_match(cfg.jp_query, data_id, info):
                if config is None:
                    config = cfg.copy()
                else:
                    config.fill_missing(cfg)

        return config

    def fill_missing(self, other):
        """:meta private:"""

        for k, v in self.dict().items():
            if v is None:
                setattr(self, k, getattr(other, k))

    @abc.abstractmethod
    def get_cols(self) -> List[str]:
        """:meta private:"""
        pass

    @abc.abstractmethod
    def artist_config(self, artist_id, plot_config) -> Dict:
        """:meta private:"""
        pass

    @abc.abstractmethod
    def create_chart(self, ax, df1, data_id, metric, plot_config):
        """:meta private:"""
        pass

    def label(self, lbl, data_id) -> str:
        """:meta private:"""
        return lbl
