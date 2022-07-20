import os, sys, importlib, re, warnings, subprocess
import yaml, json, argparse
from inspect import getmembers
import pandas as pd
from typing import List, Dict

from doespy.etl.steps.extractors import Extractor
from doespy.etl.steps.transformers import Transformer
from doespy.etl.steps.loaders import Loader


from doespy import util


ETL_CUSTOM_PACKAGE = "does"

def main():

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--suite", type=str, required=False)
    parser.add_argument("--id", type=str, required=False)
    parser.add_argument("--all", action="store_true", required=False)

    # by setting the --design flag, we can make the etl pipeline be run using the etl definition in `doe-suite-config/designs`
    # rather than the on in the results directory
    parser.add_argument("--design", action="store_true")

    parser.add_argument("--output", type=str, default="etl_results", required=False)

    args = parser.parse_args()

    # ensure that exactly one of --all or (--suite and --id) are set
    if not ((args.all and args.id is None and args.suite is None) or (not args.all and args.id is not None and args.suite is not None)):
        parser.error("either --all or --suite and --id are required but both are not possible")


    if args.suite is not None and args.id is not None:
        run(suite=args.suite, suite_id=args.id, use_etl_from_design=args.design, etl_output_dir=args.output)
    elif args.all:
        for x in util.get_does_results():
            run(suite=x["suite"], suite_id=x["suite_id"], use_etl_from_design=args.design, etl_output_dir=args.output)
    else:
        raise ValueError("the xor between the options should ensure that this cannot be the case")

def apply_pandas_df_transformer(df, func_name, args):

    try:
        func = getattr(df, func_name)

        # apply the function on the dataframe
        return func(**args)
    except AttributeError:
        raise ValueError(f"pandas.DataFrame.{func_name} not found")


def run(suite, suite_id, use_etl_from_design, etl_output_dir):

    print(f"Running etl for suite={suite}  id={suite_id} ...")

    if "DOES_PROJECT_DIR" not in os.environ:
        raise ValueError(f"env variable: DOES_PROJECT_DIR not set")
    prj_dir = os.environ["DOES_PROJECT_DIR"]
    results_dir = os.path.join(prj_dir, "doe-suite-results")

    # can search for the last suite_id
    if suite_id == "last":
        suite_id = util.get_last_suite_id(suite)

    suite_dir = os.path.join(results_dir, f"{suite}_{suite_id}")

    # load etl_config by loading suite design file
    if use_etl_from_design:
        design_dir = os.path.join(prj_dir, "doe-suite-config", "designs")
        suite_design = _load_config_yaml(design_dir, file=f"{suite}.yml")
    else:
        suite_design = _load_config_yaml(suite_dir, file="suite_design.yml")
    if "$ETL$" not in suite_design:
        # we don't have an ETL config => don't run it
        return
    etl_config = suite_design["$ETL$"]

    # collect the names of all experiments
    experiment_names = list(filter(lambda x: not x.startswith("$"), suite_design.keys()))

    # go over pipelines and run them
    for pipeline_name, pipeline in etl_config.items():


        if pipeline["experiments"] == "*":
            pipeline["experiments"] = experiment_names

        etl_info = {
            "suite": suite, "suite_id": suite_id, "pipeline": pipeline_name, "experiments": pipeline["experiments"], "suite_dir": suite_dir, "etl_output_dir": etl_output_dir
        }

        extractors, transformers, loaders = load_selected_processes(pipeline["extractors"], pipeline["transformers"], pipeline["loaders"])

        try:
            # extract data from
            df = extract(suite=suite, suite_id=suite_id, suite_dir=suite_dir, experiments=pipeline["experiments"], base_experiments=suite_design, extractors=extractors)

            # apply transformers sequentially
            for x in transformers:

                if isinstance(x["transformer"], str):
                    # possibility for df functions directly
                    df = apply_pandas_df_transformer(df, func_name=x["transformer"], args=x["options"])

                else:
                    df = x["transformer"].transform(df, options=x["options"])

            # execute all loaders on df
            for x in loaders:
                x["loader"].load(df, options=x["options"], etl_info=etl_info)
        except:
            print(f"An error occurred in pipeline {pipeline_name}!", etl_info)
            raise



############################################################################
# Load Extractor, Transformer, and Loaders                                 #
############################################################################

def load_selected_processes(extractors_sel, transformers_sel, loaders_sel):

    extractors_avl, transformers_avl, loaders_avl = _load_available_processes()

    extractors = []
    for name, options in extractors_sel.items():

        if name not in extractors_avl:
            raise ValueError(f"extractor not found: {name}")

        regex = options.get("file_regex")

        d = {
            "extractor": extractors_avl[name](regex),
            "options": options,
        }

        extractors.append(d)

    transformers = []
    for trans_sel in transformers_sel:
        if 'name' in trans_sel:
            if trans_sel['name'] not in transformers_avl:
                raise ValueError(f"transformer not found: {trans_sel['name']}")

            d = {
                "transformer": transformers_avl[trans_sel["name"]](),
                "options": trans_sel,
            }
            transformers.append(d)
        elif len(trans_sel.keys())==1:
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
            "loader": loaders_avl[name](),
            "options": options,
        }
        loaders.append(d)

    return extractors, transformers, loaders


def _load_available_processes():

    extractors = {}
    transformers = {}
    loaders = {}

    import pkgutil, warnings
    with warnings.catch_warnings(record=True):
        for _importer, modname, _ispkg in pkgutil.walk_packages(path=None, onerror=lambda x: None):
            warnings.simplefilter("ignore")
            if ETL_CUSTOM_PACKAGE in modname or "doespy" in modname:
                _load_processes(modname, extractors, transformers, loaders)

    # print(f"ext={len(extractors)}  trans={len(transformers)}  loaders={len(loaders)}")
    return extractors, transformers, loaders

def _load_processes(module_name, extractors, transformers, loaders):

    module = importlib.import_module(module_name)

    # go over all members of the module
    for member_name, _ in getmembers(module):

        # check for duplicates
        if member_name in extractors or member_name in transformers or member_name in loaders:
            raise ValueError(f"duplicate class={member_name}")

        # find members that are actually an ETL process step
        # by checking if they inherit from the abstract base class
        try:
            etl_candidate = getattr(module, member_name)
            if issubclass(etl_candidate, Extractor):
                extractor = etl_candidate()
                extractors[member_name] = etl_candidate
            elif issubclass(etl_candidate, Transformer):
                transformer = etl_candidate()
                transformers[member_name] = etl_candidate
            elif issubclass(etl_candidate, Loader):
                loader = etl_candidate()
                loaders[member_name] = etl_candidate

        except TypeError:
            pass


############################################################################
# Extractor                                                                #
############################################################################

def extract(suite:str, suite_id: str, suite_dir: str, experiments: List[str], base_experiments: Dict, extractors: List[Dict]) -> pd.DataFrame:
    res_lst = []

    existing_exps = _list_dir_only(suite_dir)

    exps_filtered = [exp for exp in existing_exps if exp in experiments]

    for exp in exps_filtered:
        exp_dir = os.path.join(suite_dir, exp)
        runs = _list_dir_only(exp_dir)
        factor_columns = _parse_factors(base_experiments[exp])

        for run in runs:
            run_dir = os.path.join(exp_dir, run)
            reps = _list_dir_only(run_dir)

            for rep in reps:
                rep_dir = os.path.join(run_dir, rep)
                host_types = _list_dir_only(rep_dir)

                try:
                    config = _load_config_yaml(path=rep_dir, file="config.json")
                except FileNotFoundError:
                    continue

                # ignores the part of the config that shows what is varied (if this is present)
                if "$FACTOR_LEVEL" in config:
                    del config["~FACTORS_LEVEL"]

                config_flat = _flatten_d(config)

                for host_type in host_types:
                    host_type_dir = os.path.join(rep_dir, host_type)
                    hosts = _list_dir_only(host_type_dir)

                    for host_idx, host in enumerate(hosts):
                        host_dir = os.path.join(host_type_dir, host)
                        files = _list_files_only(host_dir)

                        job_info = {
                            "suite_name": suite,
                            "suite_id": suite_id,
                            "exp_name": exp,
                            "run": int(run.split("_")[-1]),
                            "rep": int(rep.split("_")[-1]),
                            "host_type": host_type,
                            "host_idx": host_idx,
                            "factor_columns": factor_columns
                        }

                        for file in files:
                            d_lst = _parse_file(host_dir, file, extractors)
                            for d in d_lst:
                                d_flat = _flatten_d(d)
                                res = {**job_info, **config_flat, **d_flat}
                                res_lst.append(res)

    df = pd.DataFrame(res_lst)
    return df


def _parse_file(path: str, file:str, extractors: List[Dict]) -> List[Dict]:
    has_match = False

    for extractor_d in extractors:

        patterns = extractor_d['extractor'].regex
        if not isinstance(patterns, list):
            patterns = [patterns]

        for p in patterns:
            regex = re.compile(p)

            if regex.match(file):

                # we want to assign one extractor per file
                if has_match :
                    raise ValueError(f"file={file} matches multiple extractors (path={path})")

                file_path = os.path.join(path, file)
                d_lst = extractor_d["extractor"].extract(path=file_path, options=extractor_d["options"])

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
    for k, v, path in _nested_dict_iter(experiment['base_experiment']):
        # k: the key (i.e. the name of the config option, unless it's a factor, than the content is just $FACTOR$)
        # v: the value or a list of levels in case it's a factor
        # path: to support nested config dicts, path keep tracks of all the parent nodes of k (empty if it is on the top level)

        if k == "$FACTOR$":
            # inline factor
            factor = path[-1]
            factor_columns.append(factor)
        elif v == "$FACTOR$":
            # factor defined in factor_levels
            factor_columns.append(k)

    return factor_columns

def _load_config_yaml(path, file="config.json"):
    with open(os.path.join(path, file)) as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    return config

def _list_dir_only(path):
    return [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]

def _list_files_only(path):
    return [f for f in os.listdir(path) if not os.path.isdir(os.path.join(path, f))]

def _flatten_d(d):
    return json.loads(pd.json_normalize(d, sep='.').iloc[0].to_json())


if __name__ == "__main__":

    #parser = argparse.ArgumentParser(description="")
    #parser.add_argument("--suite", type=str, required=True)
    #parser.add_argument("--id", type=str, required=True)
    #args = parser.parse_args()

    main()
