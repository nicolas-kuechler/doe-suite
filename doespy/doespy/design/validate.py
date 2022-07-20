import yaml, os, re
from collections import abc

from doespy import util

KEYWORDS = {
    "general": ["state", "$FACTOR$", 'is_controller_yes', 'is_controller_no', 'check_status_yes', 'check_status_no', 'localhost'],
    "exp": ["n_repetitions", "common_roles", "host_types", "base_experiment", "factor_levels"],
    "host_type":  ["n", "init_roles", "check_status", "$CMD$"]
}

def validate(suite_design, prj_id, suite, dirs, exp_filter):

    # check group vars `all`
    groupvars_all_path = os.path.join(dirs["groupvars"], "all", "main.yml")
    if not os.path.isfile(groupvars_all_path):
        raise ValueError(f"group_vars all not found -> file does not exist ({groupvars_all_path})")

    _validate_and_default_suite(prj_id=prj_id, suite=suite, design_raw=suite_design, dirs=dirs)

    if exp_filter is not None:
        _apply_experiment_re_filter(design_raw=suite_design, exp_filter=exp_filter)

    return suite_design


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
        pipeline["experiments"] = list(filter(lambda x: x not in filtered_out_exp_names, pipeline["experiments"]))

        # no experiments left -> can delete etl pipeline
        if len(pipeline["experiments"]) == 0:
            etl_pipelines_to_delete.append(key)

    # delete the surplus etl pipelines
    for pipeline in etl_pipelines_to_delete:
        d = design_raw["$ETL$"]
        del d[pipeline]


def _validate_and_default_suite(prj_id, suite, design_raw, dirs):

        exp_names = []

        suite_vars = design_raw.get("$SUITE_VARS$", {})

        if "$SUITE_VARS$" in design_raw:
            del design_raw["$SUITE_VARS$"]

        host_type_names = []
        for key, exp in design_raw.items():
            if key in ["$ETL$"]:
                continue
            exp_names.append(key)

            host_type_names += list(exp["host_types"].keys())
        host_type_names = list(set(host_type_names)) # remove duplicates

        keywords_all = []
        for keyword_lst in KEYWORDS.values():
            keywords_all += keyword_lst

        expected_unique = [prj_id, suite] + exp_names + host_type_names + keywords_all

        if len(set(expected_unique)) != len(expected_unique):

            seen = set()
            duplicates = [x for x in expected_unique if x in seen or seen.add(x)]

            raise ValueError(f"found duplicates in identifiers -> adjust prj_id, suite, host_type, or exp_name to avoid them (identifiers={ expected_unique }   duplicates={duplicates})")

        # check length limit of project id and suite (tag on aws has a limit)
        if len(prj_id) > 200:
            raise ValueError("project id too long")

        if len(suite) > 200:
            raise ValueError("suite name too long")

        for exp_name in exp_names:
            if len(exp_name) > 200:
                raise ValueError("exp_name too long")

            if not re.match(r'^[A-Za-z0-9_]+$', exp_name):
                raise ValueError(f"exp_name must consist of alphanumeric chars or underscores ({exp_name})")

        if "$ETL$" not in design_raw:
            design_raw["$ETL$"] = {}

        for key, value in design_raw.items():
            if key == "$ETL$":
                include_etl_pipelines(etl_pipelines=value)
                _validate_etl_pipeline(etl_pipelines=value)

            else:
                _validate_and_default_experiment(value, dirs, suite_vars)

        return True



def include_etl_pipelines(etl_pipelines):
    for name, config in etl_pipelines.items():
        include_etl_pipeline(etl_pipeline=config)
        include_etl_steps(etl_pipeline=config)
        etl_pipelines[name] = include_etl_vars(etl_pipeline=config)



def include_etl_vars(etl_pipeline):

    if "$ETL_VARS$" in etl_pipeline:
        etl_vars = etl_pipeline.pop("$ETL_VARS$")

        import jinja2, json
        env = util.jinja2_env(loader=None, undefined=jinja2.StrictUndefined, variable_start_string="[%", variable_end_string="%]")
        template = json.dumps(etl_pipeline)
        while "[%" in template and "%]" in template:
            template = env.from_string(template)
            template = template.render(**etl_vars)
        etl_pipeline = json.loads(template)
    return etl_pipeline



def load_etl_steps(cfg, stage):
    suite = etl_load_suite(cfg)

    ETL_KEY = "$ETL$"

    if ETL_KEY in suite and cfg["pipeline"] in suite[ETL_KEY] and stage in suite[ETL_KEY][cfg["pipeline"]]:
        return suite[ETL_KEY][cfg["pipeline"]][stage]
    else:
        raise ValueError(f"pipeline {cfg['pipeline']} stage {stage} not found in {cfg}")

def include_etl_steps(etl_pipeline):

    KEY = "$INCLUDE_STEPS$"

    for name, config in etl_pipeline.items():
        if name in ["experiments", "$ETL_VARS$"]:
            continue
        elif name == "transformers":
            steps = []
            for step in config:
                if KEY in step:
                    if len(step)==1:
                        for loaded_step in load_etl_steps(cfg=cfg, stage=name):
                           steps.append(loaded_step)
                    else:
                        raise ValueError(f"{KEY} must be unique in step={step}")
                else:
                    steps.append(step)
            etl_pipeline[name] = steps

        elif name == "extractors" or name == "loaders":
            if KEY in config:
                cfg_lst = config[KEY]
                del config[KEY]

                for cfg in cfg_lst:
                    for step_name, step_cfg in load_etl_steps(cfg=cfg, stage=name).items():

                        if step_name == KEY:
                            raise ValueError(f"cannot include etl steps recursively (cfg={cfg} stage={name} has step={step_name}")
                        # set the step (if not already present)
                        if step_name not in config:
                            config[step_name] = step_cfg

        else:
            raise ValueError(f"unknown part of etl pipeline name={name}  config={config}")


def etl_load_suite(cfg):

    if "suite" in cfg:
        if os.path.isfile(os.path.join(util.get_suite_design_dir(), f"{cfg['suite']}.yml")):
            suite = util.get_suite_design(cfg['suite'])
        else:
            raise ValueError(f"ETL import failed suite={cfg['suite']} not found")

    elif "template" in cfg:
        template_dir = os.path.join(util.get_suite_design_dir(), "etl_templates")
        if os.path.isfile(os.path.join(template_dir, f"{cfg['template']}.yml")):
            suite = util.get_suite_design(suite=cfg['template'], folder=template_dir)
        else:
            raise ValueError(f"ETL import failed template={cfg['template']} not found")
    else:
        raise ValueError(f"wrong format: expect `suite` or `template` ({cfg})")

    return suite



def include_etl_pipeline(etl_pipeline):

    KEY = "$INCLUDE_PIPELINE$"
    ETL_KEY = "$ETL$"

    if  KEY in etl_pipeline:

        cfg=etl_pipeline[KEY]

        # load entire pipeline
        suite = etl_load_suite(cfg)

        if ETL_KEY in suite and cfg["pipeline"] in suite[ETL_KEY]:
            pipeline = suite[ETL_KEY][cfg["pipeline"]]
            # copy pipeline except `experiments`
            for stage_name, stage in pipeline.items():
                if stage_name != "experiments":
                    etl_pipeline[stage_name] = stage
            del etl_pipeline[KEY] # delete the include entry
        else:
            raise ValueError(f"pipeline {cfg['pipeline']} not found in suite {cfg['suite']}")



def _validate_etl_pipeline(etl_pipelines):

    for name, config in etl_pipelines.items():

        if "experiments" not in config.keys() or not (isinstance(config["experiments"], list) or config["experiments"] == "*"):
            raise ValueError(f"missing required list of experiments name={name}  config={config}")

        if "extractors" not in config.keys():
            raise ValueError(f"missing extractors: {name}")

        for ext_name, ext_config in config["extractors"].items():
            if ext_config is None:
                raise ValueError(f"extractor={ext_name} cannot be null -> use {{}} for no options")

        if "transformers" not in config.keys():
            config["transformers"] = []
        elif not isinstance(config["transformers"], list):
            raise ValueError(f"transformers in pipeline={name} is not a list")

        if "loaders" not in config.keys():
            raise ValueError(f"loader in pipeline={name} missing")

        for load_name, load_config in config["loaders"].items():
            if load_config is None:
                raise ValueError(f"loader={load_name} cannot be null -> use {{}} for no options")

def _validate_and_default_experiment(exp_raw, dirs, suite_vars):

    exp_keywords = KEYWORDS["exp"]
    exp_keywords_required = ["n_repetitions", "host_types"]

    if any(x not in exp_keywords for x in exp_raw.keys()):
        raise ValueError("unknown entry in experiment")

    if any(x not in exp_raw.keys() for x in exp_keywords_required):
        raise ValueError("missing required keyword")

    if "base_experiment" not in exp_raw:
        exp_raw["base_experiment"] = {}

    # set default values for not required keywords (common_roles, factor_levels)
    if "common_roles" not in exp_raw:
        exp_raw["common_roles"] = []

    # convert common role to list
    if isinstance(exp_raw["common_roles"], str):
        exp_raw["common_roles"] = [exp_raw["common_roles"]]

    if not isinstance(exp_raw["common_roles"], list):
        raise ValueError("common_roles must be a list")

    # check that common role actually exists
    for common_role in exp_raw["common_roles"]:
        role_path = os.path.join(dirs["roles"], common_role, "tasks")
        if not os.path.isdir(role_path):
            raise ValueError(f"common_role={common_role} not found -> dir does not exist ({role_path})")

    if "factor_levels" not in exp_raw:
        exp_raw["factor_levels"] = [{}]

    # set suite vars (if not present in exp_base)
    _include_vars(exp_raw["base_experiment"], suite_vars)

    # load external vars (marked with $INCLUDE_VARS$)
    _load_external_vars(exp_raw["base_experiment"], dirs["designvars"])

    # handle host_types
    for host_type_name, host_type_raw in exp_raw["host_types"].items():
        _validate_and_default_host_type(host_type_name, host_type_raw, dirs)

    # check base_experiment
    expected_factor_paths = _validate_base_experiment(exp_raw["base_experiment"])

    # check factor levels
    _validate_factor_levels(exp_raw["factor_levels"], expected_factor_paths)

def _load_external_vars(conf, external_dir):

    for path, value in nested_dict_iter(conf.copy()):

        if path[-1] == "$INCLUDE_VARS$":
            d = conf
            for p in path[:-1]:
                d = d[p]

            del d["$INCLUDE_VARS$"]

            if isinstance(value, str):
                value = [value]

            for external_file in value: #
                # value is the path relative to external dir
                with open(f"{external_dir}/{external_file}", "r") as f:
                    vars = yaml.load(f, Loader=yaml.SafeLoader)
                _include_vars(d, vars)

def _include_vars(base, vars):
    for path, value in nested_dict_iter(vars):
        _set_nested_value(base, path, value)


def _validate_and_default_host_type(host_type_name, host_type_raw, dirs):

    # TODO [nku] many of these checks could probably be replaced by json schema

    host_type_keywords = KEYWORDS["host_type"]

    if any(x not in host_type_keywords for x in host_type_raw.keys()):
        raise ValueError("illegal keyword in host type")

    if "$CMD$" not in host_type_raw:
        raise ValueError("$CMD$ must be in host_type")

    ############
    # Check that group vars exist
    groupvars_path = os.path.join(dirs["groupvars"], host_type_name)
    if not os.path.isdir(groupvars_path):
        raise ValueError(f"group_vars for host_type={host_type_name} not found -> folder does not exist ({groupvars_path})")


    #############
    # Set check_status: True if not set
    if "check_status" not in host_type_raw:
        host_type_raw["check_status"] = True

    #############
    # set n by default to 1
    if "n" not in host_type_raw:
        host_type_raw["n"] = 1

    #############
    # set init_roles by default to empty list
    if "init_roles" not in host_type_raw:
        host_type_raw["init_roles"] = []

    #############
    # convert init role to list
    if isinstance(host_type_raw["init_roles"], str):
        host_type_raw["init_roles"] = [host_type_raw["init_roles"]]

    if not isinstance(host_type_raw["init_roles"], list):
        raise ValueError("init_roles must be a list")

    for init_role in host_type_raw["init_roles"]:
        role_path = os.path.join(dirs["roles"], init_role, "tasks")
        if not os.path.isdir(role_path):
            raise ValueError(f"init_role={init_role} not found -> dir does not exist ({role_path})")

    #############
    # Convert $CMD$ to default structure

    if not isinstance(host_type_raw["$CMD$"], list):
        # repeat the same cmd for all `n` hosts of this type
        host_type_raw["$CMD$"] = [host_type_raw["$CMD$"]] * host_type_raw["n"]


    if len(host_type_raw["$CMD$"]) != host_type_raw["n"]:
        raise ValueError("cmd list length does not match the number of instances `n` of host type")

    # host_type_raw["$CMD$"] is a list of length n
    cmds = []
    for cmd in host_type_raw["$CMD$"]:
        if isinstance(cmd, str):
            cmd = {"main": cmd}
        elif isinstance(cmd, dict):
            if "main" not in cmd:
                raise ValueError("missing cmd for main")
        else:
            raise ValueError("unknown type")
        cmds.append(cmd)

    host_type_raw["$CMD$"] = cmds
    # host_type_raw["$CMD$"] is a list of length n, each element is a dict that contains at least one entry with key "main"

    """
    # minimal example
    n: 1
    $CMD$:
        - main: X

    # two instances, one command
    n: 2
    $CMD$:
        - main: X
        - main: Y

    # two instances, multiple commands per instance
    n: 2
    $CMD$:
        - main: X
        monitor: Z  # on first host instance also start `monitor` cmd Z
        - main: Y

    """


def _validate_base_experiment(base_experiment_raw):
    factors = []
    #extract `path`of all factors from base experiment

    for path, value in nested_dict_iter(base_experiment_raw):

        if value == "$FACTOR$":
            factors.append(path)

        if path[-1] == "$FACTOR$":
            if isinstance(value, str):

                # add support for the range syntax in factors
                if "range" not in value:
                    raise ValueError(f"if $FACTOR$ is the key, the only allowed string is the range syntax:   got=|{value}|")

            elif not isinstance(value, list):
                raise ValueError(f"if $FACTOR$ is the key, then the value must be a list of levels used in the cross product (path={path} value={value})")

    return factors


def _validate_factor_levels(factor_levels_raw, expected_factors):

    if not isinstance(factor_levels_raw, list):
        raise ValueError("factor levels must be a list")

    for run in factor_levels_raw:

        actual_factors = []
        for path, value in nested_dict_iter(run):
            actual_factors.append(path)

        if sorted(expected_factors) != sorted(actual_factors):
            raise ValueError(f"expected factors do not match actual factors: expected={expected_factors} actual={actual_factors}")






def nested_dict_iter(nested, path=[]):
    for key, value in nested.items():
        path_c = path + [key]

        if isinstance(value, abc.Mapping):
            yield from nested_dict_iter(value, path=path_c)
        else:
            yield path_c, value


def _set_nested_value(base, path, value, overwrite=False):

    d = base
    for i, k in enumerate(path):

        if k not in d:
            if i == len(path)-1: # last
                d[k] = value
            else:
                d[k] = {}
        elif overwrite and i == len(path)-1: # last + overwrite
            d[k] = value

        d = d[k]
