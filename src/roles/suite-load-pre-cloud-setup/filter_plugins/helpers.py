def suite_to_hosttypes(suite_design):

    """
    Extracts a host_types dict from a suite with default values set:

    host_types = {host_type_name1:{exp_name1: {'init_roles': X, 'n': X}, ... }, ...}
    """

    host_types = {}


    for exp_name, exp in suite_design.items():

        if exp_name == "$ETL$":
            continue

        for host_type_name, host_type_d in exp["host_types"].items():

            if host_type_name not in host_types:
                host_types[host_type_name] = {}

            host_types[host_type_name][exp_name] = host_type_d


    return host_types


def suite_to_commonroles(suite_design):

    """
    Extracts a common_roles dict from a suite with default values set:

    common_roles = {exp_name1: [role1, ...], exp_name2: [role1, ...]}
    """
    d = {}
    for exp_name, exp in suite_design.items():
        if exp_name == "$ETL$":
            continue

        d[exp_name] = exp["common_roles"]

    return d

class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            'suite2hosttypes': suite_to_hosttypes,
            'suite2commonroles': suite_to_commonroles,
        }