import os

from jinja2 import Environment, FileSystemLoader, select_autoescape, meta
import pyinputplus as pyip

vars_base_path = "group_vars"
groups = ["all", "server", "client"]
template_name = "main.yml.j2"
# The template path is assumed to be: f"{vars_base_path}/{group}"
# The output path is assumed to be f"{template_path}/template_name.rstrip('.j2')"


defaults = {
    "all": {
        #'prj_id': None,
        'git_remote_repository': 'git@github.com:pps-lab/aws-simple-ansible.git',
        'exp_n_tries': 100,
        'exp_check_wait_time': 5,
        #'key_name': None,
    },
    "server": {
        'n_hosts': 1,
        'n_hosts_status_check': 1,
        'instance_type': 't2.medium',
        'volume_size': 16,
    },
    "client": {
        'n_hosts': 1,
        'n_hosts_status_check': 1,
        'instance_type': 't2.medium',
        'volume_size': 16
    }
}


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

        input_num(d, "exp_n_tries", "> Playbook number of tries to check for experiment finished", min=1, max=1000)

        input_num(d, "exp_check_wait_time", "> Time to wait between checking in seconds", min=5, max=None)

        input_str(d, "key_name", "> AWS key name -> you must have the private key created via AWS")
    else:
        print(f"\nConfiguring \"{host}\" instance...")

        input_num(d, "n_hosts", "> Number of EC2 instances", min=0, max=10)

        input_num(d, "n_hosts_status_check", "> Number of instances to check to determine if experiment job finished", min=0, max=d["n_hosts"])

        input_str(d, "instance_type", "> EC2 instance type")

        input_num(d, "volume_size", "> EC2 volume size in GB", min=8, max=512)


    remaining_variables = list(filter(lambda x: not (x in d), variables))
    if len(remaining_variables) > 0:
        print("\nConfiguring Others...")

        for var in remaining_variables:
            input_str(d, var, f"> {var}")

    return d

# The values are not reset to the defaults when someone does not accept the config
# because that can always be achieved with restarting the script. Instead, entries
# are preserved as the new default values.
d = defaults

while True:
    for group in groups:
        template_path = f"{vars_base_path}/{group}"
        output_path = template_path
        output_name = template_name.rstrip(".j2")

        env = Environment(
                loader = FileSystemLoader(template_path),
                autoescape=select_autoescape(),
                variable_start_string=r'<<',
                variable_end_string=r'>>'
        )

        # print(env.list_templates())
        template = env.get_template(template_name)

        # find all variables in the template file
        with open(os.path.join(template_path, template_name), "r") as file:
            ast = env.parse(file.read())

        variables = meta.find_undeclared_variables(ast)

        # check if all the variables with defaults are actually detected variables
        for k in defaults[group].keys():
            if k not in variables:
                raise ValueError(f"Variable {k} with default is missing in {template_name}")

        # prompt the user to select the configuration
        d[group] = prompt_user(defaults[group], variables, group)

        # set the variable config globally in env
        for k, v in d[group].items():
            env.globals[k] = v

        # replace the variables
        content = template.render()

        print(f"Writing {os.path.join(output_path, output_name)}...")
        with open(os.path.join(output_path, output_name), "w+") as file:
            file.write(f"{content}\n")

    print("\n" + "-"*60)
    for group in groups:
        print(f"\n\"{group}\" Configuration: ")
        for k, v in d[group].items():
            print(f"- {k}={v}")

    is_ok = pyip.inputYesNo("Confirm (y): [Press enter] ", blank=True, applyFunc= lambda x: x if x else "yes")
    print(is_ok)
    if is_ok == "yes":
        break
    else:
        print("\n\n")
