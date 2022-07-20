# based on: https://gist.github.com/ju2wheels/408e2d34c788e417832c756320d05fb5

# Standard base includes and define this as a metaclass of type
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


from ansible.utils.vars import merge_hash
from ansible.plugins.action import ActionBase

from doespy.design import validate_extend

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

        _design, _ = validate_extend.main(suite=module_args["suite"],
                                       only_validate_design=True,
                                       exp_filter=module_args.get("exp_filter"),
                                       suite_design_dest=module_args["dest"],
                                       ignore_undefined_vars=False,
                                       template_vars=task_vars
                                       )

        return result