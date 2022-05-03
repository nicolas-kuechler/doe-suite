#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)
import subprocess, re, sys
__metaclass__ = type

DOCUMENTATION = r'''
---
module: bjobs_info

short_description: This module gathers information about the jobs in bjobs

version_added: "1.0.0"

description: The module queries bjobs to gather information about queued, running, and finished jobs.

'''

EXAMPLES = r'''
- name: Get list of jobs from bjobs
  bjobs_info:
'''

RETURN = r'''
tasks:
    description: a list of tasks (a task as a dict) from task spooler
    type: list
    returned: always
    sample: [{"id": "0", "state": "running", "output": /tmp/xyz, "error_level": "0", "times": "...", "label": "test", "cmd": "echo test", "pid": "123"}]
'''

from ansible.module_utils.basic import AnsibleModule

def get_tasks():
    if sys.version_info[0] == 3:
        completed_process = subprocess.run(["bjobs", "-w"], stdout=subprocess.PIPE).stdout
    else:
        # Python 2
        completed_process = subprocess.Popen(
            ["bjobs", "-w"],
            stdout=subprocess.PIPE
        ).communicate()[0]

    lines = completed_process.decode('utf-8').splitlines()

    tasks = []

    # group 1: job id (lsf)
    # group 2: username (lowercase letters)
    # group 3: status (PEND|RUN)
    # group 4: queue
    # group 5: from_host
    # group 6: exec_host
    # group 7: job name
    # group 8: date
    pattern = r'^([0-9]+)\s+([a-z]*)\s+(PEND|RUN)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+(.*)$'

    for line in lines[1:]: # ignore the first line (header)
        m = re.search(pattern, line)

        if not m:
            raise ValueError("not matched: " + line)

        d = {
            "id": m.group(1),
            "state": m.group(3),
            "label": m.group(7)
        }

        tasks.append(d)
    return tasks



def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        # return_pid=dict(type='bool', required=False, default=False),
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

    result['tasks'] = get_tasks()

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()