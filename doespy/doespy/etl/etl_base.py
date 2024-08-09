import importlib
import json
import os
import re
from inspect import getmembers
from typing import Dict, List
import warnings

import pandas as pd
import ruamel.yaml
from pydantic import ValidationError

from tqdm import tqdm

from doespy import util
from doespy import status
from doespy.design import validate_extend
from doespy.etl.steps.extractors import Extractor
from doespy.etl.steps.loaders import Loader
from doespy.etl.steps.transformers import Transformer

ETL_CUSTOM_PACKAGE = "does"


def run_single_suite(
    suite: str,
    suite_id: str,
    etl_output_dir: str = None,
    etl_from_design: bool = False,
    return_df: bool = False,
):

    # load a suite design and convert the $ETL$ part into a pipeline design
    # (as also used in super etl)
    suite_design = _load_suite_design(suite, suite_id, etl_from_design)
    pipeline_design = _etl_to_super_etl(suite, suite_id, suite_design)

    if etl_output_dir is None:
        etl_output_dir = util.get_etl_results_dir(suite=suite, id=suite_id)

    # create empty etl results dir + add .gitkeep
    if not os.path.exists(etl_output_dir):
        os.makedirs(etl_output_dir)
    with open(os.path.join(etl_output_dir, ".gitkeep"),"a+") as f:
        pass

    return run_etl(
        config_name=suite,
        pipeline_design=pipeline_design,
        etl_output_dir=etl_output_dir,
        etl_output_config_name=False,
        etl_output_pipeline_name=True,
        etl_from_design=etl_from_design,
        return_df=return_df,
    )



def run_multi_suite(
    super_etl: str,
    etl_output_dir: str,
    flag_output_dir_config_name: bool = True,
    flag_output_dir_pipeline: bool = True,
    etl_from_design: bool = False,
    pipeline_filter: List[str] = None,
    overwrite_suite_id_map: Dict[str, str] = None,
    return_df: bool = False,
    return_df_until_transformer_step: str = None,
):
    pipeline_design = _load_super_etl_design(name=super_etl, overwrite_suite_id_map=overwrite_suite_id_map)

    # filtering out pipelines by the pipeline_filter
    if pipeline_filter is not None:

        # check that pipeline_filter is valid
        for pipeline_name in pipeline_filter:
            assert pipeline_name not in ["$SUITE_ID$", "$ETL$"], "Pipeline filter cannot be $SUITE_ID$ or $ETL$"
            assert pipeline_name in pipeline_design["$ETL$"], f"Pipeline filter not found in super etl design: {pipeline_name}  (existing={pipeline_design['$ETL$'].keys()})"

        # find pipelines to remove
        existing_pipelines = set(pipeline_design["$ETL$"].keys())
        filtered_out_pipelines = existing_pipelines - set(pipeline_filter)
        print(f"Filtering our pipelines: {filtered_out_pipelines}")
        for p in filtered_out_pipelines:
            del pipeline_design["$ETL$"][p]

    return run_etl(
        config_name=super_etl,
        pipeline_design=pipeline_design,
        etl_output_dir=etl_output_dir,
        etl_output_config_name=flag_output_dir_config_name,
        etl_output_pipeline_name=flag_output_dir_pipeline,
        etl_from_design=etl_from_design,
        return_df=return_df,
        return_df_until_transformer_step=return_df_until_transformer_step,
    )


def run_etl(
    config_name,
    pipeline_design,
    etl_output_dir: str,
    etl_output_config_name: bool = False,
    etl_output_pipeline_name: bool = False,
    etl_from_design: bool = False,
    return_df: bool = False,
    return_df_until_transformer_step: str = None,
):

    etl_config = pipeline_design["$ETL$"]

    suite_id_map = pipeline_design["$SUITE_ID$"]

    output_dfs = {}

    # go over pipelines and run them
    for pipeline_name, pipeline in etl_config.items():

        experiments = pipeline["experiments"]

        extractors, transformers, loaders = load_selected_processes(
            pipeline["extractors"], pipeline["transformers"], pipeline["loaders"]
        )

        experiments_df = []
        etl_infos = []

        # only want to run pipelines where results already exist
        has_exp_result = False

        for suite, experiments in experiments.items():

            experiment_suite_id_map = _extract_experiments_suite(
                suite, experiments, suite_id_map
            )
            for experiment, suite_id in experiment_suite_id_map.items():

                if not has_exp_result:
                    res_dir = util.get_suite_results_dir(suite=suite, id=suite_id)

                    # check that results from at least one run are present
                    for x in os.listdir(os.path.join(res_dir, experiment)):
                        if x.startswith("run_"):
                            has_exp_result = True
                            break


                suite_design = _load_suite_design(suite, suite_id, etl_from_design)

                etl_info = {
                    "suite": suite,
                    "suite_id": suite_id,
                    "pipeline": pipeline_name,
                    "experiments": [experiment],
                    "etl_output_dir": etl_output_dir,
                }
                etl_infos.append(etl_info)

                try:
                    # extract data from
                    df = extract(
                        suite=suite,
                        suite_id=suite_id,
                        experiments=[experiment],
                        base_experiments=suite_design,
                        extractors=extractors,
                    )

                    experiments_df.append(df)
                except Exception:
                    print(
                        f"An error occurred in extractor from pipeline \
                            {pipeline_name}!",
                        etl_info,
                    )
                    raise


        if not has_exp_result:
            warnings.warn(f"skip executing pipeline={pipeline_name} because no experiment data available")
            return

        # ensure dir exists
        config_post = config_name if etl_output_config_name else None
        pipeline_post = pipeline_name if etl_output_pipeline_name else None

        if etl_output_dir is None:
            etl_output_dir_full = None
        else:
            etl_output_dir_full = _get_output_dir_name(
                etl_output_dir, config_post, pipeline_post
            )

            if not os.path.exists(etl_output_dir):
                os.makedirs(etl_output_dir)

        df = pd.concat(experiments_df)

        etl_info = {
            "suite": "_".join([x["suite"] for x in etl_infos]),
            "suite_id": "_".join([str(x["suite_id"]) for x in etl_infos]),
            "pipeline": pipeline_name,
            "experiments": experiments,
            "etl_output_dir": etl_output_dir_full,
        }

        try:
            # apply transformers sequentially
            for x in transformers:

                if isinstance(x["transformer"], str):
                    # possibility for df functions directly
                    df = _apply_pandas_df_transformer(
                        df, func_name=x["transformer"], args=x["options"]
                    )

                else:

                    if return_df_until_transformer_step is not None and x["transformer"].name == return_df_until_transformer_step:
                        output_dfs[pipeline_name] = df.copy()

                    df = x["transformer"].transform(df, options=x["options"])

            if return_df and return_df_until_transformer_step is None:
                output_dfs[pipeline_name] = df
            else:
                # execute all loaders on df
                for x in loaders:
                    x["loader"].load(df, options=x["options"], etl_info=etl_info)

        except Exception:
            print(f"An error occurred in pipeline {pipeline_name}!", etl_info)
            raise

    if return_df:
        # for use in jupyter notebooks
        return output_dfs


def _load_suite_design(suite, suite_id, etl_from_design):
    if etl_from_design:
        suite_design, _ = validate_extend.main(
            suite=suite, only_validate_design=True, ignore_undefined_vars=True
        )
    else:
        suite_dir = util.get_suite_results_dir(suite=suite, id=suite_id)
        suite_design = util.load_config_yaml(suite_dir, file="suite_design.yml")
    return suite_design


def _load_super_etl_design(name, overwrite_suite_id_map=None):

    from doespy.design.etl_design import SuperETL

    config_dir = util.get_super_etl_dir()

    pipeline_design = util.load_config_yaml(config_dir, file=f"{name}.yml")

    if overwrite_suite_id_map is not None:
        print(f"Replacing suite id map in super etl design: {overwrite_suite_id_map}")
        # overwrite suite id map
        pipeline_design["$SUITE_ID$"] = overwrite_suite_id_map

        for pipeline_name, pipeline in pipeline_design["$ETL$"].items():
            if pipeline_name == "$SUITE_ID$":
                continue

            # delete experiments that are not in the overwrite_suite_id_map
            for suite in list(pipeline["experiments"].keys()):
                if suite not in overwrite_suite_id_map.keys():
                    # print("Removing suite", suite, "from pipeline", pipeline_name)
                    del pipeline["experiments"][suite]

    model = SuperETL(**pipeline_design)

    pipeline_design_str = model.json(by_alias=True, exclude_none=True)
    pipeline_design = json.loads(pipeline_design_str)

    return pipeline_design


def _etl_to_super_etl(suite, suite_id, suite_design):

    # 1st Set $SUITE_ID$ Field

    suite_design["$SUITE_ID$"] = {suite: suite_id}

    etl_config = suite_design["$ETL$"]

    for _pipeline_name, pipeline in etl_config.items():
        pipeline["experiments"] = {suite: pipeline["experiments"]}

    pipeline_design = {"$SUITE_ID$": {suite: suite_id}, "$ETL$": etl_config}

    return pipeline_design


def _apply_pandas_df_transformer(df, func_name, args):

    try:
        func = getattr(df, func_name)

        # apply the function on the dataframe
        return func(**args)
    except AttributeError:
        raise ValueError(f"pandas.DataFrame.{func_name} not found")


def _extract_experiments_suite(suite, experiments, suite_id_map):
    """
    :param experiments list of experiments
    :param suite_id_map dict can be a dict of (suite, suite_id),
            or (suite, dict) where dict is a dict of experiment-level id
    :return: dict Experiment to suite mapping
    """
    suite_ids = suite_id_map[suite]

    if isinstance(suite_ids, str) or isinstance(suite_ids, int):
        # suite-wide id
        return {experiment: suite_ids for experiment in experiments}
    elif isinstance(suite_ids, dict):
        # dict { experiment: id }
        default = suite_ids.get("$DEFAULT$", None)
        d = {exp: suite_ids.get(exp, default) for exp in experiments}
        if any(v is None for k, v in d.items()):
            raise ValueError(f"Suite Id cannot be None: {d} (set default or suite in suite id map)")
        return d
    else:
        # TODO [nku] it could also be a feature to have a list of suite ids for the same suite
        raise ValueError("Suite ids must be a value or dict!")


def _get_output_dir_name(
    output_path: str, config_name: str = None, pipeline_name: str = None
):
    """Generates output directory based on options and current pipeline."""

    if config_name is not None:
        # config_prefix = re.match(r"^(.*)\.yml$", config_name).group(1)
        # assert config_prefix is not None,
        # f"Filename {config_name} has invalid format and cant be extracted!"
        output_path = os.path.join(output_path, config_name)

    if pipeline_name is not None:
        output_path = os.path.join(output_path, pipeline_name)

    return output_path


############################################################################
# Load Extractor, Transformer, and Loaders                                 #
############################################################################


def load_selected_processes(extractors_sel, transformers_sel, loaders_sel):

    extractors_avl, transformers_avl, loaders_avl = _load_available_processes()

    extractors = []
    for name, options in extractors_sel.items():

        if name not in extractors_avl:
            raise ValueError(f"extractor not found: {name}")

        d = {
            "extractor": extractors_avl[name](**options),
            "options": options, # TODO: eventually this can be removed in a newer version
        }

        extractors.append(d)

    transformers = []
    for trans_sel in transformers_sel:
        if "name" in trans_sel:
            if trans_sel["name"] not in transformers_avl:
                raise ValueError(f"transformer not found: {trans_sel['name']}")

            d = {
                "transformer": transformers_avl[trans_sel["name"]](**trans_sel),
                "options": trans_sel, # TODO: eventually this can be removed in a newer version
            }
            transformers.append(d)
        elif len(trans_sel.keys()) == 1:

            # TODO: Could switch to  DfTransformer(Transformer) and implement the functionality there.

            func_name = next(iter(trans_sel))
            args = trans_sel[func_name]

            match = re.search(r"df\.(.*)", func_name)
            func_name = match.group(1)

            d = {
                "transformer": func_name,
                "options": args,
            }
            transformers.append(d)

        else:
            raise ValueError(f"transformer with illegal format: {trans_sel}")

    loaders = []
    for name, options in loaders_sel.items():

        if name not in loaders_avl:
            raise ValueError(f"loader not found: {name}")

        d = {
            "loader": loaders_avl[name](**options),
            "options": options, # TODO: eventually this can be removed in a newer version
        }
        loaders.append(d)

    return extractors, transformers, loaders


def _load_available_processes():

    extractors = {}
    transformers = {}
    loaders = {}

    import pkgutil
    import warnings

    # Find location of doespy ETL classes
    import doespy
    assert len(doespy.__path__) == 1, "doespy.__path__ should only have one path. If this fails open an issue for @hiddely."
    doespy_path = doespy.__path__[0]
    doespy_parent_path = os.path.normpath(os.path.join(doespy_path, "../"))

    # Find location of custom ETL classes
    # doe-suite-config is fixed relative to DOES_PROJECT_DIR
    doe_suite_config_path = os.path.join(os.environ['DOES_PROJECT_DIR'], "doe-suite-config")

    paths = [
        doespy_parent_path,  # doe-suite provided etl steps
        doe_suite_config_path,  # custom steps
    ]
    with warnings.catch_warnings(record=True):
        for _importer, modname, _ispkg in pkgutil.walk_packages(
            path=paths, onerror=lambda _: None
        ):
            should_import = ETL_CUSTOM_PACKAGE in modname or "doespy" in modname
            # print("Found submodule %s (is a pack/age: %s), will import %s" % (modname, _ispkg, should_import))
            if should_import:
                _load_processes(modname, extractors, transformers, loaders)

    return extractors, transformers, loaders


def _load_processes(module_name, extractors, transformers, loaders):

    module = importlib.import_module(module_name)

    # go over all members of the module
    for member_name, _ in getmembers(module):

        # find members that are actually an ETL process step
        # by checking if they inherit from the abstract base class
        try:
            etl_candidate = getattr(module, member_name)
            if issubclass(etl_candidate, Extractor):
                try:
                    etl_candidate()
                except ValidationError:
                    # TODO: Should we warn or fail if ETL Step Validation failed?
                    warnings.warn(f"ETL Validation failed for Extractor: {member_name}")
                    pass
                except TypeError as e:
                    if member_name != "Extractor":
                        # added because if the extractor class does not overwrite the proper regex function, a type error is thrown
                        print(f"ETL Extractor TypeError: {member_name}  {e}")
                    raise e
                assert member_name not in extractors, f"Duplicate Extractor: {member_name} already exists"
                extractors[member_name] = etl_candidate
            elif issubclass(etl_candidate, Transformer):
                try:
                    etl_candidate()
                except ValidationError:
                    # TODO: Should we warn or fail if ETL Step Validation failed?
                    warnings.warn(f"ETL Validation failed for Extractor: {member_name}")
                    pass
                assert member_name not in transformers, f"Duplicate Transformer: {member_name} already exists"
                transformers[member_name] = etl_candidate
            elif issubclass(etl_candidate, Loader):
                try:
                    etl_candidate()
                except ValidationError:
                    # TODO: Should we warn or fail if ETL Step Validation failed?
                    warnings.warn(f"ETL Validation failed for Extractor: {member_name}")
                    pass
                assert member_name not in loaders, f"Duplicate Loader: {member_name} already exists"
                loaders[member_name] = etl_candidate

        except TypeError:
            pass


############################################################################
# Extractor                                                                #
############################################################################


def extract(
    suite: str,
    suite_id: str,
    experiments: List[str],
    base_experiments: Dict,
    extractors: List[Dict],
) -> pd.DataFrame:
    res_lst = []

    res_dir = util.get_suite_results_dir(suite=suite, id=suite_id)
    existing_exps = util._list_dir_only(res_dir)

    exps_filtered = [exp for exp in existing_exps if exp in experiments]

    for exp in exps_filtered:

        exp_dir = util.get_suite_results_dir(suite=suite, id=suite_id, exp=exp)

        runs = util._list_dir_only(exp_dir)
        factor_columns = _parse_factors(base_experiments[exp])

        for run in tqdm(runs, desc=f"processing runs of experiment {exp}"):
            run_dir = os.path.join(exp_dir, run)
            reps = util._list_dir_only(run_dir)

            for rep in reps:
                rep_dir = os.path.join(run_dir, rep)
                host_types = util._list_dir_only(rep_dir)

                try:
                    config = util.load_config_yaml(path=rep_dir, file="config.json")
                except FileNotFoundError:
                    continue

                # ignores the part of the config that shows what is varied
                # # (if this is present)
                if "$FACTOR_LEVEL" in config:
                    del config["~FACTORS_LEVEL"]

                config_flat = _flatten_d(config)

                for host_type in host_types:
                    host_type_dir = os.path.join(rep_dir, host_type)
                    hosts = util._list_dir_only(host_type_dir)

                    for host_idx, host in enumerate(hosts):
                        host_dir = os.path.join(host_type_dir, host)
                        files = util._list_files_only(host_dir)

                        job_info = {
                            "suite_name": suite,
                            "suite_id": suite_id,
                            "exp_name": exp,
                            "run": int(run.split("_")[-1]),
                            "rep": int(rep.split("_")[-1]),
                            "host_type": host_type,
                            "host_idx": host_idx,
                            "factor_columns": factor_columns,
                        }

                        for file in files:
                            d_lst = _parse_file(host_dir, file, extractors, config_flat)
                            for d in d_lst:
                                if d is None:
                                    warnings.warn(f"SKIP EMPTY FILE={file} in {host_dir}")
                                    continue
                                d_flat = _flatten_d(d)
                                res = {**job_info, "source_file": file, **config_flat, **d_flat}
                                res_lst.append(res)

    df = pd.DataFrame(res_lst)

    res_lst.clear()
    return df


def _parse_file(path: str, file: str, extractors: List[Dict], config_flat: Dict) -> List[Dict]:
    has_match = False

    for extractor_d in extractors:
        patterns = extractor_d["extractor"].file_regex
        if not isinstance(patterns, list):
            patterns = [patterns]

        for p in patterns:
            regex = re.compile(p)

            if regex.match(file):

                # we want to assign one extractor per file
                if has_match:
                    raise ValueError(
                        f"file={file} matches multiple extractors (p={path})"
                    )

                file_path = os.path.join(path, file)

                options = extractor_d["options"]
                options["$config_flat$"] = config_flat
                d_lst = extractor_d["extractor"].extract(
                    path=file_path, options=options
                )

                has_match = True

    # if no extractor found
    if not has_match:
        raise ValueError(f"file={file} matches no extractor (path={path})")

    return d_lst


def _parse_factors(experiment: Dict) -> list:
    """
    Parses factors in experiment. Loosely based on `suite_design_extend.py`.
    :param experiment:
    :return: list of factors
    """

    # Stolen from `suite_design_extend.py`
    def _nested_dict_iter(nested, p=[]):
        for key, value in nested.items():
            if isinstance(value, dict):
                yield from _nested_dict_iter(value, p=p + [key])
            else:
                yield key, value, p

    factor_columns = []
    for k, v, path in _nested_dict_iter(experiment["base_experiment"]):
        # k: the key (i.e. the name of the config option, unless it's a factor,
        #    than the content is just $FACTOR$)
        # v: the value or a list of levels in case it's a factor
        # path: to support nested config dicts, path keep tracks
        #       of all the parent nodes of k (empty if it is on the top level)

        if k == "$FACTOR$":
            # inline factor
            factor = ".".join(path)

            factor_columns.append(factor)
        elif v == "$FACTOR$":
            # factor defined in factor_levels
            factor = ".".join([*path, k])
            factor_columns.append(factor)

    return factor_columns




def _flatten_d(d):
    if any(isinstance(i, dict) for i in d.values()):
        return json.loads(pd.json_normalize(d, sep=".").iloc[0].to_json())
    else:
        return d
