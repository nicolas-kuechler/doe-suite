# based on: https://gist.github.com/ju2wheels/408e2d34c788e417832c756320d05fb5

# Standard base includes and define this as a metaclass of type
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import copy
import itertools
import collections
import re
from ansible.utils.vars import merge_hash
from ansible.plugins.action import ActionBase

# Load the display hander to send logging to CLI or relevant display mechanism
try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


def _set_nested_value(base, path, value, overwrite=False):

    d = base
    for i, k in enumerate(path):

        if isinstance(d, list) and isinstance(path[i], int):
            pass  # for lists we support just going over each value

        elif k not in d:
            if i == len(path)-1:  # last
                d[k] = value
            else:
                d[k] = {}
        elif overwrite and i == len(path)-1:  # last + overwrite
            d[k] = value

        d = d[k]


class ActionModule(ActionBase):

    TRANSFERS_FILES = False

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
        suite_design = module_args["suite_design"]
        exp_specific_vars = module_args["exp_specific_vars"]

        result["designs"] = extend_suite_design(
            suite_design, exp_specific_vars, self._templar)

        return result


def extend_suite_design(suite_design, exp_specific_vars, templar):
    # print(f"exp_specific_vars={exp_specific_vars}")

    suite_ext = {}

    for exp_name in suite_design.keys():

        if exp_name == "$ETL$":
            continue

        exp_runs_ext = []
        exp = suite_design[exp_name]

        exp_vars = exp_specific_vars.get(exp_name, {})

        base_experiment, cross_factor_levels = extract_cross_product(
            exp["base_experiment"])

        for factor_level in exp["factor_levels"]:

            # these are the list of factor_levels when $FACTOR$ is used as the key in base_experiment -> builds the cross product
            for cross_factor_level in cross_factor_levels:

                factor_level = merge_hash(
                    factor_level, cross_factor_level, recursive=True)
                d = copy.deepcopy(base_experiment)

                # overwrite $FACTOR$ with the concrete level of the run (via recursive merging dicts)
                d = merge_hash(d, factor_level, recursive=True)

                # replace template variables in $CMD$ (from the current run + exp_specific_vars)
                d["$CMD$"] = {}

                my_vars = copy.deepcopy(d)

                for key, value, path in _nested_dict_iter(my_vars, nested_list=True):

                    if isinstance(value, str) and re.match(r".*\[%.+%\].*", value):
                        # the replacement happens because `my_vars` itself cannot contain variables `[% %]`
                        # instead of deleting these variables from my_vars, we replace them with ` [! !]`
                        # these markers `[! !]` are however, never replaced by themselves.
                        value = value.replace("[%", "[!")
                        value = value.replace("%]", "!]")

                        _set_nested_value(
                            my_vars, path + [key], value, overwrite=True)

                with templar.set_temporary_context(variable_start_string="[%", variable_end_string="%]",
                                                   available_variables={"my_run": my_vars, **exp_vars}):
                    d = templar.template(d)

                with templar.set_temporary_context(variable_start_string="[%", variable_end_string="%]",
                                                   available_variables={"my_run": d, **exp_vars}):
                    # go through all host types, take their command and apply the templating
                    for host_type in exp["host_types"].keys():
                        cmd_d = exp["host_types"][host_type]["$CMD$"]
                        d["$CMD$"][host_type] = templar.template(cmd_d)

                # note: because of jinja -> the templating can only return strings and not numbers

                exp_runs_ext.append(d)

        suite_ext[exp_name] = exp_runs_ext

    return suite_ext


def extract_cross_product(base_experiment_in):

    base_experiment = {}

    factors = []

    for k, v, path in _nested_dict_iter(base_experiment_in):
        # k: the key (i.e. the name of the config option, unless it's a factor, than the content is just $FACTOR$)
        # v: the value or a list of levels in case it's a factor
        # path: to support nested config dicts, path keep tracks of all the parent nodes of k (empty if it is on the top level)

        if k == "$FACTOR$":

            levels = v

            # because of the specicial format of a factor where the key is always $FACTOR$, we need to look at the parent to see the name of the factor (xyz: $FACTOR$: [1,2,3])
            factor = path[-1]
            parent_path = path[:-1]

            # factor in experiment -> need to put placeholder `$FACTOR$` in base_experiment
            _insert_config(base_experiment, key=factor,
                           parent_path=parent_path, value="$FACTOR$")

            # loop over the levels and for each level add an entry with the "factor name" and the path to this factor
            factor_levels = []
            for level in levels:
                factor_levels.append((factor, level, parent_path))
            factors.append(factor_levels)

        else:
            # constant config value (over experiment runs)
            _insert_config(base_experiment, key=k, parent_path=path, value=v)

    cross_factor_levels = []

    # create a cross product of all factors with their respective levels
    for factor_levels_raw in itertools.product(*factors):
        # loop over the different factors and put their level for the run in a dict d
        d = {}
        for k, v, path in factor_levels_raw:
            _insert_config(d, key=k, parent_path=path, value=v)
        cross_factor_levels.append(d)

    return base_experiment, cross_factor_levels


def _nested_dict_iter(nested, p=[], nested_list=False):
    for key, value in nested.items():
        if isinstance(value, collections.abc.Mapping):
            yield from _nested_dict_iter(value, p=p + [key])

        elif nested_list and isinstance(value, list):

            for i, v in enumerate(value):
                yield from _nested_dict_iter(v, p=p + [key, i])

        else:
            yield key, value, p


def _insert_config(config, key, parent_path, value):
    d = config
    for k in parent_path:
        if k not in d:
            d[k] = {}
        d = d[k]
    d[key] = value
