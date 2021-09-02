

def to_tag_assignment(ec2_instances_info, host_types):
    # TODO [nku] could sort ec2_instances_info by instance_id to achieve consistent assignment (only necessary if things change in order)

    lst = []

    # group instance ids by host type
    instances = {}
    for instance_info in ec2_instances_info:
        
        host_type = instance_info["tags"]["host_type"]

        if host_type not in instances:
            instances[host_type] = []
        instances[host_type].append(instance_info["instance_id"])

    print(f"instances={instances}")

    exps_with_controller = set()

    for host_type, experiments in host_types.items():

        if host_type not in instances:
            print(f"ignore host type: {host_type}")
            continue

        for exp_name, info in experiments.items():
            
            # take n instances and assign to this experiment
            for i in range(info["n"]):
                instance_id = instances[host_type].pop(0)
                
                if exp_name in exps_with_controller:
                    exp_role = "no_controller"
                else:
                    exps_with_controller.add(exp_name)
                    exp_role = "controller"

                d = {"instance_id": instance_id, "exp_name": exp_name, "exp_role": exp_role, "host_type": host_type, "exp_host_type_idx": i}
                lst.append(d)

    
    print(lst)

    return lst


class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            'to_tag_assignment': to_tag_assignment,
        }