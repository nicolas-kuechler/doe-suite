import os, yaml
from glob import glob
from jinja2 import Environment

def get_project_dir():
    if "DOES_PROJECT_DIR" not in os.environ:
        raise ValueError(f"env variable: DOES_PROJECT_DIR not set")
    prj_dir = os.environ["DOES_PROJECT_DIR"]
    return prj_dir

def get_ssh_keyname():
    if "DOES_SSH_KEY_NAME" not in os.environ:
        raise ValueError(f"env variable:DOES_SSH_KEY_NAME not set")
    ssh_keyname = os.environ["DOES_SSH_KEY_NAME"]
    return ssh_keyname

def get_project_id():
    if "DOES_PROJECT_ID_SUFFIX" not in os.environ:
        raise ValueError(f"env variable:DOES_PROJECT_ID_SUFFIX not set")
    suffix = os.environ["DOES_PROJECT_ID_SUFFIX"]
    with open(os.path.join(get_config_dir(), "group_vars", "all", "main.yml")) as f:
        vars = yaml.load(f, Loader=yaml.SafeLoader)

    prj_id = Environment().from_string(vars["prj_id"]).render(does_project_id_suffix=suffix)
    return prj_id


def get_suite_design(suite):
    path = os.path.join(get_config_dir(), "designs", f"{suite}")
    with open(path, "r") as f:
        design = yaml.load(f, Loader=yaml.SafeLoader)
    return design

def get_config_dir():
    prj_dir = get_project_dir()
    config_dir = os.path.join(prj_dir, "does_config")
    return config_dir

def get_results_dir():
    prj_dir = get_project_dir()
    results_dir = os.path.join(prj_dir, "does_results")
    return results_dir

def get_folder(suite, suite_id):
    return f"{suite}_{suite_id}"


def find_suite_result(suite=None, id="last"):
    if suite is None and id == "last":
        # -> last result overall
        max_suite_id = None
        for res in  glob(os.path.join(get_results_dir(), "*", "")):

            parts = os.path.basename(os.path.dirname(res)).split("_")
            suite_id = parts[-1]
            try:
                suite_id = int(suite_id)
                if max_suite_id is None or suite_id > max_suite_id:
                    max_suite_id = suite_id
                    suite = "_".join(parts[:-1]) # combine first part together (after removing id)
            except ValueError:
                continue

        suite_id = str(max_suite_id)

    elif suite is not None and id == "last":
        # -> find  highest suite id
        suite_id = get_last_suite_id(suite)

    elif id != "last":
        # -> search for folder with this id + compare with suite
        res = glob(os.path.join(get_results_dir(), f"*_{id}"))
        assert len(res) == 1
        parts = os.path.basename(os.path.dirname(res[0])).split("_")
        found_suite = "_".join(parts[:-1])
        if suite is None:
            suite = found_suite
        else:
            assert suite == found_suite
        suite_id = id

    return suite, suite_id

def get_last_suite_id(suite):
    results_dir = get_results_dir()

    max_suite_id = None
    for x in glob(os.path.join(results_dir, f"{suite}*", "")):
        suite_id = os.path.basename(os.path.dirname(x)).split("_")[-1]
        try:
            suite_id = int(suite_id)
            if max_suite_id is None or suite_id > max_suite_id:
                max_suite_id = suite_id
        except ValueError:
            continue

    if max_suite_id is None:
        raise ValueError(f"cannot use `--id last` because no results found in {results_dir} for suite: {suite}")

    return str(max_suite_id)
