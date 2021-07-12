import pandas as pd
import yaml, json, csv

import os, re, warnings

def _load_config_yaml(path, file="config.yml"):
    with open(os.path.join(path, file)) as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    return config

def _list_dir_only(path):
    return [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]

def _list_files_only(path):
    return [f for f in os.listdir(path) if not os.path.isdir(os.path.join(path, f))]


def _flatten_d(d):
    return json.loads(pd.json_normalize(d, sep='.').iloc[0].to_json())
    
def _parse_file(path, file, regex_error_file, regex_ignore_file, regex_csv_result_file, regex_json_result_file, regex_yaml_result_file):
    """
    returns list of dicts
    """
    
    file_path = os.path.join(path, file)
    
    d_lst = None
    
    if any(regex.match(file) for regex in regex_error_file):
        # is an error file -> output a warning (unless file is empty)
        
        with open(file_path, 'r') as f:
            content = f.read().replace('\n', ' ')
        
        if content.strip() and not content.strip().isspace(): # ignore empty error files 
            warnings.warn(f"found error file: {file} in {path}")
            warnings.warn(f"   {content}")
        
        d_lst = []
        
        
    elif any(regex.match(file) for regex in regex_ignore_file):
        # ignore this file
        d_lst = []
                   
    elif any(regex.match(file) for regex in regex_csv_result_file):
        # this is a result file in csv format                     
        d_lst = []
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                d_lst.append(row)


        
    elif any(regex.match(file) for regex in regex_json_result_file):
        # this is a result file in json format
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        if not isinstance(data, list):
            data = [data]
        d_lst = data
                        
    elif any(regex.match(file) for regex in regex_yaml_result_file):
        # this is a result file in yaml format
        
        with open(file_path, 'r') as f:
            data = yaml.load(f)
            
        if not isinstance(data, list):
            data = [data]
        d_lst = data
                    
    else:
        raise ValueError(f"unexpected result file: {file} in {path}")
        
    return d_lst


def read_df(results_dir, exp, regex_error_file = [re.compile(r".*_stderr\.log$")],
                    regex_ignore_file = [re.compile(r".*_stdout\.log$")],
                    regex_csv_result_file=[re.compile(r".*\.csv$")],
                    regex_json_result_file=[re.compile(r".*\.json$")],
                    regex_yaml_result_file=[re.compile(r".*\.yml$"), re.compile(r".*\.yaml$")]):

    """Read the experiment results into a pandas dataframe.

    Traverses the folder structure of an experiment (or more) and uses the provided regex lists to decide how to process the files.

    Parameters:
    results_dir: the base folder where the results are located
    exp: a dict that controls which results to include {exp_name: [exp_id_1, exp_id_2, ...]}
    regex_error_file: a list of regex that matches files that indicate errors if they are non-empty (outputs a warning)
    regex_ignore_file: a list of regex that matches files to ignore (e.g., stdout)
    regex_csv_result_file: a list of regex that match result files in csv format (first row is header, then there can be multiple rows of results)
    regex_json_result_file: a list of regex that match result files in json format (a dict with a single result or a list of dicts where each entry corresponds to a result)
    regex_yaml_result_file: a list of regex that match result files in yaml format (a dict with a single result or a list of dicts where each entry corresponds to a result)
    
    Returns:
    a pandas dataframe that contains the configuration and the results (nested dictionaries are flattened with a '.' as a separator)
    """

    res_lst = []

    for exp_name in exp.keys():
        for exp_id in exp[exp_name]:
            exp_dir = os.path.join(results_dir, f"exp_{exp_name}_{exp_id}")
            runs = os.listdir(exp_dir)

            for run in runs:
                run_dir = os.path.join(exp_dir, run)
                reps = _list_dir_only(run_dir)

                for rep in reps:
                    rep_dir = os.path.join(run_dir, rep)

                    config = _load_config_yaml(path=rep_dir, file="config.yml")
                    
                    # ignores the part of the config that shows what is varied
                    del config["~FACTORS_LEVEL"]

                    config_flat = _flatten_d(config)
                    
        
                    hosts = _list_dir_only(rep_dir)
                    for host in hosts:
                        host_dir = os.path.join(rep_dir, host)

                        files = _list_files_only(host_dir)

                        job_info = {"exp_name": exp_name, "exp_id": exp_id, "run": run, "rep": rep, "host": host}

                        for file in files:

                            d_lst = _parse_file(host_dir, file, regex_error_file, regex_ignore_file, regex_csv_result_file, regex_json_result_file, regex_yaml_result_file)

                            for d in d_lst:
                                d_flat = _flatten_d(d)
                                res = {**job_info, **config_flat, **d_flat}
                                res_lst.append(res)

    df = pd.DataFrame(res_lst)
    return df