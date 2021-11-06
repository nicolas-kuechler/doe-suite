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
import re

from io import StringIO
from state import State
from slack_bot import str_to_markdown

OUT_FOLDER = f"{os.environ['HOME']}/.does-master"
LOG_FOLDER = f"{OUT_FOLDER}/logs"
STATE_PATH = f"{OUT_FOLDER}/state.json"
RESULTS_ZIP_NAME = "results"
DOES_PRJ_DIR_VARIABLE = "DOES_PROJECT_DIR"
AWS_REGION_NAME_VARIABLE = "AWS_REGION_NAME"
AWS_INSTANCE_STATES_ALL = ["pending", "running", "shutting-down", "terminated", "stopping", "stopped"]


def get_parser():
    parser = argparse.ArgumentParser(description="Utility to run benchmarks on AWS using the DoE-Suite")

    subparsers = parser.add_subparsers(dest="command")

    #
    # primary command: ansible
    #
    ansible_subparser = subparsers.add_parser("ansible", help="Ansible-related commands")

    ansible_subparser.add_argument("-b", "--benchmark",
        help="Specify the benchmark (name of the file in does_config/designs without extension)",
        type=str)

    ansible_subparser.add_argument("-c", "--commit",
        help="Commit that triggered this run", type=str)

    ansible_subparser.add_argument("-t", "--terminate",
        help="Terminate all AWS EC2 instances that run benchmarks for the given commit",
        action="store_true")

    #
    # primary command: aws
    #
    aws_subparser = subparsers.add_parser("aws", help="AWS-related commands")

    aws_subparser.add_argument("-l", "--list",
        help="List AWS EC2 instances that are in (one of the) specified state(s)",
        action="store_true")

    aws_subparser.add_argument("-a", "--all",
        help="List AWS EC2 instances that are in (one of the) specified state(s)",
        action="store_true")

    aws_subparser.add_argument("-s", "--state",
        help="AWS EC2 instance state to filter for (one or more)",
        choices=AWS_INSTANCE_STATES_ALL, nargs="+", default=["running"])

    #
    # primary command: fetch
    #
    fetch_subparser = subparsers.add_parser("fetch", help="Commands related to "
                            "fetching files from the ansible master")

    fetch_subparser.add_argument("-s", "--show",
        help="Show information on results", action="store_true")

    fetch_subparser.add_argument("-c", "--commit",
        help="Filter for the specified commit(s)", nargs="+")

    fetch_subparser.add_argument("-l", "--logs",
        help="Fetch asible master log file", action="store_true")

    fetch_subparser.add_argument("-p", "--plots", nargs="?", const="plots", type=str,
        help="Only fetch plots from the specified subfolder in does_results ")

    return parser

def create_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)
    else:
        logging.debug(f"Could not create folder, path '{path}' already exists.")

def setup_outdir():
    create_folder(OUT_FOLDER)
    create_folder(LOG_FOLDER)

def init_state():
    return State(STATE_PATH, f"{os.environ[DOES_PRJ_DIR_VARIABLE]}/doe-suite",
                        f"{os.environ[DOES_PRJ_DIR_VARIABLE]}/does_results")

class DOESMaster():
    def __init__(self, args, parser, is_run_from_cmd):
        self.args = args
        self.parser = parser
        self.is_run_from_cmd = is_run_from_cmd

        for var in [DOES_PRJ_DIR_VARIABLE, AWS_REGION_NAME_VARIABLE]:
            if var not in os.environ:
                logging.error(f"The variable '{var}' is not set. "
                               "Set it to the directory of the doe-suite.")
                exit(1)

        setup_outdir()
        self.state = init_state()

    def ansible_do_benchmark(self):
        """
        Start ansible playboook to spin up AWS EC2 instances for the specified
        experiment design.
        """

        result = self.state.add_new_result(self.args.benchmark, self.args.commit)

        p = subprocess.run([
            "poetry",
            "run",
            "ansible-playbook",
            "src/experiment-suite.yml",
            "-e",
            f"suite={self.args.benchmark} id={result.suite_id} is_new_run=True prj_id={self.args.commit}"
        ], cwd=self.state.doe_suite)

        context = f"Benchmark {self.args.benchmark} for commit {self.args.commit}"
        clear_out = ""
        if p.returncode != 0:
            self.state.set_result_failed(self.args.commit)
            state = "FAILED!"
            clear_out = "\nCleaning up instances of failed run:\n" + self.ansible_clear()
        else:
            self.state.set_result_successful(self.args.commit)
            state = "SUCCESSFUL"
        return f"{context} {state}{clear_out}", None

    def ansible_clear(self):
        """
        Clear ansible instances of the specified commit (project ID)
        """

        p = subprocess.run([
            "poetry",
            "run",
            "ansible-playbook",
            "src/clear.yml",
            "-e",
            f"prj_id={self.args.commit}"
        ], cwd=self.state.doe_suite)

        context = f"Clearing all instances for commit {self.args.commit} "
        if p.returncode != 0:
            state = "FAILED!"
        else:
            state = "SUCCESSFUL"


        return f"{context} {state}\n\n{self.aws_currently_running()}", None, None

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
        for reservation in instance_desc["Reservations"]:
            for instance in reservation["Instances"]:
                if instance["State"]["Name"] in states:
                    name = "-"
                    for key_vals in instance["Tags"]:
                        if key_vals["Key"] == "Name":
                            name = key_vals["Value"]
                    instances.append({"name": name, "id": instance['InstanceId']})

        return instances

    def aws_currently_running(self, states=["running"]):
        """
        Build a string listing all AWS instances that are in the given states.
        """
        running_instances = "Currently running AWS EC2 instances:\n"
        for instance in self.aws_get_instances(states):
            running_instances += f"\t- name: {instance['name']}, id: {instance['id']}\n"

        return running_instances

    def handle_ansible_cmd(self):
        """
        Handle ansible subcommand of does.
        """

        # Start a benchmark
        if self.args.benchmark:
            if not self.args.commit:
                self.args.commit = f"manual-{uuid.uuid1().hex}"
            return self.ansible_do_benchmark()
        # Terminate the instances of  a running benchmark
        elif self.args.terminate and self.args.commit:
                return self.ansible_clear(), None
        else:
            msg = "Received invalid command or arguments for 'ansible' subcommand!"
            logging.error(msg)
            return msg, None

    def handle_aws_cmd(self):
        """
        Handle AWS subcommand of does.
        """

        if self.args.list:
            if self.args.all:
                states = AWS_INSTANCE_STATES_ALL
            else:
                states = self.args.state
            return "Response:", [str_to_markdown(self.aws_currently_running(states))], None
        else:
            msg = "Received invalid command or arguments for 'aws' subcommand!"
            logging.error(msg)
            return msg, None, None

    # TODO: make plot extension choice available on cmd line
    def fetch_results(self, commits, plots_subdir, plots_ext=["png"]):
        """
        Get the results for the specified commits
        """

        self.state.update()

        if plots_subdir:
            plot_exts_str = ",".join(plots_ext)
            texts = []
            files = []
            for result in self.state.results:
                if result.commit in commits:
                    plots_path = f"{self.state.does_results}/{result.subdir}/{plots_subdir}"
                    for plot_dir, _, plot_files in os.walk(plots_path):
                        for plot_file in plot_files:
                            if re.search(f".*\.({plot_exts_str})", plot_file):
                                texts.append(f"Plot for commit {result.commit}")
                                files.append(f"{plot_dir}/{plot_file}")

            return texts, None, files
        else:
            # Gather results
            tmp_path = tempfile.mkdtemp()
            results_path = f"{tmp_path}/results"

            res_cnt = 0
            for result in self.state.results:
                if result.commit in commits:
                    commit_folder = f"{results_path}/{result.commit}"
                    shutil.copytree(f"{self.state.does_results}/{result.subdir}", f"{commit_folder}/{result.subdir}")
                    res_cnt += 1

            if res_cnt > 0:
                results_zip_path = shutil.make_archive(f"{tmp_path}/{RESULTS_ZIP_NAME}", "zip", results_path)

                if self.is_run_from_cmd:
                    return f"The requested results were written to {results_zip_path}", None, None
                else:
                    return [f"Results for commit(s): {', '.join(commits)}"], None, [results_zip_path]
            else:
                f"No results found for commit(s) {commits}.", None, None

    def handle_fetch_cmd(self):
        """
        Handle fetch subcommand of does.
        """

        do_list_results = self.args.show
        do_fetch_logs = self.args.logs
        commits = self.args.commit
        plots_subdir = self.args.plots
        do_fetch_plots = plots_subdir is not None

        if not commits and not (do_list_results or do_fetch_logs):
            parser.print_help()
            return

        self.state.update()

        if do_list_results:
            # TODO: Sort them by timestamp
            if len(self.state.results) > 0:
                print("The following results are available:")
                for result in self.state.results:
                    print(f"\t- {result}")
            else:
                print("No results stored")
            return

        if do_fetch_logs:
            # TODO
            pass
        else:
            return self.fetch_results(commits, plots_subdir)

    def handle(self):
        if self.args.command == "ansible":
            return self.handle_ansible_cmd()
        if self.args.command == "aws":
            return self.handle_aws_cmd()
        elif self.args.command == "fetch":
            return self.handle_fetch_cmd()
        else:
            logging.warning(f"Unknown primary command {self.args.command}")


def output_wrapper(fn, *args, **kwargs):
    """
    Run fn with the arguments args and kwargs and while wrapping stdout.
    We returnoutput by the following convention:
      - if there is an error, respond with error message
      - if the handle function returns something, we return that to slack.
      - Otherwise, we write the stdout back
    """

    # TODO: refactor and remove out, replace it with the caught stdout
    # TODO: redirect stdout of ansible run to some useful log file
    cmd_stdout = sys.stdout
    sys.stdout = str_stdout = StringIO()

    success = True
    try:
        out, out_markdown, files_to_upload = fn(*args, **kwargs)
    except SystemExit:
        rc = sys.exc_info()[1]
        success = rc == 0
        logging.error(f"Caught system exit with return code {rc}")

    sys.stdout = cmd_stdout

    if not success:
        return f"ERROR: executing the function with '{args}' and '{kwargs}' failed unexpectedly " + \
               f"with error code {rc}!", None, None
    elif out or out_markdown:
        return out, out_markdown, files_to_upload
    else:
        return str_stdout.getvalue(), None, None

def does_master_exec_helper(args_str):
    parser = get_parser()
    args = parser.parse_args(shlex.split(args_str))

    does = DOESMaster(args, parser, False)
    return does.handle()

def does_master_exec(args_str):
    """
    Parse the argument string and execute the does binary with those arguments.
    Return messages and files found by the does command to return to slack.
    """
    return output_wrapper(does_master_exec_helper, args_str)

def does_fetch_results_helper(commits, plots_subdir):
    does = DOESMaster("", None, False)
    return does.fetch_results(commits, plots_subdir)

def does_fetch_results(commits, plots_subdir):
    """
    Fetch results for the given commits. If plots_subdir is set, only plots from there are fetched.
    Otherwise, the entire result directory is put into an archive.
    """
    return output_wrapper(does_fetch_results_helper, commits, plots_subdir)


if __name__ == '__main__':
    parser = get_parser()
    args = parser.parse_args()
    does = DOESMaster(args, parser, True)
    does.handle()
