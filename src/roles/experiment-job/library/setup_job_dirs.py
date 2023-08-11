#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os, json


DOCUMENTATION = r'''
---

'''

RETURN = r'''
'''

from ansible.module_utils.basic import AnsibleModule




def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        jobs=dict(type='list', required=True),
    )

    result = dict(
        changed=False,
        original_message='',
        message=''
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode:
        module.exit_json(**result)


    changed = False # we start with changed false

    jobs = module.params["jobs"]

    for job in jobs:

        if os.path.exists(job["exp_working_dir"]):
            continue

        os.makedirs(os.path.join(job["exp_working_dir"], "results"))
        os.makedirs(os.path.join(job["exp_working_dir"], "scratch"))

        cfg_file = os.path.join(job["exp_working_dir"], "config.json")
        if not os.path.isfile(cfg_file):
            with open(os.path.join(job["exp_working_dir"], "config.json") , 'w') as f:
                json.dump(job["exp_run_config"], f, indent=4, sort_keys=True, separators=(',', ': '))

            changed = True

    result['changed'] = changed

    module.exit_json(**result)



def main():
    run_module()

if __name__ == '__main__':
    main()