
import json

def tsp_job_finished(tsp_tasks, job_id):

    # states = ["running", "queued", "finished"]

    for task in tsp_tasks:

        task_job_id = json.loads(task["label"])

        if task_job_id == job_id:
            # found matching job

            #print(f"matching task={task}")

            # TODO [nku] add improved error handling

            if task["state"] == "running" or task["state"] ==  "queued":
                return False
            elif task["state"] == "finished":
                return True
            else:
                raise ValueError(f"tsp task with unknown task state = {task['state']}   (task={task})")

        
    raise ValueError(f"no matching job found in tsp: {job_id}   tsp_tasks={tsp_tasks}")

def get_tsp_task_id(tsp_tasks, job_id):
    for task in tsp_tasks:

        task_job_id = json.loads(task["label"])

        if task_job_id == job_id:
            return task["id"]

    raise ValueError(f"no matching job found in tsp: {job_id}   tsp_tasks={tsp_tasks}")



class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            "tsp_job_finished": tsp_job_finished,
            "get_tsp_task_id": get_tsp_task_id,
        }