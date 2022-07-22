import shutil
import argparse

from doespy import util, status


def delete_incomplete_results():

    for x in util.get_all_suite_results_dir():
        # x["suite"]
        # x["suite_id"]
        # x["path"]
        suite_status, etl_error = status.get_suite_status(x["path"])

        is_suite_complete = None
        for exp, d in suite_status.items():

            if d["is_complete"] and is_suite_complete is None:
                is_suite_complete = True

            if not d["is_complete"]:
                is_suite_complete = False

        if is_suite_complete is None or not is_suite_complete:
            # incomplete suite -> delete
            assert x[
                "id_is_number"
            ], f"cannot delete non number suite  {x['suite']}   {x['suite_id']}"

            print(f"Deleting folder {x['path']}")
            shutil.rmtree(x["path"], ignore_errors=False)


def keep_last_complete_results():
    # incomplete suites cannot be kept
    delete_incomplete_results()

    # compute unique suites
    suites = {}
    for x in util.get_all_suite_results_dir():
        if x["id_is_number"]:
            suites[x["suite"]] = -1

    # compute highest suite id -> run to keep
    for suite in suites.keys():
        keep_suite_id = util.get_last_suite_id(suite)
        suites[suite] = keep_suite_id

    for x in util.get_all_suite_results_dir():
        if x["id_is_number"] and suites[x["suite"]] != x["suite_id"]:
            # delete suite
            print(f"Deleting folder {x['path']}")
            shutil.rmtree(x["path"], ignore_errors=False)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--incomplete", action="store_true")
    parser.add_argument("--keeplast", action="store_true")
    args = parser.parse_args()

    if args.incomplete:
        delete_incomplete_results()
    if args.keeplast:
        keep_last_complete_results()
