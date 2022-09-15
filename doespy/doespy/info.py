from doespy import util
from doespy.design import validate_extend

import os
import glob


def display_info():
    print(f"Project: {util.get_project_dir()}")
    print(f"Project Id: {util.get_project_id()}")

    print("Suites")
    print("------------------")
    for suite in sorted(get_suite_designs()):
        etl = "x" if len(get_etl_pipelines(suite)) > 0 else " "
        pad = (30 - len(suite)) * " "
        print(f"{suite} {pad}etl[{etl}]")
        for exp in sorted(get_experiments(suite), key=lambda x: x["exp_name"]):
            print(f"   {exp['exp_name']}  ({exp['n_runs']} runs) ")
    print("------------------")


def get_suite_designs():

    config_dir = util.get_config_dir()
    designs_dir = os.path.join(config_dir, "designs", "*.yml")

    designs = []
    for path in glob.glob(designs_dir):

        suite = os.path.splitext(os.path.basename(path))[0]
        designs.append(suite)
    return designs


def get_experiments(suite):
    exps = []

    _suite_design, suite_design_ext = validate_extend.main(
        suite=suite,
        ignore_undefined_vars=True,
    )


    for exp_name, runs in suite_design_ext.items():
        exps.append({"exp_name": exp_name, "n_runs": len(runs)})

    return exps


def get_etl_pipelines(suite):
    design = util.get_suite_design(suite)
    if "$ETL$" in design:
        pipelines = list(design["$ETL$"].keys())
    else:
        pipelines = []
    return pipelines


if __name__ == "__main__":
    display_info()
