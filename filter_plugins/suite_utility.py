import os

def jobid2workingdir(job_id, base):

    exp_working_dir = os.path.join(base, "results", 
                f"{job_id['suite']}_{job_id['suite_id']}", 
                job_id['exp_name'], 
                f"run_{job_id['exp_run']}",
                f"rep_{job_id['exp_run_rep']}")
    
    return exp_working_dir



class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            'jobid2workingdir': jobid2workingdir
        }