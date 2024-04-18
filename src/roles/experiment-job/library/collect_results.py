#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os, json, subprocess, warnings


DOCUMENTATION = r'''
---

'''

RETURN = r'''
'''

from ansible.module_utils.basic import AnsibleModule


def jobid2workingdir(job_id, base):

    """
    Derives the path for the working directory corresponding to the job_id within `base`.

    job_id: {'suite': X, 'suite_id': X, 'exp_name': X, ... }
    base: a path to a directory in which the workingdir resides

    return: path to the working directory for a job
    """

    exp_working_dir = os.path.join(base,
                f"{job_id['suite']}_{job_id['suite_id']}",
                job_id['exp_name'],
                f"run_{job_id['exp_run']}",
                f"rep_{job_id['exp_run_rep']}")

    return exp_working_dir


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        job_ids_ready_to_collect_results=dict(type='list', required=True),
        exp_host_lst=dict(type='list', required=True),
        local_result_dir=dict(type='str', required=True),
        remote_result_dir=dict(type='str', required=True),
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

    if module.check_mode:
        module.exit_json(**result)


    changed = False # we start with changed false


    for job_id in module.params["job_ids_ready_to_collect_results"]:


        local_results_dir_base = jobid2workingdir(job_id, module.params["local_result_dir"])
        remote_results_dir = os.path.join(jobid2workingdir(job_id, module.params["remote_result_dir"]), "results")
        remote_config_file = os.path.join(jobid2workingdir(job_id, module.params["remote_result_dir"]), "config.json")

        for i, my_host in enumerate(module.params["exp_host_lst"]):


            # create local result dir
            local_results_dir = os.path.join(local_results_dir_base, my_host['host_type'], f"host_{my_host['exp_host_type_idx']}" )
            os.makedirs(local_results_dir, exist_ok=True)

            # fetch results
            server_port = my_host.get('public_port', 22)
            nonstandard_port = ['-e', f'ssh -p {server_port}'] if server_port != 22 else []
            src_path = f"{my_host['public_dns_name']}:{remote_results_dir}/*"
            try:
                # -L is needed to follow symlinks
                _completed_process = subprocess.run(["rsync", "-azL"] + nonstandard_port + [src_path, local_results_dir], check=True)
            except subprocess.CalledProcessError as e:
                warnings.warn(f"Rsync command failed to fetch results with return code {e.returncode}   dir={local_results_dir}")
                raise e


            # fetch config.json from first host
            if i == 0:
                src_path = f"{my_host['public_dns_name']}:{remote_config_file}"
                try:
                    _completed_process = subprocess.run(["rsync", "-az"] + nonstandard_port + [src_path, local_results_dir_base], check=True)
                except subprocess.CalledProcessError as e:
                    warnings.warn(f"Rsync command failed to fetch config.json with return code {e.returncode}")
                    raise e

        changed = True


    result['changed'] = changed

    module.exit_json(**result)



def main():
    run_module()

if __name__ == '__main__':
    main()