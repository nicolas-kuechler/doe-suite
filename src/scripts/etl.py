import os, sys, importlib, re, warnings
import yaml, json, argparse
from inspect import getmembers
import pandas as pd
from typing import List, Dict


def main(suite, suite_id):

    if "DOES_PROJECT_DIR" not in os.environ:
        raise ValueError(f"env variable: DOES_PROJECT_DIR not set")
    prj_dir = os.environ["DOES_PROJECT_DIR"]
    results_dir = os.path.join(prj_dir, "does_results")
    suite_dir = os.path.join(results_dir, f"{suite}_{suite_id}")

    # load etl_config by loading suite design file
    suite_design =  _load_config_yaml(suite_dir, file="suite_design.yml")
    if "$ETL$" not in suite_design:
        # we don't have an ETL config => don't run it
        return
    etl_config = suite_design["$ETL$"]

    # go over pipelines and run them
    for pipeline_name, pipeline in etl_config.items():

        etl_info = {
            "suite": suite, "suite_id": suite_id, "pipeline": pipeline_name, "experiments": pipeline["experiments"], "suite_dir": suite_dir
        }

        extractors, transformers, loaders = load_selected_processes(pipeline["extractors"], pipeline["transformers"], pipeline["loaders"])

        try:    
            # extract data from
            df = extract(suite=suite, suite_id=suite_id, suite_dir=suite_dir, experiments=pipeline["experiments"], extractors=extractors)

            # apply transformers sequentially
            for x in transformers:
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

        if trans_sel['name'] not in transformers_avl:
            raise ValueError(f"transformer not found: {trans_sel['name']}")

        d = {
            "transformer": transformers_avl[trans_sel["name"]](),
            "options": trans_sel,
        }
        transformers.append(d)

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

    # load processes in current directory
    _load_processes("etl_base", extractors, transformers, loaders)

    # load processes from external project directory (i.e., project specific steps)
    prj_dir = os.environ["DOES_PROJECT_DIR"]
    external_etl_dir = os.path.join(prj_dir, "does_config", "etl")

    external_dirs = _find_external_processes_dir(external_etl_dir)

    # ensure that we can load modules from the directory
    for external_dir in external_dirs:
        sys.path.append(external_dir)

    # check all files in the external directory
    for external_dir in external_dirs:
        for x in os.listdir(external_dir):
            parts = os.path.splitext(x)
            if parts[1] == ".py":
                module_name = parts[0]
                _load_processes(module_name, extractors, transformers, loaders)
    return extractors, transformers, loaders

def _find_external_processes_dir(base_dir):
    dirs = []
    # walk over all subdirectories recursively
    for dirpath, _, filenames in os.walk(base_dir):
        for file in filenames:
            if file.endswith(".py"): # only use directories with python files
                dirs.append(dirpath)
                break
    return dirs

def _load_processes(module_name, extractors, transformers, loaders):

    from etl_base import Extractor, Transformer, Loader

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

def extract(suite:str, suite_id: str, suite_dir: str, experiments: List[str], extractors: List[Dict]) -> pd.DataFrame:
    res_lst = []

    existing_exps = _list_dir_only(suite_dir)

    exps_filtered = [exp for exp in existing_exps if exp in experiments]

    for exp in exps_filtered:
        exp_dir = os.path.join(suite_dir, exp)
        runs = _list_dir_only(exp_dir)

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
                            "host_idx": host_idx
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

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--suite", type=str, required=True)
    parser.add_argument("--id", type=str, required=True)
    args = parser.parse_args()

    main(suite=args.suite, suite_id=args.id)
