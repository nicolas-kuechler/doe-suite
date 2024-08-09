import os
import ruamel.yaml
import jinja2
import jmespath
from glob import glob
import importlib.util

def get_project_dir():
    if "DOES_PROJECT_DIR" not in os.environ:
        raise ValueError("env variable: DOES_PROJECT_DIR not set")
    prj_dir = os.environ["DOES_PROJECT_DIR"]
    return prj_dir


def get_ssh_keyname():
    if "DOES_SSH_KEY_NAME" not in os.environ:
        raise ValueError("env variable:DOES_SSH_KEY_NAME not set")
    ssh_keyname = os.environ["DOES_SSH_KEY_NAME"]
    return ssh_keyname


def get_project_id():
    if "DOES_PROJECT_ID_SUFFIX" not in os.environ:
        raise ValueError("env variable:DOES_PROJECT_ID_SUFFIX not set")
    suffix = os.environ["DOES_PROJECT_ID_SUFFIX"]
    with open(os.path.join(get_config_dir(), "group_vars", "all", "main.yml")) as f:
        vars = ruamel.yaml.safe_load(f)

    prj_id = (
        jinja2.Environment()
        .from_string(vars["prj_id"])
        .render(does_project_id_suffix=suffix)
    )
    return prj_id


def get_suite_design(suite, folder=None):

    if folder is None:
        folder = get_suite_design_dir()

    env = jinja2_env(
        loader=jinja2.FileSystemLoader(folder), undefined=DebugChainableUndefined
    )

    template = env.get_template(f"{suite}.yml")
    template_vars = {}
    suite_design = template.render(**template_vars)

    suite_design = ruamel.yaml.safe_load(suite_design)
    return suite_design


def get_suite_design_path(suite):
    path = os.path.join(get_config_dir(), "designs", f"{suite}.yml")
    return path


def get_config_dir():
    prj_dir = get_project_dir()
    config_dir = os.path.join(prj_dir, "doe-suite-config")
    return config_dir


def get_super_etl_dir():
    return os.path.join(get_config_dir(), "super_etl")

def get_all_super_etl_configs():
    super_etl_configs = [os.path.splitext(x)[0] for x in _list_files_only(get_super_etl_dir())]
    return super_etl_configs




def get_super_etl_output_dir():
    os.path.join(get_results_dir(), "super_etl")


def get_suite_design_dir():
    return os.path.join(get_config_dir(), "designs")


def get_suite_design_vars_dir():
    return os.path.join(get_suite_design_dir(), "design_vars")


def get_suite_group_vars_dir():
    return os.path.join(get_config_dir(), "group_vars")


def get_suite_roles_dir():
    return os.path.join(get_config_dir(), "roles")


def get_results_dir():
    prj_dir = get_project_dir()
    results_dir_name = "doe-suite-results"
    results_dir = os.environ.get("DOES_RESULTS_DIR", os.path.join(prj_dir, results_dir_name))
    return results_dir


def get_suite_results_dir(suite, id, exp=None):

    # resolve logic with last and defaults if not set
    suite, id = find_suite_result(suite=suite, id=id)

    result_dir = os.path.join(get_results_dir(), get_folder(suite=suite, suite_id=id))

    if exp is not None:
        result_dir = os.path.join(result_dir, exp)

    return result_dir


def get_all_suite_results_dir():

    results = []
    for res in glob(os.path.join(get_results_dir(), "*", "")):

        parts = os.path.basename(os.path.dirname(res)).split("_")
        suite_id = parts[-1]
        suite = "_".join(parts[:-1])  # combine first part together (after removing id)

        try:
            int(suite_id)
            id_is_number = True
        except ValueError:
            id_is_number = False

        results.append(
            {
                "suite": suite,
                "suite_id": suite_id,
                "path": res,
                "id_is_number": id_is_number,
            }
        )

    return results


def get_etl_results_dir(suite, id, output_dir="etl_results"):
    results_dir = get_suite_results_dir(suite, id)
    return os.path.join(results_dir, output_dir)


def get_folder(suite, suite_id):
    return f"{suite}_{suite_id}"


def from_folder(name):
    parts = name.split("_")
    suite_id = parts[-1]
    suite = "_".join(parts[:-1])
    return suite, suite_id


def get_does_results(ignore_expected=True):
    results_dir = get_results_dir()

    does_results = []
    for suite_run_id in os.listdir(results_dir):
        if os.path.isdir(os.path.join(results_dir, suite_run_id)):
            suite, suite_id = from_folder(name=suite_run_id)

            if not ignore_expected or suite_id != "$expected":
                does_results.append({"suite": suite, "suite_id": suite_id})

    return does_results


def get_does_result_experiments(suite, suite_id):
    res_dir = get_suite_results_dir(suite=suite, id=suite_id)
    suite_design = load_config_yaml(res_dir, file="suite_design.yml")
    experiments_in_design = {x for x in suite_design.keys() if not x.startswith("$")}

    experiments_in_results = [exp for exp in _list_dir_only(res_dir) if exp in experiments_in_design]

    return experiments_in_results



def find_suite_result(suite=None, id="last"):
    if suite is None and id == "last":
        # -> last result overall
        max_suite_id = None
        for res in glob(os.path.join(get_results_dir(), "*", "")):

            parts = os.path.basename(os.path.dirname(res)).split("_")
            suite_id = parts[-1]
            try:
                suite_id = int(suite_id)
                if max_suite_id is None or suite_id > max_suite_id:
                    max_suite_id = suite_id
                    suite = "_".join(
                        parts[:-1]
                    )  # combine first part together (after removing id)
            except ValueError:
                continue

        suite_id = str(max_suite_id)

    elif suite is not None and id == "last":
        # -> find  highest suite id
        suite_id = get_last_suite_id(suite)

    elif suite is None and id != "last" and id != "$expected":
        # -> search for folder with this id + compare with suite
        res = glob(os.path.join(get_results_dir(), f"*_{id}"))
        gpath = os.path.join(get_results_dir(), f"*_{id}")
        print(f"suite={suite}   id={id}   glob={gpath}  res={res}")
        assert len(res) == 1, res
        parts = os.path.basename(res[0]).split("_")
        found_suite = "_".join(parts[:-1])
        if suite is None:
            suite = found_suite
        else:
            assert suite == found_suite, f"suite={suite}   found_suite={found_suite}"
        suite_id = id
    else:
        suite = suite
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
        raise ValueError(
            "cannot use `--id last` because no results",
            f" found in {results_dir} for suite: {suite}",
        )

    return str(max_suite_id)

class DebugChainableUndefined(jinja2.ChainableUndefined, jinja2.DebugUndefined):
    pass

def jinja2_env(loader, undefined, variable_start_string="{{", variable_end_string="}}"):

    env = jinja2.Environment(
        loader=loader,
        undefined=undefined,
        variable_start_string=variable_start_string,
        variable_end_string=variable_end_string,
    )

    def lookup(type, var):
        if type == "env":
            return os.environ[var]
        else:
            raise ValueError(
                f"this type of lookup is not supported: {type}  (var={var})"
            )

    env.globals["lookup"] = lookup

    # small hack to also provide json_query functionality
    def json_query(data, expr):
        return jmespath.search(expr, data)

    env.filters["json_query"] = json_query

    from distutils.util import strtobool
    env.filters["bool"] = strtobool

    from math import ceil, floor
    env.filters["ceil"] = ceil
    env.filters["floor"] = floor

    # load design specific fiters
    filter_folder = os.path.join(get_suite_design_dir(), "filter_plugins")
    source_files = [file for file in os.listdir(filter_folder) if file.endswith(".py")] \
        if os.path.exists(filter_folder) else [] # skip if folder does not exist for backwards compatibility
    for file in source_files:
        try:
            path = os.path.join(filter_folder, file)
            module_name = 'design_filters_' + file.removesuffix(".py")
            DesignFilterSpec = importlib.util.spec_from_file_location(module_name, path)
            DesignFilterModule = importlib.util.module_from_spec(DesignFilterSpec)
            DesignFilterSpec.loader.exec_module(DesignFilterModule)
            design_filters = DesignFilterModule.FilterModule().filters()
        except:
            continue
        if isinstance(design_filters, dict):
            for name, function in design_filters.items():
                env.filters[name] = function
        else:
            raise ValueError(
                f"filters method for FilterModule in Design does not return dict"
            )

    return env


def get_suite_design_etl_template_dir():
    return os.path.join(get_suite_design_dir(), "etl_templates")

#def get_suites():
#    get_suite_design_dir()


def get_host_types():
    host_types = [x for x in os.listdir(get_suite_group_vars_dir()) if x not in ["all", "ansible_controller"]]
    return host_types


def get_setup_roles():
    roles = os.listdir(get_suite_roles_dir())
    return roles


def _list_dir_only(path):
    lst = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    return lst

def _list_files_only(path):
    def _is_file(path, f):
        return not os.path.isdir(os.path.join(path, f))

    lst = [f for f in os.listdir(path) if _is_file(path, f)]
    return lst

def load_config_yaml(path, file="config.json"):
    #yaml = ruamel.yaml.YAML(typ='safe', pure=True)
    with open(os.path.join(path, file)) as file:
        #config = yaml.load(file)
        config = ruamel.yaml.safe_load(file)
    return config