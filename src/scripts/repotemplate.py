import os
import subprocess
import signal
import sys

from ast import literal_eval
from jinja2 import Environment, FileSystemLoader, select_autoescape, meta
import pyinputplus as pyip

DEFAULT_HOST_TYPE = "host_type"

vars_base_path = os.environ["DOES_PROJECT_FOLDER"] + "/does_config/group_vars"
src_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
templates_base_path = src_path + "/resources/repotemplate/group_vars"
groups = ["all", "server", "client", "ansible_controller"]
template_name = "main.yml.j2"
# The template path is assumed to be: f"{templates_base_path}/<<NAME>>", where
# <<NAME>> is 'all' for the group 'all' and the string 'DEFAULT_HOST_TYPE' for all other host types.
# The output path is assumed to be f"{vars_base_path}/{group}/template_name.rstrip('.j2')"

default_ubuntu_ami = "ami-02e5f497990930ec1"

# Try to find the latest ubuntu ami (the AWS CLI must be configured for this to work).
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
    print(f"WARNING: Failed to get latest ubuntu AMI, using {default_ubuntu_ami}")
    ubuntu_ami = default_ubuntu_ami

defaults = {
    "all": {
        #'prj_id': None,
        'git_remote_repository': 'git@github.com:nicolas-kuechler/doe-suite.git',
        'job_n_tries': 100,
        'job_check_wait_time': 5,
        #'key_name': None,
    },
    "server": {
        'instance_type': 't2.medium',
        'volume_size': 16,
        'ec2_image_id': ubuntu_ami,
        'snapshot_id': None
    },
    "client": {
        'instance_type': 't2.medium',
        'volume_size': 16,
        'ec2_image_id': ubuntu_ami,
        'snapshot_id': None
    },
    "ansible_controller": {
        'instance_type': 't2.small',
        'volume_size': 64,
        'ec2_image_id': ubuntu_ami,
        'snapshot_id': None,
        'ansible_exp_suite_git_repo': 'git@github.com:nicolas-kuechler/doe-suite.git'
    },
    # General default values
    DEFAULT_HOST_TYPE: {
        'instance_type': 't2.medium',
        'volume_size': 16,
        'ec2_image_id': ubuntu_ami,
        'snapshot_id': None
    }
}


def signal_handler(sig, frame):
    print("\nAborting config...")
    exit(0)

def input_str(d, key, msg):
    if key in d:
        # with default
        d[key] = pyip.inputStr(f'{msg} ({d[key]}): [Press enter] ', blank=True, applyFunc= lambda x: x if x else d[key])
    else:
        # without default
        d[key] = pyip.inputStr(f'{msg}: ')


def input_num(d, key, msg, min, max):
    if key in d:
        # with default
        d[key] = pyip.inputInt(f'{msg} ({d[key]}): [Press enter] ', min=min, max=max, blank=True, applyFunc= lambda x: x if x else d[key])
    else:
        # without default
        d[key] = pyip.inputInt(f'{msg}: ', min=min, max=max)


def prompt_user(d, variables, host):
    if host == "all":
        print("\nConfiguring General Project...")

        input_str(d, "prj_id", "> Unique Project ID")

        input_str(d, "git_remote_repository", "> Git remote repository -> cloned on client and server")

        input_num(d, "job_n_tries", "> Playbook number of tries to check for experiment finished", min=1, max=1000)

        input_num(d, "job_check_wait_time", "> Time to wait between checking in seconds", min=5, max=None)

        input_str(d, "key_name", "> AWS key name -> you must have the private key created via AWS")
    else:
        print(f"\nConfiguring \"{host}\" instance...")

        input_str(d, "instance_type", "> EC2 instance type")

        input_num(d, "volume_size", "> EC2 volume size in GB", min=8, max=512)

        input_str(d, "ec2_image_id", "> EC2 image AMI")

        # Find the SnapshotId for this instance
        if "snapshot_id" not in d or d["snapshot_id"] == None:
            try:
                snapshot_id = literal_eval(subprocess.check_output([
                    "aws",
                    "ec2",
                    "describe-images",
                    "--image-ids",
                    d["ec2_image_id"],
                    "--query",
                    "Images[0].BlockDeviceMappings[*].Ebs.SnapshotId"
                ]).decode())[0]

                d["snapshot_id"] = snapshot_id
            except:
                print(f"WARNING: could not fetch snapshot id for {d['ec2_image_id']}")
                pass

        input_str(d, "snapshot_id", "> Snapshot ID for this instance")

        if host == "ansible_controller":
            input_str(d, "ansible_exp_suite_git_repo", "> URL to AWS Ansible Experiment Suite git repository")

    remaining_variables = list(filter(lambda x: not (x in d), variables))
    if len(remaining_variables) > 0:
        print("\nConfiguring Others...")

        for var in remaining_variables:
            input_str(d, var, f"> {var}")

    return d

def get_env_and_template(template_path, template_name):
    env = Environment(
            loader = FileSystemLoader(template_path),
            autoescape=select_autoescape(),
            variable_start_string=r'<<',
            variable_end_string=r'>>'
    )

    template = env.get_template(template_name)

    return env, template

def write_template(template, output_path):
    # replace the variables
    content = template.render()

    print(f"Writing {output_path}...")
    with open(output_path, "w+") as file:
        file.write(f"{content}\n")

def ask_confirmation(question, yes_msg=None, no_msg=None, default_answer="y"):
    """
    Ask a question and require the user to answer yes/no.

    :return: True is the user answered yes.
    """

    is_ok = pyip.inputYesNo(
        f"{question} ({default_answer}): [Press enter] ",
        blank=True, applyFunc= lambda x: x if x else default_answer
    )
    if is_ok == "yes":
        if yes_msg:
            print(yes_msg)
        return True
    else:
        if no_msg:
            print(no_msg)
        return False

def parse_group_list(group_list):
    if group_list == "":
        return []
    return list(map(str.strip, group_list.split(",")))

def validate_group_list(group_list):
    if any(map(lambda t: " " in t, parse_group_list(group_list))):
        raise Exception("Host types cannot contain spaces.")

# The values are not reset to the defaults when someone does not accept the config
# because that can always be achieved with restarting the script. Instead, entries
# are preserved as the new default values.
d = defaults

# Catch CTRL+C, exit gracefully
signal.signal(signal.SIGINT, signal_handler)

if not os.path.isdir(templates_base_path):
    raise Exception("Invalid template path given. Change templates_base_path.")

while True:
    if not ask_confirmation(f"Create default host types ({', '.join(groups[1:])})?"):
        groups = pyip.inputCustom(
            validate_group_list,
            prompt="Input comma-separated host types to create (may be empty, 'all' is always created): ",
            blank=True,
            postValidateApplyFunc=parse_group_list
        )

        if "all" not in groups:
            groups = ["all"] + groups

    templates_to_write = dict()
    configured_groups = groups[:]

    for group in groups:
        template_path = f"{templates_base_path}/{group}"
        if not os.path.isdir(template_path):
            template_path = f"{templates_base_path}/{DEFAULT_HOST_TYPE}"

        output_path = f"{vars_base_path}/{group}/{template_name.rstrip('.j2')}"

        if os.path.exists(output_path):
            if not ask_confirmation(f"Group vars for '{group}' already exist, overwrite?", no_msg=f"Skipping '{output_path}'"):
                configured_groups.remove(group)
                continue

        env, template = get_env_and_template(template_path, template_name)

        # find all variables in the template file
        template_full_path = os.path.join(template_path, template_name)
        with open(template_full_path, "r") as file:
            ast = env.parse(file.read())

        variables = meta.find_undeclared_variables(ast)

        # check if all the variables with defaults are actually detected variables
        group_defaults = defaults.get(group, defaults[DEFAULT_HOST_TYPE])
        for k in group_defaults.keys():
            if k not in variables:
                raise ValueError(f"Variable {k} with default is missing in {template_full_path}")

        # prompt the user to select the configuration
        d[group] = prompt_user(group_defaults, variables, group)

        # set the variable config globally in env
        for k, v in d[group].items():
            env.globals[k] = v

        templates_to_write[output_path] = template
        print()

    print("\n" + "-"*60)
    for group in configured_groups:
        print(f"\n\"{group}\" Configuration: ")
        for k, v in d[group].items():
            print(f"- {k}={v}")

    if ask_confirmation("Confirm", yes_msg="finishing config.", no_msg="restart config.\n\n"):
        # Write changes to disk
        for output_path, template in templates_to_write.items():
            output_dir = os.path.dirname(output_path)
            if not os.path.isdir(output_dir):
                if os.path.exists(output_dir):
                    print(f"Error: Cannot create directory, '{output_dir}' is already a file!")
                    exit(1)
                os.mkdir(output_dir)

            write_template(template, output_path)

        break
