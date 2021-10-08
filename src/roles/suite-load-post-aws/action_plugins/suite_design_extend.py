# based on: https://gist.github.com/ju2wheels/408e2d34c788e417832c756320d05fb5

# Standard base includes and define this as a metaclass of type
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import copy
from ansible.utils.vars import merge_hash
from ansible.plugins.action import ActionBase

# Load the display hander to send logging to CLI or relevant display mechanism
try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


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


        #print(f"exp_specific_vars={exp_specific_vars}")

        suite_ext = {}

        for exp_name in suite_design.keys():

            #print(f"exp_name={exp_name}")

            exp_runs_ext = []
            exp = suite_design[exp_name]

            exp_vars = exp_specific_vars.get(exp_name, {})


            for factor_level in exp["factor_levels"]: 
                d = copy.deepcopy(exp["base_experiment"])

                # overwrite $FACTOR$ with the concrete level of the run (via recursive merging dicts)
                d = merge_hash(d, factor_level, recursive=True)


                # replace template variables in $CMD$ (from the current run + exp_specific_vars)
                d["$CMD$"] = {}

                with self._templar.set_temporary_context(variable_start_string="[%", variable_end_string="%]",
                                                       available_variables={"my_run": d, **exp_vars}):
                    # go through all host types, take their command and apply the templating
                    for host_type in exp["host_types"].keys():
                        cmd_d = exp["host_types"][host_type]["$CMD$"]
                        d["$CMD$"][host_type] = self._templar.template(cmd_d)

                exp_runs_ext.append(d)

            suite_ext[exp_name] = exp_runs_ext

        result["designs"] = suite_ext
        
        return result