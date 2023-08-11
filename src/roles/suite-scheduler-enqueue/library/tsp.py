#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import subprocess, os, signal, re, time


DOCUMENTATION = r'''
---
module: tsp

short_description: This module creates an interface to task-spooler

version_added: "1.0.0"

description: This module allows to (i) schedule new tasks to the batch job system task-spooler, (ii) clear task-spooler (stop running tasks and remove all queued), (iii) remove an individual task from the queue. For tasks scheduled with this module, the command given to task spooler is extended such that it runs in the provided working_dir and outputs stdout and stderr in separate files.

options:
    remove_task_id:
        description: Remove the task (e.g., because it is finished) with the task spooler task id from the task spooler queue
        required: false
        type: str
    remove_task_label:
        description: Remove all tasks (e.g., because they are finished) with the task spooler task label from the task spooler queue
        required: false
        type: str
    clear_tasks:
        description: Before adding new commands (tasks), stop all running tasks and remove all tasks from the queue.
        required: false
        type: bool
    cmd:
        description: The command to add at the end of the task spooler queue.
        required: false
        type: str
    cmd_label:
        description: The label of the command to add (required if there is a command)
        required: false
        type: str
    cmd_working_dir:
        description: The working dir of the command (required if there is a command)
        required: false
        type: str
    cmd_stdout_file:
        description: The file to log stdout, relative to the working dir (required if there is a command).
        required: false
        type: str
    cmd_stderr_file:
        description: The file to log stderr, relative to the working dir (required if there is a command).
        required: false
        type: str
'''

EXAMPLES = r'''
- name: Clear the task-spooler queue (and stop all running)
  tsp:
    clear_tasks: True

- name: Add a command but first clear the task-spooler queue (and stop all running)
  tsp:
    clear_tasks: True
    cmd: echo hello
    cmd_label: abc
    cmd_working_dir: /home/ubuntu
    cmd_stdout_file: stdout.log
    cmd_stderr_file: stderr.log

- name: Add a command to task spooler
  tsp:
    cmd: echo hello
    cmd_label: abc
    cmd_working_dir: /home/ubuntu
    cmd_stdout_file: stdout.log
    cmd_stderr_file: stderr.log


- name: Remove the task with id 2 from the queue
  tsp:
    remove_task_id: 2

- name: Remove all tasks with label 'abc' from the queue
  tsp:
    remove_task_label: abc
'''

RETURN = r'''
'''

from ansible.module_utils.basic import AnsibleModule



def get_tasks(return_pid):
    completed_process = subprocess.run(["tsp"], capture_output=True)

    lines = completed_process.stdout.decode('utf-8').splitlines()

    tasks = []

    pattern = r'([0-9]+)\s+(queued|running|finished)\s+([^\s]+)\s+(?:([0-9]+)\s+([^\s]+)|\s+)\s(?:\[(.+)\](.+)|(.+))'

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

        # used for building commands (schedule command)
        cmd=dict(type='str', required=False),
        cmd_label=dict(type='str', required=False),
        cmd_working_dir=dict(type='str', required=False),
        cmd_stdout_file=dict(type='str', required=False),
        cmd_stderr_file=dict(type='str', required=False),

        # id task to remove (could take list maybe?)
        remove_task_id=dict(type='str', required=False),

        remove_task_labels=dict(type='list', required=False),

        # boolean that indicates whether to clear
        clear_tasks=dict(type='bool', required=False, default=False),

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


    # TSP LOGIC:
    changed = False # we start with changed false

    if module.params["clear_tasks"]:
        # stop all running tasks and clear the queue
        changed = clear_task_spooler()


    if module.params["cmd"]: # run a command

        if not all(module.params[v] is not None for v in ["cmd_label", "cmd_working_dir", "cmd_stdout_file", "cmd_stderr_file"]):
            module.fail_json(msg="for adding a cmd: label, working_dir, stdout_file, stderr_file are required", **result)


        # get current tsp state
        tasks = get_tasks(return_pid=False)

        labels = [d["label"] for d in tasks]

        cmd_label = module.params["cmd_label"]

        # cmd with same label already in task spooler => don't add
        if  cmd_label is not None and cmd_label in labels:
            changed = changed # or False   -> here nothing changed

        else: # add cmd to task spooler queue

            # build cmd that changes working directory and outputs stdout to file, stderr to file and everything to stdout
            cmd = f"cd {module.params['cmd_working_dir']} &&  (({module.params['cmd']}) | tee {module.params['cmd_stdout_file']}) 3>&1 1>&2 2>&3 | tee {module.params['cmd_stderr_file']}"

            if cmd_label is not None:
                tsp_cmd = ["tsp", "-L", cmd_label, "/bin/sh", "-c", cmd]
            else:
                tsp_cmd = ["tsp", "/bin/sh", "-c", cmd]

            # enqueue command
            subprocess.run(tsp_cmd, capture_output=True, text=True, check=True)

            changed = True


    # remove task from task spooler queue
    if module.params['remove_task_id']:
        subprocess.run(["tsp", "-r", module.params['remove_task_id']], capture_output=True, text=True)

        changed = True
    elif module.params['remove_task_labels']:

        tasks = get_tasks(return_pid=False)

        for task in tasks:
            if task["label"] in module.params['remove_task_labels']:
                subprocess.run(["tsp", "-r", task["id"]], capture_output=True, text=True)
                changed = True

    # mark whether module changed
    result['changed'] = changed


    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)

def clear_task_spooler():

    # clear all done
    subprocess.run(["tsp", "-C"], capture_output=True, check=True)

    tasks = get_tasks(return_pid=True)

    if len(tasks) == 0:
        return False # changed

    # make single slot
    subprocess.run(["tsp", "-S", "1"], capture_output=True, check=True)

    # add a dummy task that just waits for one minute (when this is running, then we know that in between cmds, the task is not done because it takes 1 min)
    cp = subprocess.run(["tsp", "-L", "DUMMY", "sleep", "60"], capture_output=True, check=True)

    # make the dummy task urgent (next in line)
    subprocess.run(["tsp", "-u"], capture_output=True, check=True)

    for task in tasks:
        if task["state"] == "running":
            # kill the running processes
            os.killpg(int(task['pid']), signal.SIGTERM)

    # now the dummy task is running
    def get_dummy_task_pid():
        tasks = get_tasks(return_pid=True)
        dummy_task_pid = None
        for task in tasks:
            if task["state"] == "running":
                if task["label"] != "DUMMY" or dummy_task_pid is not None:
                    raise ValueError(f"unexpected running task  (only single dummy task should run): {task}")
                dummy_task_pid = task["pid"]

        if dummy_task_pid is None:
            raise ValueError("running dummy task not found")

        return dummy_task_pid

    try:
        dummy_task_pid = get_dummy_task_pid()
    except ValueError as e:
        time.sleep(3) # add some slack for process to finish
        # try again
        dummy_task_pid = get_dummy_task_pid()

    # clear the task spooler (remove all jobs in queue)
    subprocess.run(["tsp", "-K"], capture_output=True, check=True)

    # finally also kill the dummy task by pid
    os.killpg(int(dummy_task_pid) , signal.SIGTERM)

    return True # changed


def main():
    run_module()

if __name__ == '__main__':
    main()