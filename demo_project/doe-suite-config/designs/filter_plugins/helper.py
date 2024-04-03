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


class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            'to_public_dns_name': to_public_dns_name,
            'to_private_dns_name': to_private_dns_name,
            'to_ipv4': to_ipv4,

        }