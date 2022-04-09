
from urllib.parse import non_hierarchical


def to_network(my_host, eni_assignment):
    """
    if my_host has an eni assignment -> use it.
    """
    if my_host['host_type'] in eni_assignment:
        eni_id = eni_assignment[my_host['host_type']][my_host['idx']]
        return {'interfaces': [eni_id]}
    else:
        return {'assign_public_ip': True}


def to_eni_assignment(ec2_eni_info, ec2_instance_info, host_types, host_type_specific_vars):
    """
    if host types have the variable `attach_eni: True` in their host specific vars,
    then we find an existing (not assigned) eni to attach.
    (enough eni need to exist in group_vars/all -> exp_base: eni: [])
    """

    #print(f"eni_info={ec2_eni_info}")
    #print(f"\n\nec2_instance_info={ec2_instance_info}")
    #print(f"host_types={host_types}")
    #print(f"host_type_specific_vars={host_type_specific_vars}")

    d_tags = {}
    for x in ec2_instance_info["instances"]:
        d_tags[x['instance_id']] = x['tags']

    assignment = {}

    # init the assignment
    for host_type, vars in host_type_specific_vars.items():
        if vars.get("attach_eni", False):
            count = 0
            for exp in host_types[host_type].keys():
                count += host_types[host_type][exp]["n"]
            assignment[host_type] = count * [None]

    available_eni_ids = []
    for eni in ec2_eni_info["network_interfaces"]:
        if "attachment" in eni:
            # assign existing eni to same host_type
            instance_id = eni["attachment"]["instance_id"]
            if instance_id in d_tags:
                host_type = d_tags[instance_id]["host_type"]
                idx = int(d_tags[instance_id]["idx"])
                if host_type in assignment:
                    assignment[host_type][idx] = eni["network_interface_id"]
        else: # -> eni is available
            available_eni_ids.append(eni["network_interface_id"])


    for host_type in assignment.keys():
        for i in range(len(assignment[host_type])):
            if assignment[host_type][i] is None:
                eni_id = available_eni_ids.pop()
                if eni_id is None:
                    raise ValueError(f"Not enough eni available -> create more via group_vars/all")
                assignment[host_type][i] = eni_id


    return assignment



def to_tag_assignment(ec2_instances_info, host_types):

    """
    Given the available ec2 instances and the requirements for the suite (in `host_types`),
    the function returns an assignment (i.e., which instance is used in which experiment).

    ec2_instance_info: a list of dictionaries retrieved from module: `community.aws.ec2_instance_inf`
    host_types: a dictionary with all host types of the suite and their experiments{<HOST_TYPE>: {<EXP_NAME>: X}}

    return: list of dicts [{"instance_id" X, "exp_name": X, ...}, ...] that decides which ec2 instances to use in which experiment.
    """

    #  sort ec2_instances_info by instance_id to achieve consistent assignment
    list(sorted(ec2_instances_info, key=lambda instance_info: (instance_info["tags"]["host_type"], instance_info["tags"]["idx"], instance_info["instance_id"])))

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


            if "init_roles" in host_types[host_type][exp_name]:
                init_roles = host_types[host_type][exp_name]["init_roles"]
            else: init_roles = "-"


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
                        "init_roles": init_roles,

                        "check_status": check_status}
                lst.append(d)


    return lst


class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            'to_tag_assignment': to_tag_assignment,
            'to_eni_assignment': to_eni_assignment,
            'to_network': to_network,
        }