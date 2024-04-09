import subprocess
import os
import warnings
from typing import Callable
from ast import literal_eval

DEFAULT_UBUNTU_AMI = "ami-08481eff064f39a84"
DEFAULT_AMI_SNAPSHOT_ID = "snap-0b8d7894c93b6df7a"

def get_latest_ami(default_ubuntu_ami=DEFAULT_UBUNTU_AMI):
    """use the aws cli to determine the latest ami of ec2 ubuntu machines

    Args:
        default_ubuntu_ami (str, optional): default ami if no other was found. Defaults to "ami-08481eff064f39a84".
    """
    try:
        proc_aws = subprocess.Popen([
            "aws",
            "ec2",
            "describe-images",
            "--filters",
            "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*",
            "--query",
            "Images[*].[ImageId,CreationDate]",
            "--output",
            "text"
        ], stdout=subprocess.PIPE)

        proc_sort = subprocess.Popen([
            "sort",
            "-k2",
            "-r"
        ], stdin=proc_aws.stdout, stdout=subprocess.PIPE)

        proc_aws.stdout.close()

        proc_head = subprocess.Popen([
            "head",
            "-n1"
        ], stdin=proc_sort.stdout, stdout=subprocess.PIPE)

        proc_sort.stdout.close()

        proc_awk = subprocess.Popen([
            "awk",
            "{print $1}"
        ], stdin=proc_head.stdout, stdout=subprocess.PIPE)

        ubuntu_ami = proc_awk.communicate()[0].decode().rstrip()
    except:
        warnings.warn(f"Failed to get latest ubuntu AMI (is aws cli setup?), using {default_ubuntu_ami}")
        ubuntu_ami = default_ubuntu_ami

    return ubuntu_ami


def get_volume_snapshot(ec2_image_id):
    """Use the aws cli to determine tha volume snapshot id for the ec2_image_id
    """

    if ec2_image_id == DEFAULT_UBUNTU_AMI:
        return DEFAULT_AMI_SNAPSHOT_ID

    # for other image id, need to find matching snapshot id
    try:
        snapshot_id = literal_eval(subprocess.check_output([
            "aws",
            "ec2",
            "describe-images",
            "--image-ids",
            ec2_image_id,
            "--query",
            "Images[0].BlockDeviceMappings[*].Ebs.SnapshotId"
        ]).decode())[0]

    except:
        warnings.warn(f"Could not fetch snapshot id for {ec2_image_id} (is aws cli setup?)")
        snapshot_id = input("> Snapshot ID for this instance:")

    return snapshot_id

def post_hook_replace(filepath, pattern, replacement):
    is_updated = False
    value = None
    with open(filepath, 'r') as read_file:
        lines = read_file.readlines()
        with open(filepath, 'w') as write_file:
            for line in lines:
                if pattern in line:
                    if isinstance(replacement, str) and not is_updated:
                        value  = replacement
                    elif isinstance(replacement, Callable) and not is_updated:
                        value = replacement()
                    else:
                        raise ValueError("not supported replacement type")
                    write_file.write(line.replace(pattern, value))
                    is_updated = True
                else:
                    write_file.write(line)
    return is_updated, value

# replace ami and volume snapshot with latest info
is_updated, value = post_hook_replace(filepath="group_vars/{{ cookiecutter.host_name }}/main.yml", pattern="<LATEST-AMI>", replacement=get_latest_ami)

if is_updated:
    snapshot_id = get_volume_snapshot(ec2_image_id=value)
else:
    snapshot_id = get_volume_snapshot(ec2_image_id="{{ cookiecutter.host_ec2_ami }}")
post_hook_replace(filepath="group_vars/{{ cookiecutter.host_name }}/main.yml", pattern="<LATEST-VOLUME-SNAPSHOT>", replacement=snapshot_id)

# set the connection between the doe-suite and the does_config in poetry
doespy_relative_to_does_config = os.path.relpath(os.path.join(os.environ.get("PWD"), "doespy"), os.getcwd())
post_hook_replace(filepath="pyproject.toml", pattern="<AUTO-PATH>", replacement=doespy_relative_to_does_config)

# in custom cloud via inventory: by default read user from env variables
post_hook_replace(filepath="inventory/{{ cookiecutter.custom_cloud }}.yml", pattern="<ENV:DOES_CUSTOM_CLOUD_USER>", replacement="{% raw %}{{ lookup('env', 'DOES_CUSTOM_CLOUD_USER', default=undef()) }}{% endraw %}")
