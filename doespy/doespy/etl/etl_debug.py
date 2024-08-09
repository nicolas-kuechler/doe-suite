from typing import Type, Union, Optional, Dict
from doespy import util
import pandas as pd
import ruamel.yaml
import os

from doespy.etl.steps.transformers import Transformer
from doespy.etl.steps.loaders import Loader
from functools import lru_cache, wraps

from doespy.etl.etl_base import run_multi_suite
from doespy.design import etl_design

class HDict(dict):
    """Allows us to pass a dictionary to this cached function"""
    def __hash__(self):
        return hash(frozenset(self.items()))

@lru_cache(maxsize=1)
def debug_compute_input_df(super_etl: str , pipeline: str, StepCls: Type[Union[Transformer, Loader]],
                           overwrite_suite_id_map: Optional[HDict[str, str]]=None):
    """
    Computes the input dataframe for a given step in the super_etl pipeline.

    The function will run the super_etl pipeline until the given step and return the dataframe.
    For future invocation, the dataframe will be cached.
    (use cdebug_compute_input_df.cache_clear() to reset the cache)
    """

    if issubclass(StepCls, Transformer):
        return_df_until_transformer_step=StepCls.__name__
    elif issubclass(StepCls, Loader):
        return_df_until_transformer_step=None
    else:
        raise ValueError(f"Unknown step type: {StepCls}")

    df_cached = run_multi_suite(
            super_etl=super_etl,
            etl_output_dir=None,
            pipeline_filter=[pipeline],
            return_df=True,
            return_df_until_transformer_step=return_df_until_transformer_step,
            overwrite_suite_id_map=overwrite_suite_id_map
        )
    if df_cached is not None:
        return df_cached[pipeline]
    else:
        return pd.DataFrame()


def debug_super_etl_step(super_etl: str, pipeline: str, StepCls, df: pd.DataFrame):
    """
    Allows running a single step in the super_etl pipeline with the configuration from the super_etl file.
    This is useful for debugging / developing a single step without running the entire pipeline.

    See `demo_project/doe-suite-config/super_etl/debug_etl.ipynb` for an example.
    """

    path = os.path.join(util.get_super_etl_dir(), f"{super_etl}.yml")

    with open(path, "r") as f:
        config = ruamel.yaml.safe_load(f)

    cfg = config["$ETL$"]
    assert pipeline in cfg, f"Pipeline {pipeline} not found in {cfg.keys()}"

    cfg = cfg[pipeline]

    experiments = cfg["experiments"]

    if issubclass(StepCls, Transformer):
        step = None
        for tf in cfg["transformers"]:
            if "name" in tf and tf["name"] == StepCls.__name__:
                step = StepCls(**tf)
                break
        assert step is not None, f"Step {StepCls.__name__} not found in {cfg['transformers']}"
        return step.transform(df, options={})

    elif issubclass(StepCls, Loader):
        assert StepCls.__name__ in cfg["loaders"], f"Step {StepCls.__name__} not found in {cfg['loaders']}"

        cfg = cfg["loaders"][StepCls.__name__]

        print(f"Config={cfg=}")
        step = StepCls(**cfg)

        etl_info = {
            "suite": "suite",
            "suite_id": "suite_id",
            "pipeline": pipeline,
            "experiments": experiments,
            "etl_output_dir": None,
        }
        return step.load(df, options={}, etl_info=etl_info)
    else:
        raise ValueError(f"Unknown step type: {StepCls}")