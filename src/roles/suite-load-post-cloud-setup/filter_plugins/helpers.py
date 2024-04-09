
def to_exp_specific_vars(suite_hosts_lst, experiment_names, hostvars):
    # print(f"to_exp_specific_vars:     {experiment_names=}    {type(hostvars)=}")

    exp_specific_vars = {e: {"exp_host_lst": []} for e in experiment_names if e != "$ETL$"}

    for x in suite_hosts_lst:

        # TODO [nku] could be switched to Pydantic model which can then be documented in the docs

        d = {"host_type": x["host_type"],
             "host_type_idx": x["exp_host_type_idx"],
             "host_type_n": x["exp_host_type_n"],
             "public_dns_name": x["public_dns_name"],
             "private_dns_name": x["private_dns_name"],
             "hostvars": hostvars[x["ansible_host_id"]]
            }

        exp_specific_vars[x["exp_name"]]["exp_host_lst"].append(d)

    return exp_specific_vars


class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            'to_exp_specific_vars': to_exp_specific_vars
        }