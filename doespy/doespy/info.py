from doespy import util
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
        for exp in sorted(get_experiments(suite)):
            print(f"   {exp}")
    print("------------------")


def get_suite_designs(designs_dir=None):

    if designs_dir is None:
        designs_dir = util.get_suite_design_dir()

    designs_dir = os.path.join(designs_dir, "*.yml")

    designs = []
    for path in glob.glob(designs_dir):

        suite = os.path.splitext(os.path.basename(path))[0]
        designs.append(suite)
    return designs


def get_experiments(suite):
    exps = []
    design = util.get_suite_design(suite)
    for exp_name in design.keys():
        if not exp_name.startswith("$"):
            exps.append(exp_name)
    return exps


def get_etl_pipelines(suite, designs_dir=None):
    design = util.get_suite_design(suite, folder=designs_dir)
    if "$ETL$" in design:
        pipelines = list(design["$ETL$"].keys())
    else:
        pipelines = []
    return pipelines


if __name__ == "__main__":
    display_info()
