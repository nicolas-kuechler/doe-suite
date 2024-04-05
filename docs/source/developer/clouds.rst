======
Clouds
======

The DoE-Suite supports multiple _clouds_.
A cloud refers to an environment in which servers are set up and configured.
So far, we support AWS (aws), Euler (euler, ETH compute cluster), and clouds described by an Ansible inventory file.

Set the environment variable ``DOES_CLOUD`` to control the default cloud.
On every invocation of the DoE-Suite, you can set the cloud environment,
e.g., ``make run suite=XYZ id=new cloud=euler``.
For clouds described by an Ansible inventory file, the name of the inventory is the cloud name.
Note, that if you started a suite on a cloud, than this suite run cannot switch to another cloud.


Supported clouds
----------------

+-------+-------------------------------+
| Cloud | Description                   |
+-------+-------------------------------+
| aws   | Amazon Web Services (EC2)     |
+-------+-------------------------------+
| euler | Euler (ETHZ compute cluster)  |
+-------+-------------------------------+
| <INV> | Ansible Inventory named <INV> |
+-------+-------------------------------+


Cloud multiplexing
------------------

Doe-suite can load cloud-specific functionality depending on the active cloud.

For some roles, the DoE-Suite will look for the cloud specific  ``{cloud}.yml`` file.
If no such file exists, ``main.yml`` will be used as a fallback.

This cloud multiplexing is enabled for the following roles:
- ``setup-suite``
- Any ``suite-cloud-*`` role
- Any host-specific role, those in ``doe-suite-config/roles/setup-*``.

Schedulers
----------

We now have the concept of schedulers that handles the scheduling of jobs.
The default scheduler is ``tsp`` which will be set-up on the OS by the DoE-Suite.
In some cases, the cloud has its own scheduler, for example ``bsub`` or ``slurm`` in Euler.
The variable ``_job_scheduler`` in ``doe-suite/src/group_vars/all`` is used to control which scheduler is used.

For ansible inventories, you can set the scheduler in the inventory file as a host variable: `job_scheduler: slurm`

We support the same type of multiplexing as for clouds.
The Doe-Suite looks for the specific scheduler implementation in the following roles:
- ``suite-scheduler-enqueue`` Enqueue the pending jobs
- ``suite-scheduler-remove`` Remove a finished job (unused in ``slurm``, ``bjobs``, but used for ``tsp``)
- ``suite-scheduler-status`` Get status of a specific job



Adding new clouds
=================

``main`` represents all supported clouds except the ones that have a specific file.

In ``doe-suite-config/roles/**``, rename ``main.yml`` to ``aws.yml``

Add setup tasks for all cloud-related tasks: ``suite-cloud-*`` in the suite.
