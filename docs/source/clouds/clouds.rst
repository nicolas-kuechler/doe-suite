======
Clouds
======

The DoE-Suite supports multiple _clouds_.
A cloud refers to an environment in which servers are set up and configured.
So far, we support AWS (aws) and Euler (euler, ETH compute cluster).

Set the environment variable `DOES_CLOUD` to control the default cloud.
On every invocation of the DoE-Suite, you can set the cloud environment,
e.g., `make run suite=XYZ id=new cloud=euler`.
Note, that if you started a suite on a cloud, than this suite run cannot switch to another cloud.


Supported clouds
================

| Cloud  | Description                 |
|--------|-----------------------------|
| aws    | Amazon Web Services         |
| euler  | Euler (ETH compute cluster) |

Cloud multiplexing
==================

Doe-suite can load cloud-specific functionality depending on the active cloud.

For some roles, the DoE-Suite will look for the cloud specific  `{cloud}.yml` file.
If no such file exists, `main.yml` will be used as a fallback.

This cloud multiplexing is enabled for the following roles:
- `setup-suite`
- Any `suite-cloud-*` role
- Any host-specific role, those in `doe-suite-config/roles/setup-*`.

Schedulers
==========

We now have the concept of schedulers that handles the scheduling of jobs.
The default scheduler is `tsp` which will be set-up on the OS by the DoE-Suite.
In some cases, the cloud has its own scheduler, for example `bsub` or `slurm` in Euler.
The variable `job_scheduler` in `doe-suite/src/group_vars/all` is used to control which scheduler is used.

We support the same type of multiplexing as for clouds.
The Doe-Suite looks for the specific scheduler implementation in the following roles:
- `suite-scheduler-enqueue` Enqueue the pending jobs
- `suite-scheduler-remove` Remove a finished job (unused in `slurm`, `bjobs`, but used for `tsp`)
- `suite-scheduler-status` Get status of a specific job


====================================================
[For devs] Supporting additional clouds [incomplete]
====================================================

`main` represents all supported clouds except the ones that have a specific file.

Setup roles
-----------
In `doe-suite-config/roles/**`, rename `main.yml` to `aws.yml`

Adding new clouds
=================
Add setup tasks for all cloud-related tasks: `suite-cloud-*` in the suite.

Cloud interface
===============
After the cloud setup scripts run, the cloud should provide servers as Ansible inventory.
It needs to provide some additional metadata on the servers and experiments,
so they can be properly allocated by the system.
Here we describe some task-specific variables that must be defined.

suite-cloud-inventory-setup
---------------------------
Set up the inventory file for ansible based on local parameters and then refresh inventory.
May consist of templating a template inventory file with the relevant parameters in the `group_vars` of the `doe-suite-config` dir.

"Coordinating" servers must be added to the host group `is_controller_yes`.

suite-cloud-ec2-create
----------------------

| Variable        | Contents   |
|-----------------|-----|
| suite_hosts_lst | list of all instances with their id and other relevant infos (+ public and private dns names), ` [{"instance_id": X, "exp_name": X, "is_controller": X, "host_type": X, "exp_host_type_idx": X, "exp_host_type_n": X, "init_roles": X, "check_status": X, "public_dns_name": X, "private_dns_name": X}, ...]`    |
| setup_roles     |     |
|                 |     |

`suite_hosts_lst` should contain a variable called `ansible_host_id` that can be used to reference the ansible host in `delegate_to`.
For AWS this is the public_dns_name, for euler this is the instance name `euler_XX` where `XX` is the experiment id.

### Scheduler interface
#### suite-scheduler-enqueue
Enqueue all jobs to the remote scheduler

#### suite-scheduler-status
Get the status of jobs

#### suite-scheduler-remove
Remove a job with label from the queue when its finished.
`job_id_to_wait_for` must be defined.
