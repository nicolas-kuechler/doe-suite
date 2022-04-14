# Clouds

Doe supports multiple _clouds_.
A cloud refers to an environment in which servers are set up and configured.
So far, we support AWS (aws) and Euler (euler, ETH compute cluster).

## Supported clouds

| Cloud  | Description                 |
|--------|-----------------------------|
| aws    | Amazon Web Services         |
| euler  | Euler (ETH compute cluster) |

## Migration guide

After the transition to support for clouds, some things must be changed:

## [For devs] Supporting additional clouds

`main` represents all supported clouds except the ones that have a specific file.

### Setup roles
In `does_config/roles/**`, rename `main.yml` to `aws.yml`

## Adding new clouds
Add setup tasks for all cloud-related tasks: `suite-cloud-*` in the suite.

### Cloud interface
After the cloud setup scripts run, the cloud should provide servers as Ansible inventory.
It needs to provide some additional metadata on the servers and experiments,
so they can be properly allocated by the system.
Here we describe some task-specific variables that must be defined.

#### suite-cloud-inventory-setup
Set up the inventory file for ansible based on local parameters and then refresh inventory.
May consist of templating a template inventory file with the relevant parameters in the `group_vars` of the `does_config` dir.

"Coordinating" servers must be added to the host group `is_controller_yes`.

#### suite-cloud-ec2-create

| Variable        | Contents   |
|-----------------|-----|
| suite_hosts_lst | list of all instances with their id and other relevant infos (+ public and private dns names), ` [{"instance_id": X, "exp_name": X, "is_controller": X, "host_type": X, "exp_host_type_idx": X, "exp_host_type_n": X, "init_roles": X, "check_status": X, "public_dns_name": X, "private_dns_name": X}, ...]`    |
| setup_roles     |     |
|                 |     |

### Scheduler interface
#### suite-scheduler-enqueue
Enqueue all jobs to the remote scheduler

#### suite-scheduler-status
Get the status of jobs

#### suite-scheduler-remove
Remove a job with label from the queue when its finished.
`job_id_to_wait_for` must be defined.

