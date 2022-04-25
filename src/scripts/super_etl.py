import os, sys, importlib, re, warnings
import yaml, json, argparse
from inspect import getmembers
import pandas as pd
from typing import List, Dict

from etl import _load_config_yaml, load_selected_processes, extract


def run_multi_suite(config_name, return_df=False):

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

    # go over pipelines and run them
    for pipeline_name, pipeline in etl_config.items():

        experiments = pipeline["experiments"]
        # extract suites here

        extractors, transformers, loaders = load_selected_processes(pipeline["extractors"], pipeline["transformers"], pipeline["loaders"])

        experiments_df = pd.DataFrame()
        for experiment_full in experiments:

            experiment_components = experiment_full.split(":")
            assert len(experiment_components) > 1, f"Experiments must be specified with a `suite:` prefix!" \
                                                   f"\nExperiment: {experiment_full}"
            suite = experiment_components[0]
            experiment = experiment_components[1]

            if suite not in suite_id_map.keys():
                raise ValueError(f"No suite id specified for {suite}! Specify in $SUITE_ID$")

            suite_id = suite_id_map[suite]
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

        df = experiments_df
        etl_info = {
            "suite": None, "suite_id": None, "pipeline": pipeline_name, "experiments": experiments,
            "suite_dir": config_dir # overwrite output dir to super etl dir
        }
        try:
            # apply transformers sequentially
            for x in transformers:
                df = x["transformer"].transform(df, options=x["options"])

            # execute all loaders on df
            for x in loaders:
                x["loader"].load(df, options=x["options"], etl_info=etl_info)
        except:
            print(f"An error occurred in pipeline {pipeline_name}!", etl_info)
            raise

    if return_df:
        # for use in jupyter notebooks
        return df


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--config", type=str, required=True)
    args = parser.parse_args()

    run_multi_suite(config_name=args.config)
