
import json
import logging
import os
import shutil
import traceback
import time

from datetime import datetime, timedelta

# keep logs for 1 week (7 days)
DAYS_TO_PRESERVE_RESULTS = 7


# Structure of a result
#     "timestamp": time of creation
#     "path": "/path/to/results",
#     "commit": "hash",
#     "progress": "running"/"done"/"failed",

class Result():
    def __init__(self, *args):
        if len(args) == 2:
            path, commit = args
            
            self.timestamp = time.time()
            self.path = path
            self.commit = commit
            self.progress = "running"
        elif len(args) == 1:
            d, = args

            self.timestamp = d["timestamp"]
            self.path = d["path"]
            self.commit = d["commit"]
            self.progress = d["progress"]
        else:
            logging.error("Invalid number of arguments for Result!")
            exit(1)

    def to_json(self):
        d = {
            "timestamp": self.timestamp, 
            "path": self.path, 
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

# Structure of the kept state:
#    "does_home": "path/to/does/suite",
#    "results": { Result(), ... }
class State():
    def __init__(self, path, home):
        self.path = path
        self.init_state(home, set())
        self.store()

    def __str__(self):
        return f"home: {self.home}, results: {self.results}"

    def init_state(self, home, results):
        if os.path.exists(self.path):
            # load old state
            self.update()

            if self.home != home:
                logging.error(
                    "Conflicting state detected! Delete the file in {self.path} to start a new run.\n"
                    f"Conflicting state:\n{self}"
                )
                exit(1)

            logging.debug("Using stored state.")
            self.results = self.results.union(results)
        else:
            self.home = home
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
            "home": self.home
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

            self.home = state["home"]
            self.results = {Result(r) for r in state["results"]}
        self.cleanup_results()

    def store(self):
        with open(self.path, "w+") as fp:
            fp.write(json.dumps(self.to_json()))

    def add_new_result(self, path, commit):
        self.results.add(Result(path, commit))
        self.store()
