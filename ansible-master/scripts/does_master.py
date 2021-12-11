#!/usr/bin/env python3

import argparse
import boto3
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid

from datetime import datetime
from io import StringIO
from state import State

OUT_FOLDER = f"{os.environ['HOME']}/.does-master"
LOG_FOLDER = f"{OUT_FOLDER}/logs"
STATE_PATH = f"{OUT_FOLDER}/state.json"
RESULTS_ZIP_NAME = "results"
DOES_PRJ_DIR_VARIABLE = "DOES_PROJECT_DIR"
AWS_REGION_NAME_VARIABLE = "AWS_REGION_NAME"
AWS_INSTANCE_STATES_ALL = ["pending", "running", "shutting-down", "terminated", "stopping", "stopped"]
DEFAULT_PLOTS_SUBDIR = "plots"
DOES_BRANCH = "master"

BENCH_PROGRESS_TO_EMOJI = {
    "running": ":gear:",
    "finished": ":white_check_mark:",
    "failed": ":x:",
}


def get_parser():
    parser = argparse.ArgumentParser(description="Utility to run benchmarks on AWS using the DoE-Suite")

    parser.add_argument("--log_level", help="Set the log level for logging (default: WARNING)",
            type=str, default="WARNING")

    subparsers = parser.add_subparsers(dest="command")

    #
    # primary command: ansible
    #
    ansible_subparser = subparsers.add_parser("ansible", help="Ansible-related commands")

    ansible_subparser.add_argument("-b", "--benchmark",
        help="Specify the benchmark (name of the file in does_config/designs without extension)",
        type=str)

    ansible_subparser.add_argument("-c", "--commit",
        help="Commit that triggered this run (manual commits do not correspond to Git commits)", type=str)

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
        help="Use together with list, lists all AWS EC2 instances (in any state, overwrites --state)",
        action="store_true")

    aws_subparser.add_argument("-s", "--state",
        help="AWS EC2 instance state to filter for (one or more)", nargs="+",
        type=lambda xs: all([x in AWS_INSTANCE_STATES_ALL for x in xs]), default=["running"])

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
        help="Fetch ansible master log file", action="store_true")

    fetch_subparser.add_argument("-p", "--plots", nargs="?", const=[DEFAULT_PLOTS_SUBDIR],
        help="Only fetch plots from the specified subfolder in does_results ")


    #
    # primary command: plot
    #
    plot_subparser = subparsers.add_parser("plot", help="Commands related to "
                            "plotting existing benchmarks")

    plot_subparser.add_argument("-c", "--commit",
        help="Commit for which we should re-generate the plot", type=str, required=True)

    plot_subparser.add_argument("-p", "--path", default=["plots"], nargs="+",
        help="Path(s) to the plots in does_results")

    plot_subparser.add_argument("-e", "--ext", default=["png"], type=str, nargs="+",
        help="Extensions of plots that should be posted in response")

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
                f"{os.environ[DOES_PRJ_DIR_VARIABLE]}/does_results",
                LOG_FOLDER)

class Repo():
    def __init__(self, path, branch, remote="origin"):
        self.path = path
        self.branch = branch
        self.remote = remote

    def __str__(self):
        return f"Repo{{banch: {self.branch}, remote: {self.remote}, path: {self.path}}}"

class DOESMaster():
    """
    Class wrapping all functionality of the does executable.

    :param args: arguments of the binary after they were processed by argparse
    :param parser: argparse parser for this binary (used to print the help page)
    :param say: python bolt handle to reply to slack. Set this to None when the
        command is not triggered from slack.
    :param repo: Repo of the benchmark source code. The newest updates
        from that branch are pulled when a DOESMaster object is initialized.
    /"""

    def __init__(self, args, parser, say, branch=None):
        self.args = args
        self.parser = parser
        self.say = say
        self.is_run_from_cmd = say == None

        for var in [DOES_PRJ_DIR_VARIABLE, AWS_REGION_NAME_VARIABLE]:
            if var not in os.environ:
                logging.error(f"The variable '{var}' is not set. "
                               "Set it to the directory of the doe-suite.")
                exit(1)

        setup_outdir()
        self.state = init_state()

        if branch:
            self.repo = Repo(os.environ[DOES_PRJ_DIR_VARIABLE], branch)
        else:
            self.repo = None
        self.update_benchmarks()

    def update_benchmarks(self):
        """
        Fetch updates b pulling the git repo of the benchmarks.
        """
        if self.repo:
            logging.debug(f"Updating repo: {self.repo}")
            p = subprocess.run([
                    "git",
                    "pull",
                    "--recurse-submodules",
                    self.repo.remote,
                    self.repo.branch
                ], cwd=self.repo.path, capture_output=True)

            if p.stdout:
                for line in p.stdout.decode().split("\n"):
                    logging.debug(line)

            if p.returncode != 0:
                logging.error("Updating the benchmarking repo failed! "
                    f"Trying to still continue.\nError:\n{p.stderr.decode()}")

    def ansible_do_benchmark(self):
        """
        Start ansible playboook to spin up AWS EC2 instances for the specified
        experiment design.
        """

        result = self.state.add_new_result(self.args.benchmark, self.args.commit)
        bench_log_dir = f"{LOG_FOLDER}/{result.subdir}"

        if not self.is_run_from_cmd:
            self.say(f"Starting benchmark for commit {result.commit}")

        with open(result.stderr_file, "w+") as stderr_fp:
            with open(result.stdout_file, "w+") as stdout_fp:
                p = subprocess.run([
                    "poetry",
                    "run",
                    "ansible-playbook",
                    "src/experiment-suite.yml",
                    "-e",
                    f"suite={self.args.benchmark} id={result.suite_id} is_new_run=True prj_id={self.args.commit}"
                ], cwd=self.state.doe_suite, stdout=stdout_fp, stderr=stderr_fp)

        context = f"Benchmark {self.args.benchmark} for commit {self.args.commit}"
        clear_out = ""
        if p.returncode != 0:
            self.state.set_result_failed(self.args.commit)
            state = "FAILED!"
            clear_out = "\nCleaning up instances of failed run:\n" + self.ansible_clear()
        else:
            self.state.set_result_successful(self.args.commit)
            state = "SUCCESSFUL"

            # If there is a plot for this benchmark, post this one instead of the success message
            texts, _, files = self.fetch_results([result.commit], DEFAULT_PLOTS_SUBDIR)
            if len(files) > 0:
                return texts, None, files
        return f"{context} {state}{clear_out}", None, None

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


        return f"{context} {state}\n\n{self.aws_currently_running()}"

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
                instance_state = instance["State"]["Name"]
                if instance_state in states:
                    name = "-"
                    for key_vals in instance["Tags"]:
                        if key_vals["Key"] == "Name":
                            name = key_vals["Value"]
                    instances.append({
                        "name": name,
                        "id": instance['InstanceId'],
                        "state": instance_state
                    })

        return instances

    def aws_currently_running(self, states=["running"]):
        """
        Build a string listing all AWS instances that are in the given states.
        """
        running_instances = "Currently running AWS EC2 instances:\n"
        for instance in self.aws_get_instances(states):
            running_instances += f"\t- name: {instance['name']}, id: {instance['id']}, " +\
                                 f"state: {instance['state']}\n"

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
                return self.ansible_clear(), None, None
        else:
            msg = "Received invalid command or arguments for 'ansible' subcommand!"
            logging.error(msg)
            return msg, None

    def handle_aws_cmd(self):
        """
        Handle AWS subcommand of does.
        """

        if self.args.all and not self.args.list:
            err = "Invalid argument(s), use --all together with --list"
            logging.error(err)
            return err, None, None

        if self.args.list:
            if self.args.all:
                states = AWS_INSTANCE_STATES_ALL
            else:
                states = self.args.state
            return "Response:", [self.aws_currently_running(states)], None
        else:
            msg = "Received invalid command or arguments for 'aws' subcommand!"
            logging.error(msg)
            return msg, None, None

    # TODO: make plot extension choice available on cmd line
    def fetch_results(self, commits, plots_subdirs, plots_ext=["png"]):
        """
        Get the results for the specified commits
        """

        self.state.update()
        results = [ self.state.get_result(commit) for commit in commits ]

        if plots_subdirs:
            texts, files = self.get_plot_files(results, plots_subdirs, plots_ext)
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

    def get_plot_files(self, results, plots_subdirs, plot_exts):
        plot_exts_str = ",".join(plot_exts)
        texts, files = [], []
        i = 1

        for result in results:
            for plots_subdir in plots_subdirs:
                plots_path = f"{self.state.does_results}/{result.subdir}/{plots_subdir}"
                if os.path.exists(plots_path):
                    for plot_dir, _, plot_files in os.walk(plots_path):
                        for plot_file in plot_files:
                            if re.search(f".*\.({plot_exts_str})", plot_file):
                                texts.append(f"Plot {i} for commit {result.commit}")
                                files.append(f"{plot_dir}/{plot_file}")
                                i += 1

        return texts, files

    def handle_fetch_cmd(self):
        """
        Handle fetch subcommand of does.
        """

        do_list_results = self.args.show
        do_fetch_logs = self.args.logs
        commits = self.args.commit
        plots_subdirs = self.args.plots
        do_fetch_plots = plots_subdirs is not None

        if not commits and not (do_list_results or do_fetch_logs):
            parser.print_help()
            return

        self.state.update()

        if do_list_results:
            if len(self.state.results) > 0:
                results_sorted = sorted(self.state.results, key=lambda r: r.timestamp)

                print("The following results are available:")
                for result in results_sorted:
                    if not self.is_run_from_cmd:
                        status_indicator = BENCH_PROGRESS_TO_EMOJI[result.progress]
                        time = str(datetime.fromtimestamp(result.timestamp))
                        print(f"\t- {result.suite} {status_indicator}:\n\t\t- time: {time}\n\t\t- ID: {result.commit}")
                    else:
                        print(f"\t- {result}")
            else:
                print("No results stored")
            return

        if do_fetch_logs:
            texts = []
            log_files = []
            for commit in commits:
                result = self.state.get_result(commit)

                texts.append(f"Error log file for commit {result.commit}:")
                log_files.append(result.stderr_file)
                texts.append(f"Stdout log file for commit {result.commit}:")
                log_files.append(result.stdout_file)

            return texts, None, log_files
        else:
            return self.fetch_results(commits, plots_subdirs)

    def handle_plot_cmd(self):
        """
        Handle plot subcommand of does.
        """

        commit = self.args.commit
        plots_subdirs = self.args.path
        plot_exts = self.args.ext

        result = self.state.get_result(commit)

        if not result:
            print(f"No results stored for commit {commit}.\n"
                   "Available results can be listed with `does fetch -s`")
            return

        p = subprocess.run([
            "poetry",
            "run",
            "python3",
            "src/scripts/etl.py",
            "--suite",
            result.suite,
            "--id",
            str(result.suite_id)

        ], cwd=self.state.doe_suite)

        if p.returncode != 0:
            return f"Plotting failed with return code {p.returncode}.\nError:\n{p.stderr.decode()}", None, None

        texts, files = self.get_plot_files([result], plots_subdirs, plot_exts)

        return texts, None, files

    def handle(self):
        if self.args.command == "ansible":
            return self.handle_ansible_cmd()
        if self.args.command == "aws":
            return self.handle_aws_cmd()
        elif self.args.command == "fetch":
            return self.handle_fetch_cmd()
        elif self.args.command == "plot":
            return self.handle_plot_cmd()
        else:
            logging.warning(f"Unknown primary command {self.args.command}")


def output_wrapper(fn, say, *args, **kwargs):
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

    response = None
    success = True
    out, out_markdown = None, None
    try:
        response = fn(say, *args, **kwargs)
    except SystemExit:
        rc = sys.exc_info()[1].code
        success = rc == 0

    sys.stdout = cmd_stdout
    if not success:
        logging.error(f"Caught system exit with return code {rc}")
        return f"ERROR: executing the function with '{args}' and '{kwargs}' failed unexpectedly " + \
               f"with error code {rc}!", None, None
    elif response:
        return response
    else:
        return str_stdout.getvalue(), None, None

def set_log_level(args):
    if args.log_level:
        numeric_level = getattr(logging, args.log_level.upper(), None)

        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % loglevel)

        logging.basicConfig(level=numeric_level)

def does_master_exec_helper(say, args_str, *args, **kwargs):
    parser = get_parser()
    args = parser.parse_args(shlex.split(args_str))
    set_log_level(args)

    does = DOESMaster(args, parser, say, DOES_BRANCH)
    return does.handle()

def does_master_exec(args_str, say):
    """
    Parse the argument string and execute the does binary with those arguments.
    Return messages and files found by the does command to return to slack.
    """
    return output_wrapper(does_master_exec_helper, say, args_str)

def does_fetch_results_helper(say, commits, plots_subdir, *args, **kwargs):
    does = DOESMaster("", None, say, DOES_BRANCH)
    return does.fetch_results(commits, plots_subdir)

def does_fetch_results(commits, plots_subdir):
    """
    Fetch results for the given commits. If plots_subdir is set, only plots from there are fetched.
    Otherwise, the entire result directory is put into an archive.
    """
    return output_wrapper(does_fetch_results_helper, None, commits, plots_subdir)


if __name__ == '__main__':
    parser = get_parser()
    args = parser.parse_args()
    set_log_level(args)
    does = DOESMaster(args, parser, None, DOES_BRANCH)
    out = does.handle()
    if out:
        stdout, texts, files = out

        if stdout:
            print(stdout)
        if texts:
            for text in texts:
                print(text)
        if files and len(files) > 0:
            print("\nAttachments:")
            for f in files:
                print(f"\t- {f}")

