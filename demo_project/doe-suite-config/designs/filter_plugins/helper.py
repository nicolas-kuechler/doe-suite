# INFO: Should be in sync with: cookiecutter-doe-suite-config/{{cookiecutter.repo_name | default("doe-suite-config") }}/designs/filter_plugins/helper.py

import socket

from jinja2.runtime import Undefined


def to_ipv4(hostlist, host_type, host_type_idx=0, default=None):
    if isinstance(hostlist, Undefined):
        if default is not None:
            return default
        return hostlist # return undefined
    else:
        hosts = [host for host in hostlist if host['host_type'] == host_type]
        assert len(hosts) > host_type_idx, f"to_ipv4: host_type_idx out of range: {host_type_idx=}, {len(hosts)=}"
        return socket.gethostbyname(hosts[host_type_idx]['public_dns_name'])

def to_public_dns_name(hostlist, host_type, host_type_idx=0, default=None):
    if isinstance(hostlist, Undefined):
        if default is not None:
            return default
        return hostlist
    else:
        hosts = [host for host in hostlist if host['host_type'] == host_type]
        assert len(hosts) > host_type_idx, f"to_public_dns_name: host_type_idx out of range: {host_type_idx=}, {len(hosts)=}"
        return hosts[host_type_idx]['public_dns_name']


def to_private_dns_name(hostlist, host_type, host_type_idx=0, default=None):
    if isinstance(hostlist, Undefined):
        if default is not None:
            return default
        return hostlist
    else:
        hosts = [host for host in hostlist if host['host_type'] == host_type]
        assert len(hosts) > host_type_idx, f"to_private_dns_name: host_type_idx out of range: {host_type_idx=}, {len(hosts)=}"
        return hosts[host_type_idx]['private_dns_name']



def at_runtime(var, exp_host_lst, host_type=None, host_type_idx=0):

    if isinstance(exp_host_lst, Undefined):
        return f"<{var}@runtime>"
    elif host_type is not None:
        hosts = [host for host in exp_host_lst if host['host_type'] == host_type]
        assert len(hosts) > host_type_idx, f"at_runtime: host_type_idx out of range: {host_type_idx=}, {len(hosts)=}"
        return hosts[host_type_idx]['hostvars'][var]
    else:
        # need to guarantee that all hosts have the variable set to the same value
        vars = [host['hostvars'].get(var, Undefined(name=var)) for host in exp_host_lst]
        assert len(set(vars)) == 1, f"at_runtime: all hosts must have the same value for the variable {var=}, {set(vars)=}"
        return vars[0]


class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            'to_public_dns_name': to_public_dns_name,
            'to_private_dns_name': to_private_dns_name,
            'to_ipv4': to_ipv4,
            'at_runtime': at_runtime,

        }