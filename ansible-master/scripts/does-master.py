#!/usr/bin/env python3

import argparse
import logging
import os
import tempfile
import shutil
import subprocess

from state import State

OUT_FOLDER = "~/.does-master"
LOG_FOLDER = f"{OUT_FOLDER}/logs"
STATE_PATH = f"{OUT_FOLDER}/state.json"
RESULTS_ZIP_PATH = "/tmp/results.zip"

def parse_arguments():
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
        help="Commit that triggered this run",
        default="manual", type=str)
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

    return parser.parse_args()

def create_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)
    else:
        logging.debug(f"Could not create folder, path '{path}' already exists.")

def setup_outdir():
    create_folder(OUT_FOLDER)
    create_folder(LOG_FOLDER)

def handle_ansible_cmd(args, state):
    benchmark = args.benchmark
    commit = args.commit

    # TODO: change project ID to commit hash -> add functionality to kill old benchmarks
    # subprocess.run(["poetry", "run", "ansible-playbook", "src/experiment-suite.yml", "-e", f"suite={benchmark} id=new"], cwd=self.state["home"])

    # TODO: get result path fron ETL pipeline!
    path = ""
    state.add_new_result(path, commit)

def handle_slack_cmd(args, state):
    files_to_post = args.post
    channel = args.channel

    state.update()

def handle_results_cmd(args, state):
    do_list_results = args.list
    files_to_fetch = args.fetch

    state.update()

    if do_list_results:
        for result in self.state["results"]:
            print(f"\t-", result)
        return

    # TODO: add functionality to fetch all results for a commit

    results_path = tempfile.mkdtemp()

    for result in self.state["results"]:
        if result["path"] in files_to_fetch:
            commit_folder = f"{results_path}/{result['commit']}"
            create_folder(commit_folder)

            # TODO: find better way to not overwrite result files
            shutil.copyfile(result["path"], f"{commit_folder}/{results_path.split('/')[1]}")

    if os.path.exists(RESULTS_ZIP_PATH):
        os.remove(RESULTS_ZIP_PATH)

    shutil.make_archive(RESULTS_ZIP_PATH, "zip", results_path)

    print(f"Download the requested files from {RESULTS_ZIP_PATH} (e.g., using scp).")

if __name__ == '__main__':
    setup_outdir()
    state = State(STATE_PATH, os.environ["DOES_PROJECT_DIR"])

    args = parse_arguments()

    if args.command == "ansible":
        handle_ansible_cmd(args, state)
    elif args.command == "slack":
        handle_slack_cmd(args, state)
    elif args.command == "results":
        handle_results_cmd(args, state)
    else:
        logging.warning(f"Unknown primary command {args.command}")
