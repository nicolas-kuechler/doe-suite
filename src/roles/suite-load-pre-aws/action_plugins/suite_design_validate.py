# based on: https://gist.github.com/ju2wheels/408e2d34c788e417832c756320d05fb5

# Standard base includes and define this as a metaclass of type
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import yaml, os, re
from collections import abc

from ansible.utils.vars import merge_hash
from ansible.plugins.action import ActionBase

# Load the display hander to send logging to CLI or relevant display mechanism
try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()

class UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        mapping = []
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise AssertionError(f"duplicate key={key}")
            mapping.append(key)

        return super().construct_mapping(node, deep)


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

class ActionModule(ActionBase):

    TRANSFERS_FILES = False

    keywords = {
            "general": ["state", "suite_design", "$FACTOR$", 'is_controller_yes', 'is_controller_no', 'check_status_yes', 'check_status_no', 'localhost'],
            "exp": ["n_repetitions", "common_roles", "host_types", "base_experiment", "factor_levels"],
            "host_type":  ["n", "init_roles", "check_status", "$CMD$"]
    }

    def run(self,  tmp=None, task_vars=None):

        result = super(ActionModule, self).run(tmp, task_vars)

        # Initialize result object with some of the return_common values:
        result.update(
            dict(
                changed=False,
                failed=False,
                msg='',
                skipped=False
            )
        )

        # extract argument from module
        module_args = self._task.args
        src = module_args["src"]
        dest = module_args["dest"]

        dirs = {
            "designvars": module_args["prj_designvars_dir"],
            "groupvars": module_args["prj_groupvars_dir"],
            "roles": module_args["prj_roles_dir"]
        }

        prj_id = task_vars["prj_id"]

        suite = os.path.splitext(os.path.basename(src))[0]

        # check group vars `all`
        groupvars_all_path = os.path.join(dirs["groupvars"], "all", "main.yml")
        if not os.path.isfile(groupvars_all_path):
            raise ValueError(f"group_vars all not found -> file does not exist ({groupvars_all_path})")

        try:
            with open(src) as f:
                design_raw = yaml.load(f, Loader=UniqueKeyLoader)
                self._validate_and_default_suite(prj_id=prj_id, suite=suite, design_raw=design_raw, dirs=dirs)

            with open(dest, 'w+') as f:
                yaml.dump(design_raw, f, sort_keys=False, width=10000)

        except AssertionError as e:
            raise ValueError("duplicate keys (experiment names)")


        return result


    def _validate_and_default_suite(self, prj_id, suite, design_raw, dirs):

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
        for keyword_lst in self.keywords.values():
            keywords_all += keyword_lst

        expected_unique = [prj_id, suite] + exp_names + host_type_names + keywords_all

        if len(set(expected_unique)) != len(expected_unique):
            raise ValueError(f"found duplicates in identifiers -> adjust prj_id, suite, host_type, or exp_name to avoid them (identifiers={ expected_unique })")

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
                self._validate_etl_pipeline(etl_pipelines=value)
            else:
                self._validate_and_default_experiment(value, dirs, suite_vars)

        return True

    def _validate_etl_pipeline(self, etl_pipelines):

        for name, config in etl_pipelines.items():

            if "experiments" not in config.keys() or not isinstance(config["experiments"], list):
                raise ValueError(f"missing required list of experiments name={name}  config={config}")

            if "extractors" not in config.keys():
                raise ValueError("missing extractors")


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

    def _validate_and_default_experiment(self, exp_raw, dirs, suite_vars):

        exp_keywords = self.keywords["exp"]
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
            role_path = os.path.join(dirs["roles"], common_role, "tasks", "main.yml")
            if not os.path.isfile(role_path):
                raise ValueError(f"common_role={common_role} not found -> file does not exist ({role_path})")

        if "factor_levels" not in exp_raw:
            exp_raw["factor_levels"] = [{}]

        # set suite vars (if not present in exp_base)
        self._include_vars(exp_raw["base_experiment"], suite_vars)

        # load external vars (marked with $INCLUDE_VARS$)
        self._load_external_vars(exp_raw["base_experiment"], dirs["designvars"])

        # handle host_types
        for host_type_name, host_type_raw in exp_raw["host_types"].items():
            self._validate_and_default_host_type(host_type_name, host_type_raw, dirs)

        # check base_experiment
        expected_factor_paths = self._validate_base_experiment(exp_raw["base_experiment"])

        # check factor levels
        self._validate_factor_levels(exp_raw["factor_levels"], expected_factor_paths)

    def _load_external_vars(self, conf, external_dir):

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
                    self._include_vars(d, vars)

    def _include_vars(self, base, vars):
        for path, value in nested_dict_iter(vars):
            _set_nested_value(base, path, value)


    def _validate_and_default_host_type(self, host_type_name, host_type_raw, dirs):

        # TODO [nku] many of these checks could probably be replaced by json schema

        host_type_keywords = self.keywords["host_type"]

        if any(x not in host_type_keywords for x in host_type_raw.keys()):
            raise ValueError("illegal keyword in host type")

        if "$CMD$" not in host_type_raw:
            raise ValueError("$CMD$ must be in host_type")

        ############
        # Check that group vars exist
        groupvars_path = os.path.join(dirs["groupvars"], host_type_name, "main.yml")
        if not os.path.isfile(groupvars_path):
            raise ValueError(f"group_vars for host_type={host_type_name} not found -> file does not exist ({groupvars_path})")


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
            role_path = os.path.join(dirs["roles"], init_role, "tasks", "main.yml")
            if not os.path.isfile(role_path):
                raise ValueError(f"init_role={init_role} not found -> file does not exist ({role_path})")

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




    def _validate_base_experiment(self, base_experiment_raw):
        factors = []
        #extract `path`of all factors from base experiment

        for path, value in nested_dict_iter(base_experiment_raw):

            if value == "$FACTOR$":
                factors.append(path)

            if path[-1] == "$FACTOR$":
                if isinstance(value, str):
                    # add support for the range syntax in factors
                    # range(start, stop, step)
                    s3 = re.search(r"^range\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\)$", value.strip())
                    # range(start, stop)
                    s2 = re.search(r"^range\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)$", value.strip())
                    # range(stop)
                    s1 = re.search(r"^range\(\s*(-?\d+)\s*\)$", value.strip())

                    if s3 is not None:
                        value_ext = list(range(int(s3.group(1)), int(s3.group(2)), int(s3.group(3))))
                        _set_nested_value(base=base_experiment_raw, path=path, value=value_ext, overwrite=True)
                    elif s2 is not None:
                        value_ext = list(range(int(s2.group(1)), int(s2.group(2))))
                        _set_nested_value(base=base_experiment_raw, path=path, value=value_ext, overwrite=True)
                    elif s1 is not None:
                        value_ext = list(range(int(s1.group(1))))
                        _set_nested_value(base=base_experiment_raw, path=path, value=value_ext, overwrite=True)
                    else:
                        raise ValueError(f"if $FACTOR$ is the key, the only allowed string is the range syntax:   got=|{value}|")

                elif not isinstance(value, list):
                    raise ValueError(f"if $FACTOR$ is the key, then the value must be a list of levels used in the cross product (path={path} value={value})")

        return factors


    def _validate_factor_levels(self, factor_levels_raw, expected_factors):

        if not isinstance(factor_levels_raw, list):
            raise ValueError("factor levels must be a list")

        for run in factor_levels_raw:

            actual_factors = []
            for path, value in nested_dict_iter(run):
                actual_factors.append(path)

            if sorted(expected_factors) != sorted(actual_factors):
                raise ValueError(f"expected factors do not match actual factors: expected={expected_factors} actual={actual_factors}")
