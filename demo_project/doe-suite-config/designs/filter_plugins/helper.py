import socket


def get_ip_for_hosttype(hostlist, hostlist_defined, host_type):
    # if hostlist is defined 
    # return the IPv4 for the host name
    if hostlist_defined:
        host = [host for host in hostlist if host['host_type'] == host_type]
        if len(host) == 1:
            return socket.gethostbyname(host[0]['public_dns_name'])
    # if hostlistnot defined or hostname not unique return default value
    print("get_ip_for_hostname: hostlist not defined or host_type not unique")
    return "0.0.0.0"

class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            'get_ip_for_hosttype': get_ip_for_hosttype
        } 