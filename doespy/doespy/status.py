import os
import ruamel.yaml
import argparse

from doespy import util


def display_suite_status(suite, suite_id):
    results_dir = util.get_results_dir()
    dir = os.path.join(results_dir, util.get_folder(suite, suite_id))

    suite_status, etl_error = get_suite_status(dir)
    title = f"Suite={suite} Id={suite_id}"
    print(title)

    if etl_error is not None:
        print(f"WARNING - ETL Pipeline Failed: {etl_error}")
    print(dir)
    print(len(title) * "-")
    for exp_name in sorted(suite_status.keys()):
        stats = suite_status[exp_name]
        print(f"{exp_name}: {stats['n_jobs_finished']}/{stats['n_jobs']} jobs")
    print(len(title) * "-")


def get_suite_status(dir):

    if os.path.exists(os.path.join(dir, "ETL_ERROR.log")):
        etl_error = os.path.join(dir, "ETL_ERROR.log")
    else:
        etl_error = None
    suite_status = {}

    for exp in os.listdir(dir):
        state_file = os.path.join(dir, exp, "state.yml")
        if not os.path.exists(state_file):
            continue

        with open(state_file) as file:
            state = ruamel.yaml.safe_load(file)
        suite_status[exp] = {}
        suite_status[exp]["n_jobs"] = len(state["exp_job_ids"])
        suite_status[exp]["n_jobs_unfinished"] = len(state["exp_job_ids_unfinished"])
        suite_status[exp]["n_jobs_finished"] = len(state["exp_job_ids_finished"])
        suite_status[exp]["is_complete"] = len(state["exp_job_ids_unfinished"]) == 0

    return suite_status, etl_error


def print_suite_status(suite_status):
    for exp, s in suite_status.items():
        print(
            f"Experiment={exp}  -  {s['n_jobs_finished']}/{s['n_jobs']} jobs done"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--suite", type=str)
    parser.add_argument("--id", type=str)
    args = parser.parse_args()

    if args.suite is not None and len(args.suite) == 0:
        args.suite = None

    if args.id is not None and len(args.id) == 0:
        args.id = "last"

    suite, suite_id = util.find_suite_result(suite=args.suite, id=args.id)

    display_suite_status(suite=suite, suite_id=suite_id)
