def extend_tsp_label(d, job_host_assignment):
    """
    extend the dictionary by parsing the label and adding host info
    """

    parts = d["label"].split('_')

    d["exp_name"] = parts[0]
    d["exp_id"] = parts[1]
    d["exp_run"] = parts[2]
    d["exp_run_rep"] = parts[3]
    d["job_id"] = d["exp_run"] + "_" + d["exp_run_rep"]
    d["host_info"] = job_host_assignment[d["job_id"]]
    
    return d

class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            'extend_tsp_label': extend_tsp_label,
        }