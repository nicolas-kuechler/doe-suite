#!/usr/bin/env python3

import shlex
import argparse
import logging
import os
import tempfile
import shutil
import subprocess
import sys
import boto3
import uuid

from io import StringIO
from state import State

OUT_FOLDER = f"{os.environ['HOME']}/.does-master"
LOG_FOLDER = f"{OUT_FOLDER}/logs"
STATE_PATH = f"{OUT_FOLDER}/state.json"
RESULTS_ZIP_PATH = "/tmp/results"
DOES_PRJ_DIR_VARIABLE = "DOES_PROJECT_DIR"
AWS_REGION_NAME_VARIABLE = "AWS_REGION_NAME"


def get_parser():
    parser = argparse.ArgumentParser(description="Utility to run benchmarks on AWS using the DoE-Suite")

    subparsers = parser.add_subparsers(dest="command")

    #
    # primary command: ansible
    #
    ansible_subparser = subparsers.add_parser("ansible", help="Ansible-related commands")

    ansible_subparser.add_argument("-b", "--benchmark",
        help="Specify the benchmark (name of the file in does_config/designs without extension)",
        required=True, type=str)

    ansible_subparser.add_argument("-c", "--commit",
        help="Commit that triggered this run", type=str)

    ansible_subparser.add_argument("-t", "--terminate",
        help="Terminate AWS EC2 instances that run benchmarks for the given commit",
        action="store_true")

    #
    # primary command: aws
    #
    aws_subparser = subparsers.add_parser("aws", help="AWS-related commands")

    aws_subparser.add_argument("-l", "--list",
        help="List AWS EC2 instances that are in (one of the) specified state(s)",
        action="store_true")

    aws_subparser.add_argument("-s", "--state",
        help="AWS EC2 instance state to filter for (one or more)",
        nargs="+", default=["running"])

    #
    # primary command: slack
    #
    slack_subparser = subparsers.add_parser("slack", help="Slack-related commands")

    slack_subparser.add_argument("-p", "--post",
        help="Post the specified files", nargs="+")

    slack_subparser.add_argument("-c", "--channel",
        help="Channel to post messages in", type=str)

    #
    # primary command: results
    #
    results_subparser = subparsers.add_parser("results", help="Commands related to result-fetching")

    results_subparser.add_argument("-l", "--list",
        help="List all produced results", action="store_true")

    results_subparser.add_argument("-f", "--fetch",
        help="Fetch the specified results", nargs="+")

    return parser

def create_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)
    else:
        logging.debug(f"Could not create folder, path '{path}' already exists.")

def setup_outdir():
    create_folder(OUT_FOLDER)
    create_folder(LOG_FOLDER)


class DOESMaster():
    def __init__(self, args):
        self.args = args

        for var in [DOES_PRJ_DIR_VARIABLE, AWS_REGION_NAME_VARIABLE]:
            if var not in os.environ:
                logging.error(f"The variable '{var}' is not set. "
                               "Set it to the directory of the doe-suite.")
                exit(1)

        setup_outdir()
        self.state = State(STATE_PATH, f"{os.environ[DOES_PRJ_DIR_VARIABLE]}/doe-suite")


    def aws_get_instances(self, states):
        """
        Get AWS EC2 instance descriptions (only the ID and instance name) for
        all instances that are in one of the given states.
        """
        instances = []

        # Gather which AWS instances are still running
        aws_client = boto3.client('ec2', region_name=os.environ["AWS_REGION_NAME"])
        instance_desc = aws_client.describe_instances()

        running_instances = ""
        for reservation in instance_desc"Reservations"]:
            for instance in reservation["Instances"]:
                if instance["State"]["Name"] in states:
                    name = "-"
                    for key_vals in reservation["Tags"]:
                        if key_vals["Key"] == "Name":
                            name = key_vals["Value"]
                    instances.append({"name": name, "id": instance['InstanceId']})

        return instances

    def ansible_do_benchmark(self):
        """
        Start ansible playboook to spin up AWS EC2 instances for the specified
        experiment design.
        """

        # TODO: get result path fron ETL pipeline!
        path = ""
        self.state.add_new_result(path, commit)

        # TODO: change project ID to commit hash -> add functionality to kill old benchmarks
        p = subprocess.run([
            "poetry",
            "run",
            "ansible-playbook",
            "src/experiment-suite.yml",
            "-e",
            f"suite={self.args.benchmark} id=new prj_id={self.args.commit}"
        ], cwd=self.state.home)

        context = f"Benchmark {self.args.benchmark} for commit {self.args.commit}"
        if p.returncode != 0:
            state = "FAILED!"
        else:
            state = "STARTED"
        return f"{context} {state}"

    def ansible_clear(self):
        """
        Clear ansible instances of the specified commit (project ID)
        """

        p = subprocess.run([
            "poetry",
            "run",
            "ansible-playbook",
            "src/clear",
            "-e",
            f"prj_id={self.args.commit}"
        ], cwd=self.state.home)

        context = f"Clearing all instances for commit {slef.args.commit} "
        if p.returncode != 0:
            state = "FAILED!"
        else:
            state = "SUCCESSFUL"


        return f"{context} {state}\n\n{self.aws_currently_running()}"

    def aws_currently_running(self):
        running_instances = "Currently running AWS EC2 instances:\n"
        for instance in self.aws_get_instances("running"):
            running_instances += f"- name: {instance['name']}, id: {instance['id']}\n"

        return running_instances

    def handle_ansible_cmd(self):
        # Start a benchmark
        if self.args.benchmark:
            if not self.args.commit:
                self.args.commit = f"manual-{uuid.uuid1().hex}"
            return self.ansible_do_benchmark()
        # Terminate the instances of  a running benchmark
        elif self.args.terminate and self.args.commit:
                return self.ansible_clear()
        else:
            msg = "Received invalid command or arguments for 'ansible' subcommand!"
            logging.error(msg)
            return msg

    def handle_aws_cmd(self):
        if self.args.list:
            return self.aws_currently_running(self.args.state)
        else:
            msg = "Received invalid command or arguments for 'aws' subcommand!"
            logging.error(msg)
            return msg

    def handle_slack_cmd(self):
        files_to_post = self.args.post
        channel = self.args.channel

        self.state.update()

    def handle_results_cmd(self):
        do_list_results = self.args.list
        files_to_fetch = self.args.fetch

        self.state.update()

        if do_list_results:
            print("The following results are available:")
            for result in self.state.results:
                print(f"\t- {result}")
            return

        # TODO: add functionality to fetch all results for a commit

        results_path = tempfile.mkdtemp()

        for result in self.state["results"]:
            if result["path"] in files_to_fetch:
                commit_folder = f"{results_path}/{result['commit']}"
                create_folder(commit_folder)

                # TODO: find better way to not overwrite result files
                shutil.copyfile(result["path"], f"{commit_folder}/{results_path.split('/')[1]}")

        if len(self.state["results"]) > 0:
            if os.path.exists(RESULTS_ZIP_PATH):
                os.remove(RESULTS_ZIP_PATH)

            shutil.make_archive(RESULTS_ZIP_PATH, "zip", results_path)

            print(f"Download the requested files from {RESULTS_ZIP_PATH} (e.g., using scp).")


    def handle(self):
        if self.args.command == "ansible":
            return self.handle_ansible_cmd()
        if self.args.command == "aws":
            return self.handle_aws_cmds()
        elif self.args.command == "slack":
            return self.handle_slack_cmd()
        elif self.args.command == "results":
            return self.handle_results_cmd()
        else:
            logging.warning(f"Unknown primary command {self.args.command}")


def does_master_exec(args_str):
    cmd_stdout = sys.stdout
    sys.stdout = str_stdout = StringIO()

    success = True
    try:
        parser = get_parser()
        args = parser.parse_args(shlex.split(args_str))

        does = DOESMaster(args)
        out = does.handle()
    except SystemExit:
        rc = sys.exc_info()[1]
        success = rc == 0
        logging.error("Caught system exit with return code {rc}")

    sys.stdout = cmd_stdout

    # Convention:
    #   - if there is an error, respond with error message
    #   - if the handle function returns something, we return that to slack.
    #   - Otherwise, we write the stdout back
    if not success:
        return f"ERROR: executing the does command {self.args.command} failed unexpectedly with error code {rc}!"
    elif out:
        return out
    else:
        return str_stdout.getvalue()

if __name__ == '__main__':
    parser = get_parser()
    args = parser.parse_args()
    does = DOESMaster(args)
    does.handle()
