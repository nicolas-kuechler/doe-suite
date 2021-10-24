
import json
import shutil
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
    def __init__(self, path, commit):
        self.timestamp = time.time()
        self.path = path
        self.commit = commit
        self.progress = "running"

    def __str__(self):
        timestamp = datetime.fromtimestamp(self.timestamp)
        return f"{{ timestamp: {timestamp}, path: {self.path}, commit: {self.commit}, progress: {self.progress}}}"

# Structure of the kept state:
# {
#    "does_home": "path/to/does/suite",
#    "results": [ Result(), ... ]
# }
class State():
    def __init__(self, path, home):
        self.path = path
        self.state = { "home": home, "results": [] }
        self.store()

    def __str__(self):
        datetime = datetime.fromtimestamp(self.state)
        return f"timestamp: {datetime.fromtimestamp()}"

    def cleanup_results(self, oldest_log_timestamp=None):
        if not oldest_log_timestamp:
            # Default: keep logs for 1 week
            oldest_log_timestamp = datetime.now() - timedelta(days=DAYS_TO_PRESERVE_RESULTS)

        to_remove = []
        for result in self.state["results"]:
            if datetime.fromtimestamp(result.timestamp) < oldest_log_timestamp:
                logging.debug("Removing results for commit", result.commit)
                shutil.rmtree(result.path)
                to_remove.append(result)

        for result in to_remove:
            self.state.remove(result)

    def update(self):
        with open(self.path, "r") as fp:
            self.state = json.load(fp)

        self.cleanup_results()

    def store(self):
        with open(self.path, "w+") as fp:
            fp.write(json.dumps(self.state))

    def add_new_result(self, path, commit):
        self.state["results"].append(Result(path, commit))
