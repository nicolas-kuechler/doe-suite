



def check_manual_inventory(host_types, available_inventory):


    """Checks if the requested host_types are available in the inventory

    The `available_inventory` is from a custom inventory file, the `host_types` is from the suite design and has the form:

    host_types: {<host_type_1>: {
                    <exp_name_1>: {'n': <int>, 'check_status': <bool>, ...},
                    <exp_name_2>: {'n': <int>, 'check_status': <bool>, ...}}
                <host_type_2>: {...}
                },


    available_inventory:{
                    "all": {
                        "children": {
                            <host_type_1>: {
                                "hosts": {
                                    <host_1>: {
                                        "ansible_host": <ip>,
                                        "ansible_user": <user>,
                                    },
                                    <host_2>: {...}
                                }
                            },
                                }
                            }
                        }


    """


    # TODO [nku] could also validate it with pydantic

    # TODO [nku] should validate that the host type ids have a unique id.

    avl = available_inventory['all']['children']

    errors = []


    host_ids = set()

    for host_type, exps in host_types.items():

        n_requested = 0
        for _exp, c in exps.items():
            n_requested += c['n']

        assert host_type in avl, f"host_type: {host_type} missing in available_inventory  (available_inventory: {avl})"

        if host_type not in avl:
            n_available = 0
        else:
            n_available = len(avl[host_type]["hosts"].keys())

            # enforce unique host ids
            for host_id in avl[host_type]["hosts"].keys():
                assert host_id not in host_ids, f"host_id: {host_id} is not unique in available_inventory"
                host_ids.add(host_id)


        if n_available < n_requested:
            errors.append(f"  -> not enough hosts of type {host_type} available (available: {n_available}, requested: {n_requested})")


    if len(errors) > 0:
        raise ValueError(f"The manually provided inventory does not have the requested host_types in the design: \n{errors}")

    return True

class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {

            'check_manual_inventory': check_manual_inventory,
        }