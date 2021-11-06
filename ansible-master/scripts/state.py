
import json
import logging
import os
import shutil
import traceback
import time

from datetime import datetime, timedelta

# keep logs for 1 week (7 days)
DAYS_TO_PRESERVE_RESULTS = 7


class Result():
    """
    Structure of a result
        "suite": suite name
        "suite_id": suite id (time of creation in seconds from the epoch)
        "timestamp": timestamp when the result was started
        "subdir": "sub folder of the results (parent folder is specified by the state)",
        "commit": "hash",
        "progress": "running"/"done"/"failed",
    """

    def __init__(self, *args):
        """
        Different numbers of arguments are possible:
            - 1 argument: json string of a state
            - 2 arguments: suite, path, commit (in this order)
            - 3 arguments: suite, suite_id, path, commit (in this order)
        """
        if len(args) == 2 or len(args) == 3:
            if len(args) == 2:
                suite, commit = args
                self.suite_id = int(time.time())
                self.timestamp = self.suite_id
            else:
                suite, self.suite_id, commit = args
                self.timestamp = int(time.time())

            self.suite = suite
            self.subdir = f"{self.state.suite}_{self.state.suite_id}"
            self.commit = commit
            self.progress = "running"
        elif len(args) == 1:
            d, = args

            self.suite = d["suite"]
            self.suite_id = d["suite_id"]
            self.timestamp = d["timestamp"]
            self.subdir = d["subdir"]
            self.commit = d["commit"]
            self.progress = d["progress"]
        else:
            logging.error("Invalid number of arguments for Result!")
            exit(1)

    def to_json(self):
        d = {
            "suite": self.suite,
            "suite_id": self.suite_id,
            "timestamp": self.timestamp,
            "subdir": self.subdir,
            "commit": self.commit,
            "progress": self.progress
        }
        return d

    def __str__(self):
        j = self.to_json()
        j["timestamp"] = str(datetime.fromtimestamp(j["timestamp"]))
        return str(j)

    def __cmp__(self, other):
        return self.commit.__cmp__(other.commit)


class State():
    """
    Structure of the kept state:
       "path": "path/to/state"
       "doe_suite": "path/to/does/suite",
       "does_results": "path/to/does_results",
       "results": { Result(), ... }
    """

    def __init__(self, path, doe_suite, does_results):
        self.path = path
        self.does_results = does_results
        self.init_state(doe_suite, set())
        self.store()

    def __str__(self):
        return f"doe_suite: {self.doe_suite}, results: {self.results}"

    def init_state(self, doe_suite, results):
        if os.path.exists(self.path):
            # load old state
            self.update()

            if self.doe_suite != doe_suite:
                logging.error(
                    "Conflicting state detected! Delete the file in {self.path} to start a new run.\n"
                    f"Conflicting state:\n{self}"
                )
                exit(1)

            logging.debug("Using stored state.")
            self.results = self.results.union(results)
        else:
            self.doe_suite = doe_suite
            self.results = results


    def cleanup_results(self, oldest_log_timestamp=None):
        if not oldest_log_timestamp:
            # Default: keep logs for 1 week
            oldest_log_timestamp = datetime.now() - timedelta(days=DAYS_TO_PRESERVE_RESULTS)

        to_remove = []
        for result in self.results:
            if datetime.fromtimestamp(result.timestamp) < oldest_log_timestamp:
                logging.debug("Removing results for commit", result.commit)
                shutil.rmtree(result.path)
                to_remove.append(result)

        for result in to_remove:
            self.results.remove(result)

    def to_json(self):
        d = {
            "results": [r.to_json() for r in self.results],
            "doe_suite": self.doe_suite,
            "does_results": self.does_results
        }
        return d

    def update(self):
        with open(self.path, "r") as fp:
            try:
                state = json.load(fp)
            except Exception:
                logging.error(f"Cannot read state file, invalid format!\nError:")
                traceback.print_exc()
                exit(1)

            self.doe_suite = state["doe_suite"]
            self.does_results = state["does_results"]
            self.results = {Result(r) for r in state["results"]}
        self.cleanup_results()

    def store(self):
        with open(self.path, "w+") as fp:
            fp.write(json.dumps(self.to_json()))

    def add_new_result(self, commit):
        self.results.add(Result(commit))
        self.store()
