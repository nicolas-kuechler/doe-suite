import json
from sys import argv,stderr,stdout
from subprocess import Popen,PIPE,call
import os
import signal

background_tasks = []

def handle_shutdown():
    for task in background_tasks: 
        os.killpg(os.getpgid(task.pid), signal.SIGTERM)

def main():

    # install signal handler to tear down child processes
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    if len(argv) != 3:
        raise ValueError("Unexpected number of arguments" + len(argv))

    host_type = argv[1]
    host_type_index = int(argv[2])

    # get all commands from config
    with open('config.json', 'r') as f:
        config = json.load(f)

    # get main command
    command_list = config["$CMD$"][host_type][host_type_index]
    main_cmd = command_list['main']
    if main_cmd is None:
        raise ValueError("Expected main command")

    del command_list['main']

    # start all background tasks
    for key, cmd in command_list.items():
        task = Popen(cmd, shell=True, stderr=stderr, stdout=stdout, preexec_fn=os.setsid)
        background_tasks.append(task)

    # start main task
    call(main_cmd, shell=True, stderr=stderr, stdout=stdout)

    # when main task finishes -> terminate all background tasks
    for task in background_tasks:
        os.killpg(os.getpgid(task.pid), signal.SIGTERM)


if __name__ == "__main__":
    main()