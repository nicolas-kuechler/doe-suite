import json
from sys import argv,stderr,stdout
from subprocess import Popen,PIPE

def main():

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
    del command_list['main']

    background_tasks = []

    # start all background tasks
    for key, cmd in command_list.items():
        background_tasks.append(Popen(cmd, shell=True, stderr=stderr, stdout=stdout))

    # start main task
    main_task = Popen(main_cmd, shell=True, stderr=stderr, stdout=stdout)

    # when main task finishes -> terminate all background tasks
    main_task.wait()
    for task in background_tasks:
        task.terminate()


if __name__ == "__main__":
    main()