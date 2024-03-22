
import json, os

# from ...filter_plugins.helpers import safe_job_info_string


def tsp_jobs_finished(job_ids, tsp_tasks):


    completed_jobs = []

    for task in tsp_tasks:

        if task["state"] == "finished":
            task_job_id = json.loads(task["label"])

            if task_job_id in job_ids:
                completed_jobs.append(task_job_id)
            else:
                raise ValueError(f"no matching job found in tsp: {job_ids}   tsp_tasks={tsp_tasks}")

        elif task["state"] == "running" or task["state"] ==  "queued":
            pass
        else:
            raise ValueError(f"tsp task with unknown task state = {task['state']}   (task={task})")


    return completed_jobs




def get_tsp_task_id(tsp_tasks, job_id):

    """
    return: the tsp id of the task with the provided job_id
    """

    for task in tsp_tasks:

        task_job_id = json.loads(task["label"])

        if task_job_id == job_id:
            return task["id"]

    raise ValueError(f"no matching job found in tsp: {job_id}   tsp_tasks={tsp_tasks}")




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


def bsub_jobs_finished(queued_jobs, bjobs):
    """
    Determines newly finished tasks.

    :param queued_jobs:
    :param bjob_tasks:
    :return: job from queued_jobs
    """
    # TODO: Somehow import this from global helpers file, as this is duplicated code
    def safe_job_info_string(job_info):
        """
        Transforms job_info into a safe string that can be read by external systems

        :type job_info: dict
        """
        # transforms job info into safe string
        order = ["suite", "suite_id", "exp_name", "exp_run", "exp_run_rep"]
        safe_elements = [f"{item}_{job_info[item]}" for item in order]

        return "__".join(safe_elements)

    queued_or_running_labels = [bjob["label"] for bjob in bjobs]

    completed_jobs = []

    for queued_job in queued_jobs:
        safe_id = safe_job_info_string(queued_job)

        if safe_id not in queued_or_running_labels:
            # job has finished
            return completed_jobs.append(queued_job)

    if len(completed_jobs) == 0:
        return ''
    else:
        return completed_jobs


class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            "tsp_jobs_finished": tsp_jobs_finished,
            "bsub_jobs_finished": bsub_jobs_finished,
            "get_tsp_task_id": get_tsp_task_id,
            "jobid2workingdir": jobid2workingdir,
        }
