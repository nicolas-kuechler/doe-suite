#!/usr/bin/python3


from __future__ import (absolute_import, division, print_function)
import subprocess, re, sys
__metaclass__ = type

DOCUMENTATION = r'''
---
module: slurm_info

short_description: This module gathers information about the jobs in slurm

version_added: "1.0.0"

description: The module queries slurm to gather information about queued, running, and finished jobs.

'''

EXAMPLES = r'''
- name: Group job ids into complete, incomplete, and error
  slurm_info:
    job_ids: [{..}]
    job_id_names: ["l1", "l2", ..]
'''


from ansible.module_utils.basic import AnsibleModule
import json

def get_jobs_status(job_ids, job_id_names):
    """Checks the status of the jobs from job_ids in slurm.
    (group into complete, incomplete, and error)

    Args:
        job_ids (list): list of job_id dicts
        job_id_names (list): list of job_id labels (generated from job_ids)

    Returns:
        complete: (list): list of job_id objects that are complete
        incomplete: list of job_id objects that are still pending or running
        error: (list): list of job_id objects + state for unexpected states
    """

    completed_process = subprocess.run(["squeue", "--json"], stdout=subprocess.PIPE).stdout
    output = json.loads(completed_process.decode('utf-8'))

    state_info = {job['name'] : job['job_state'] for job in output["jobs"]}

    complete = []
    incomplete = []
    error = []

    for job_id, job_id_name in zip(job_ids, job_id_names):
        state = state_info.get(job_id_name)

        if state is None or state == "COMPLETED":
            # job id not found in queue -> assume job is complete
            complete += [job_id]

        elif state == "PENDING" or "RUNNING" or "COMPLETING":
            incomplete += [job_id]
        else:
            print(f"unexpected state for job id  state={state}  job_id={job_id}")
            error += [(job_id, state)]


    return complete, incomplete, error


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        job_ids=dict(type='list', required=True),
        job_id_names=dict(type='list', required=True),
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

    result['complete'], result['incomplete'], result['error'] = get_jobs_status(module.params["job_ids"], module.params["job_id_names"])

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()