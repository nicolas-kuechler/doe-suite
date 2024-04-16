import copy
import itertools
import collections
import jinja2
import json
import subprocess
from ansible.utils.vars import merge_hash

from doespy import util

from typing import List
from typing import Dict
from typing import Literal
from typing import Union

from pydantic import Field
from pydantic import BaseModel
from pydantic import root_validator



def extend(suite_design, exp_specific_vars, use_cmd_shellcheck=False):
    """

    Args:
        suite_design (Dict): suite design (not extended)
                                and without any variables replaced
        exp_specific_vars (_type_): _description_
        ansible_vars (Dict): variables from the ansible environment

    Raises:
        ValueError: _description_
        jinja2.UndefinedError: _description_

    Returns:
        _type_: _description_
    """

    suite_ext = {}

    for exp_name in suite_design.keys():

        if exp_name == "$ETL$":
            continue

        exp_runs_ext = []
        exp = suite_design[exp_name]

        exp_vars = exp_specific_vars.get(exp_name, {})

        base_experiment, cross_factor_levels = extract_cross_product(
            exp["base_experiment"]
        )

        for factor_level in exp["factor_levels"]:
            # these are the list of factor_levels when $FACTOR$ is used
            #  as the key in base_experiment -> builds the cross product
            for cross_factor_level in cross_factor_levels:

                factor_level = merge_hash(
                    factor_level, cross_factor_level, recursive=True
                )


                # introduce except_filters to skip certain runs
                skip_run = any(_is_subset_dict(except_level, factor_level) for except_level in exp.get("except_filters", []))
                if skip_run:
                    print(f"Skipping run with factor_level={factor_level}")
                    continue # we are skipping this combination

                run_config = copy.deepcopy(base_experiment)

                # overwrite $FACTOR$ with the concrete level of the run
                # (via recursive merging dicts)
                run_config = merge_hash(run_config, factor_level, recursive=True)

                # copy the cmds from host_types
                run_config["$CMD$"] = {}
                for host_type in exp["host_types"].keys():
                    run_config["$CMD$"][host_type] = exp["host_types"][host_type][
                        "$CMD$"
                    ]

                # resolve [% %] for specific factor level
                env = util.jinja2_env(
                    loader=None,
                    undefined=jinja2.StrictUndefined,
                    variable_start_string="[%",
                    variable_end_string="%]",
                )

                # TODO [nku]can we do the templating for each host in $CMD$ separately?
                # -> this would allow setting `host_type_idx` as exp_vars and then we can use it in multi instance experiments
                # (In MPC audit would allow a single command rather than a list of commands that only differs by a player id)
                # -> should probably not be a big issue if $CMD$ already follows the list structure at this point
                # At the moment, host specific variables are available via the hostvars in `exp_host_lst`

                template = json.dumps(run_config)
                while "[%" in template and "%]" in template:
                    # temporary convert to a dict
                    try:
                        run_config = json.loads(template)
                    except ValueError:
                        raise ValueError(f"JSONDecodeError in template: {template}")
                    del run_config[
                        "$CMD$"
                    ]  # temporary delete of cmd
                    # (should not be available as var for templating)

                    template = env.from_string(template)

                    try:
                        template = template.render(my_run=run_config, **exp_vars)
                    except:
                        print(f"\n\n==================\nrun_config={run_config}\n==================")
                        raise
                run_config = json.loads(template)

                exp_runs_ext.append(run_config)

        # validate the extended suite (check commands)
        if use_cmd_shellcheck:
            SuiteExt(__root__=exp_runs_ext)
        suite_ext[exp_name] = exp_runs_ext

    return suite_ext


def extract_cross_product(base_experiment_in):

    base_experiment = {}

    factors = []

    for k, v, path in _nested_dict_iter(base_experiment_in):
        # k: the key (i.e. the name of the config option, unless it's a factor,
        #     than the content is just $FACTOR$)
        # v: the value or a list of levels in case it's a factor
        # path: to support nested config dicts, path keep tracks of all the parent
        #        nodes of k (empty if it is on the top level)

        if k == "$FACTOR$":

            levels = v

            # because of the specicial format of a factor where the key is always
            # $FACTOR$, we need to look at the parent to see the name of the factor
            # (xyz: $FACTOR$: [1,2,3])
            factor = path[-1]
            parent_path = path[:-1]

            # factor in experiment
            # -> need to put placeholder `$FACTOR$` in base_experiment
            _insert_config(
                base_experiment, key=factor, parent_path=parent_path, value="$FACTOR$"
            )

            # loop over the levels and for each level add an entry
            # with the "factor name" and the path to this factor
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


# TODO [nku] does this need to be different from design.util.nested_dict_iter?
def _nested_dict_iter(nested, p=[]):
    for key, value in nested.items():
        if isinstance(value, collections.abc.Mapping):
            yield from _nested_dict_iter(value, p=p + [key])
        else:
            yield key, value, p


def _is_subset_dict(sub_dict, main_dict):
    """Checks if sub_dict is a subset of main_dict"""

    for key, value in sub_dict.items():
        if key not in main_dict:
            return False
        if isinstance(value, dict):
            if not _is_subset_dict(value, main_dict[key]):
                return False
        else:
            if value != main_dict[key]:
                return False
    return True


def _insert_config(config, key, parent_path, value):
    d = config
    for k in parent_path:
        if k not in d:
            d[k] = {}
        d = d[k]
    d[key] = value


class MyExtBaseModel(BaseModel):
    class Config:
        extra = "forbid"
        smart_union = True
        use_enum_values = True

class CmdExt(MyExtBaseModel):
    __root__: str

    @root_validator(skip_on_failure=True)
    def check_cmd_syntax(cls, values):

        cmd = values.get("__root__")

        # echo "printf 'x: 1\\ny: 5' > results/coordinates.yaml" | poetry run  shellcheck --shell=bash  /dev/stdin
        # We disable error SC1091 because we run the validation locally (so shellcheck does not have access to all files)
        # For more information see: https://www.shellcheck.net/wiki/SC1091
        result = subprocess.run([f'echo "{cmd}" | shellcheck -x -e SC1091 --shell=bash /dev/stdin'], text=True, capture_output=True, shell=True) # check=True,

        if result.returncode != 0:
            print("=====================")
            print("shellcheck output: ")
            print(result.stdout)
            print("=====================")
            raise ValueError(f"$CMD$ is invalid bash syntax! (see shellcheck output above)")

        return values

class RunConfig(MyExtBaseModel):

    cmd: Dict[str, Union[CmdExt, Dict[str, CmdExt], List[CmdExt], List[Dict[str, CmdExt]]]] = Field(alias="$CMD$")

    class Config:
        extra = "allow"
        arbitrary_types_allowed = True

class SuiteExt(MyExtBaseModel):
    __root__: List[RunConfig]