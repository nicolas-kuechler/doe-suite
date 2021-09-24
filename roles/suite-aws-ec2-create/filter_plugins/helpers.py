

def to_tag_assignment(ec2_instances_info, host_types):

    """
    Given the available ec2 instances and the requirements for the suite (in `host_types`),
    the function returns an assignment (i.e., which instance is used in which experiment).

    ec2_instance_info: a list of dictionaries retrieved from module: `community.aws.ec2_instance_inf`
    host_types: a dictionary with all host types of the suite and their experiments{<HOST_TYPE>: {<EXP_NAME>: X}} 
    
    return: list of dicts [{"instance_id" X, "exp_name": X, ...}, ...] that decides which ec2 instances to use in which experiment. 
    """


    #  sort ec2_instances_info by instance_id to achieve consistent assignment
    list(sorted(ec2_instances_info, key=lambda instance_info: instance_info["instance_id"]))

    lst = []

    # group instance ids by host type
    instances = {}
    for instance_info in ec2_instances_info:
        
        host_type = instance_info["tags"]["host_type"]

        if host_type not in instances:
            instances[host_type] = []
        instances[host_type].append(instance_info["instance_id"])

    exps_with_controller = set()

    for host_type, experiments in host_types.items():

        for exp_name, info in experiments.items():


            if "init_role" in host_types[host_type][exp_name]:
                init_role = host_types[host_type][exp_name]["init_role"]
            else: init_role = "-"


            check_status = 'yes' if  bool(host_types[host_type][exp_name]["check_status"]) else 'no'
            
            # take n instances and assign to this experiment
            for i in range(info["n"]):
                instance_id = instances[host_type].pop(0)
                
                if exp_name in exps_with_controller:
                    is_controller = 'no'
                else:
                    exps_with_controller.add(exp_name)
                    is_controller = 'yes'

                d = {"instance_id": instance_id, 
                        "exp_name": exp_name, 
                        "is_controller": is_controller, 
                        "host_type": host_type, 
                        "exp_host_type_idx": i, 
                        "exp_host_type_n": info["n"], 
                        "init_roles": init_role,

                        "check_status": check_status}
                lst.append(d)


    return lst


class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            'to_tag_assignment': to_tag_assignment,
        }