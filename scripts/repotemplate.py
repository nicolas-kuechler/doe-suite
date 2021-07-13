import os

from jinja2 import Environment, FileSystemLoader, select_autoescape, meta
import pyinputplus as pyip


template_path = "group_vars/all"
template_name = "main.yml.j2"

output_path = "group_vars/all"
output_name = "main.yml"


defaults = {
    #'prj_id': None,
    'git_remote_repository': 'git@github.com:pps-lab/aws-simple-ansible.git',
    'exp_n_tries': 100,
    'exp_check_wait_time': 5,
    #'key_name': None,
    
    'n_servers': 1,
    'n_servers_status_check': 1,
    'instance_type_server': 't2.medium',
    'volume_size_server': 16,
    
    'n_clients': 1,
    'n_clients_status_check': 1,
    'instance_type_client': 't2.medium',
    'volume_size_client': 16
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


def prompt_user(defaults, variables):   
    
    d = defaults

    while True:

        print("Configuring General Project...")

        input_str(d, "prj_id", "> Unique Project ID")

        input_str(d, "git_remote_repository", "> Git remote repository -> cloned on client and server")

        input_num(d, "exp_n_tries", "> Playbook number of tries to check for experiment finished", min=1, max=None)

        input_num(d, "exp_check_wait_time", "> Time to wait between checking in seconds", min=5, max=None)

        input_str(d, "key_name", "> AWS key name -> you must have the private key created via AWS")


        print("\nConfiguring Server instances...")

        input_num(d, "n_servers", "> Number of server EC2 instances", min=0, max=10)

        input_num(d, "n_servers_status_check", "> Number of servers to check to determine if experiment job finished", min=0, max=d["n_servers"])

        input_str(d, "instance_type_server", "> Server EC2 instance type")

        input_num(d, "volume_size_server", "> Server EC2 volume size in GB", min=8, max=512)


        print("\nConfiguring Client instances...")

        input_num(d, "n_clients", "> Number of client EC2 instances", min=0, max=10)

        input_num(d, "n_clients_status_check", "> Number of clients to check to determine if experiment job finished", min=0, max=d["n_clients"])

        input_str(d, "instance_type_client", "> Client EC2 instance type")

        input_num(d, "volume_size_client", "> Client EC2 volume size in GB", min=8, max=512)



        remaining_variables = list(filter(lambda x: not (x in d), variables))
        if len(remaining_variables) > 0:
            print("\nConfiguring Others...")

            for var in remaining_variables:
                input_str(d, var, f"> {var}")


        print("\n\n------------------------------")
        print("Configuration: ")
        for k, v in d.items():
            print(f"- {k}={v}")

        is_ok = pyip.inputYesNo("Confirm (y): [Press enter] ", blank=True, applyFunc= lambda x: x if x else "yes")
        print(is_ok)
        if is_ok == "yes":
            break
        else:
            print("\n\n")
            
    return d


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
for k in defaults.keys():
    if k not in variables:
        raise ValueError(f"Variable {k} with default is missing in {template_name}")

# prompt the user to select the configuration
d = prompt_user(defaults, variables)

# set the variable config globally in env
for k, v in d.items():
    env.globals[k] = v

# replace the variables
content = template.render()

print(f"Writing {os.path.join(output_path, output_name)}...")
with open(os.path.join(output_path, output_name), "w+") as file:
    file.write(content)

