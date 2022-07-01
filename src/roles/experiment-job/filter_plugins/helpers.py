
import json, os


def to_job_schedule_lst(job_ids, exp_host_lst, exp_runs_ext, working_base_dir):

    job_schedule_lst = []


    for job_id in job_ids:
        for host_info in exp_host_lst:

            run_idx = int(job_id["exp_run"])
            host_type = host_info["host_type"]
            host_type_idx = host_info["exp_host_type_idx"]

            d = {
                "host_info": host_info,
                "job_info": job_id,
                "exp_run_config": exp_runs_ext[run_idx],
                # TODO [nku] for multi command support, need to change this here and also use other than main
                "exp_run_cmd": exp_runs_ext[run_idx]["$CMD$"][host_type][host_type_idx]["main"],
                "exp_working_dir":  jobid2workingdir(job_id, working_base_dir)
            }

            job_schedule_lst.append(d)

    return job_schedule_lst


def jobid2workingdir(job_id, base):

    """
    Derives the path for the working directory corresponding to the job_id within `base`.

    job_id: {'suite': X, 'suite_id': X, 'exp_name': X, ... }
    base: a path to a directory in which the workingdir resides

    return: path to the working directory for a job
    """

    exp_working_dir = os.path.join(base,
                f"{job_id['suite']}_{job_id['suite_id']}",
                job_id['exp_name'],
                f"run_{job_id['exp_run']}",
                f"rep_{job_id['exp_run_rep']}")

    return exp_working_dir




class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            "to_job_schedule_lst": to_job_schedule_lst,
            "jobid2workingdir": jobid2workingdir,
        }
