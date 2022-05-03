import os, sys, importlib, re, warnings
import yaml, json, argparse
from inspect import getmembers
import pandas as pd
from typing import List, Dict

from etl import _load_config_yaml, load_selected_processes, extract


def run_multi_suite(config_name: str,
                    output_path: str, flag_output_dir_config_name: bool = True, flag_output_dir_pipeline: bool = True,
                    return_df=False):

    if "DOES_PROJECT_DIR" not in os.environ:
        raise ValueError(f"env variable: DOES_PROJECT_DIR not set")
    prj_dir = os.environ["DOES_PROJECT_DIR"]
    config_dir = os.path.join(prj_dir, "does_config", "super_etl")
    results_dir = os.path.join(prj_dir, "does_results")

    # load etl_config by loading suite design file
    pipeline_design = _load_config_yaml(config_dir, file=config_name)
    if "$ETL$" not in pipeline_design:
        # we don't have an ETL config => don't run it
        return
    if "$SUITE_ID$" not in pipeline_design:
        print("Must specify concrete suite ids to load from!")
        return
    etl_config = pipeline_design["$ETL$"]
    suite_id_map = pipeline_design["$SUITE_ID$"]

    output_dfs = {}
    # go over pipelines and run them
    for pipeline_name, pipeline in etl_config.items():

        experiments = pipeline["experiments"]
        # extract suites here

        extractors, transformers, loaders = load_selected_processes(pipeline["extractors"], pipeline["transformers"], pipeline["loaders"])

        experiments_df = pd.DataFrame()
        for suite, experiments in experiments.items():

            experiment_suite_id_map = _extract_experiments_suite(suite, experiments, suite_id_map)
            for experiment, suite_id in experiment_suite_id_map.items():

                suite_dir = os.path.join(results_dir, f"{suite}_{suite_id}")
                suite_design = _load_config_yaml(suite_dir, file="suite_design.yml")
                etl_info = {
                    "suite": suite, "suite_id": suite_id, "pipeline": pipeline_name, "experiments": [experiment], "suite_dir": suite_dir
                }

                try:
                    # extract data from
                    df = extract(suite=suite, suite_id=suite_id, suite_dir=suite_dir, experiments=[experiment], base_experiments=suite_design, extractors=extractors)

                    experiments_df = experiments_df.append(df)
                except:
                    print(f"An error occurred in extractor from pipeline {pipeline_name}!", etl_info)
                    raise

        output_dir = _get_output_dir_name(prj_dir, output_path,
                                          config_name, pipeline_name,
                                          flag_output_dir_config_name, flag_output_dir_pipeline)
        # ensure dir exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        df = experiments_df
        etl_info = {
            "suite": None, "suite_id": None, "pipeline": pipeline_name, "experiments": experiments,
            "suite_dir": output_dir # overwrite output dir to super etl dir
        }
        try:
            # apply transformers sequentially
            for x in transformers:
                df = x["transformer"].transform(df, options=x["options"])

            if return_df:
                output_dfs[pipeline_name] = df
            else:
                # execute all loaders on df
                for x in loaders:
                    x["loader"].load(df, options=x["options"], etl_info=etl_info)

        except:
            print(f"An error occurred in pipeline {pipeline_name}!", etl_info)
            raise

    if return_df:
        # for use in jupyter notebooks
        return output_dfs


def _extract_experiments_suite(suite, experiments, suite_id_map):
    """
    :param experiments list of experiments
    :param suite_id_map dict can be a dict of (suite, suite_id), or (suite, dict) where dict is a dict of experiment-level id
    :return: dict Experiment to suite mapping
    """
    suite_ids = suite_id_map[suite]

    if isinstance(suite_ids, str) or isinstance(suite_ids, int):
        # suite-wide id
        return {
            experiment: suite_ids for experiment in experiments
        }
    elif isinstance(suite_ids, dict):
        # dict { experiment: id }
        default = suite_ids.get('$DEFAULT$', None)
        return {
            experiment: suite_ids.get(experiment, default) for experiment in experiments
        }
    else:
        raise ValueError(f"Suite ids must be a value or dict!")


def _get_output_dir_name(prj_dir: str, output_path: str,
                         config_name: str, pipeline_name: str,
                         flag_output_dir_config_name: bool, flag_output_dir_pipeline: bool) -> str:
    """Generates output directory based on options and current pipeline."""
    if not os.path.isabs(output_path):
        # assume we want to be relative to DOES_PROJECT_DIR
        output_path = os.path.join(prj_dir, output_path)

    if flag_output_dir_config_name:
        config_prefix_regex = r"^(.*)\.yml$"
        config_prefix = re.match(config_prefix_regex, config_name).group(1)
        assert config_prefix is not None, f"Filename {config_name} has invalid format and cant be extracted!"
        output_path = os.path.join(output_path, config_prefix)

    if flag_output_dir_pipeline:
        output_path = os.path.join(output_path, pipeline_name)

    return output_path

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--output_path", type=str, default="does_results/super_etl", required=False)
    parser.add_argument("--output_dir_config_name_disabled", action='store_true',
                        help="Whether to output in a subdirectory with the name of the super_etl config file.")
    parser.add_argument("--output_dir_pipeline", action='store_false',
                        help="Whether to output in a subdirectory with the name of the pipeline.")
    args = parser.parse_args()

    run_multi_suite(config_name=args.config,
                    output_path=args.output_path,
                    flag_output_dir_config_name=not args.output_dir_config_name_disabled,
                    flag_output_dir_pipeline=not args.output_dir_pipeline)
