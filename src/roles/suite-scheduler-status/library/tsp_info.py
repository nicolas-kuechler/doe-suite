#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)
import subprocess, re
__metaclass__ = type

DOCUMENTATION = r'''
---
module: tsp_info

short_description: This module gathers information about the tasks in task-spooler

version_added: "1.0.0"

description: The module queries task-spooler to gather information about queued, running, and finished tasks.

options:
    return_pid:
        description: A flag that dermines whether running tasks should include the pid.
        required: false
        type: bool

'''

EXAMPLES = r'''
- name: Get list of tasks from task-spooler
  tsp_info:
    return_pid: True
'''

RETURN = r'''
tasks:
    description: a list of tasks (a task as a dict) from task spooler
    type: list
    returned: always
    sample: [{"id": "0", "state": "running", "output": /tmp/xyz, "error_level": "0", "times": "...", "label": "test", "cmd": "echo test", "pid": "123"}]
'''

from ansible.module_utils.basic import AnsibleModule


def get_tasks(return_pid):
    completed_process = subprocess.run(["tsp"], capture_output=True)

    lines = completed_process.stdout.decode('utf-8').splitlines()

    tasks = []

    pattern = r'([0-9]+)\s+(queued|running|finished)\s+([^\s]+)\s+(?:(-?[0-9]+)\s+([^\s]+)|\s+)\s(?:\[(.+?)\](.+)|(.+))'

    for line in lines[1:]: # ignore the first line (header)
        m = re.search(pattern, line)

        if not m:
            raise ValueError("not matched: " + line)

        cmd = m.group(7)
        if cmd is None:
            cmd = m.group(8) # has no label => cmd is in group 7
        
        d = {
            "id": m.group(1),
            "state": m.group(2),
            "output": m.group(3),
            "error_level": m.group(4),
            "times": m.group(5),
            "label": m.group(6),
            "cmd": cmd,
            "pid": None,
            #"full_line": m.group(0),
        }

        if return_pid and d["state"] == "running":
            cp = subprocess.run(["tsp", "-p", d["id"]], capture_output=True)
            d["pid"] = cp.stdout.decode('utf-8').strip()

        tasks.append(d)
    return tasks



def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        return_pid=dict(type='bool', required=False, default=False),
    )

    result = dict(
        changed=False,
        tasks=[]
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


    result['tasks'] = get_tasks(return_pid = module.params['return_pid'])

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()