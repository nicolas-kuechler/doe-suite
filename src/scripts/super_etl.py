import os, sys, importlib, re, warnings
import yaml, json, argparse
from inspect import getmembers
import pandas as pd
from typing import List, Dict


def run_multi_suite(config):

    if "DOES_PROJECT_DIR" not in os.environ:
        raise ValueError(f"env variable: DOES_PROJECT_DIR not set")
    prj_dir = os.environ["DOES_PROJECT_DIR"]
    results_dir = os.path.join(prj_dir, "does_results")
    suite_dir = os.path.join(results_dir, f"{suite}_{suite_id}")

    # load etl_config by loading suite design file
    suite_design = _load_config_yaml(suite_dir, file="suite_design.yml")
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
            df = extract(suite=suite, suite_id=suite_id, suite_dir=suite_dir, experiments=pipeline["experiments"], base_experiments=suite_design, extractors=extractors)

            # apply transformers sequentially
            for x in transformers:
                df = x["transformer"].transform(df, options=x["options"])

            # execute all loaders on df
            for x in loaders:
                x["loader"].load(df, options=x["options"], etl_info=etl_info)
        except:
            print(f"An error occurred in pipeline {pipeline_name}!", etl_info)
            raise


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--config", type=str, required=True, description="Path to super etl config file")
    args = parser.parse_args()

    run_multi_suite(config=config)
