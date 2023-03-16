import os
import re
import jinja2
import json


from doespy import util


def validate(suite_design_raw, suite, exp_filter):

    from doespy.design import exp_design

    _validate_setup()

    # validate the raw design against the pydantic model (+ set default values)
    model = exp_design.dict_to_pydantic(suite_name=suite, suite_design_raw=suite_design_raw)

    # convert back from model to dict (because remaining things depend on this style)
    suite_design = exp_design.pydantic_to_dict(model)


    # filter out experiments which should not be run
    if exp_filter is not None:
        _apply_experiment_re_filter(design_raw=suite_design, exp_filter=exp_filter)

    #print(f"Suite Design:")
    #print("================================")
    #print(suite_design)
    #print("================================")

    return suite_design



def _validate_setup():

    # check group vars `all`
    groupvars_all_path = os.path.join(util.get_suite_group_vars_dir(), "all", "main.yml")
    assert os.path.isfile(groupvars_all_path),  f"group_vars all not found -> file does not exist ({groupvars_all_path})"


    # TODO [nku] could add a check that environment vars are set

    # TODO [nku] could validate folder structure of doe-suite-config


def _apply_experiment_re_filter(design_raw, exp_filter):
    pattern = re.compile(exp_filter)
    filtered_out_exp_names = []
    for exp_name in design_raw.keys():
        if exp_name in ["$ETL$"]:
            continue
        if not pattern.match(exp_name):
            filtered_out_exp_names.append(exp_name)

    # delete the skipped experiments
    for exp_name in filtered_out_exp_names:
        del design_raw[exp_name]

    etl_pipelines_to_delete = []
    for key, pipeline in design_raw.get("$ETL$", {}).items():
        pipeline["experiments"] = list(
            filter(lambda x: x not in filtered_out_exp_names, pipeline["experiments"])
        )

        # no experiments left -> can delete etl pipeline
        if len(pipeline["experiments"]) == 0:
            etl_pipelines_to_delete.append(key)

    # delete the surplus etl pipelines
    for pipeline in etl_pipelines_to_delete:
        d = design_raw["$ETL$"]
        del d[pipeline]



if __name__ == "__main__":

    suites = ["example01-minimal", "example02-single", "example03-format", "example04-multi", "example05-complex", "example06-vars", "example07-etl"]
    for suite in suites:
    #suite = "example07-etl"
        suite_design = util.get_suite_design(suite=suite)

        validate(suite_design_raw=suite_design, prj_id=util.get_project_id(), suite=suite, exp_filter=None)