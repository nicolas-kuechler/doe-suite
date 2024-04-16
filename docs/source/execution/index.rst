===================
Running Experiments
===================


After defining your experiment suite, e.g., ``example01-minimal``, you can execute it using the ``make run`` command:

.. code::

    make run suite=example01-minimal id=new cloud=aws


The role of the doe-suite varies depending on whether you are conducting **single-instance** or **multi-instance** experiments.
In **single-instance** experiments, the doe-suite schedules all jobs directly on the remote instance using `task spooler <https://manpages.ubuntu.com/manpages/focal/man1/tsp.1.html>`_.
Once a job completes, `task spooler` automatically starts the next job, even if the doe-suite is not running.
To retrieve the results later, you can run the doe-suite with the following command: ``make run suite=example01-minimal id=<THE-SUITE-ID> cloud=aws``.
In **multi-instance**  experiments (e.g., client-server), the doe-suite is essential for orchestrating each job.
Consequently, the doe-suite must remain running; otherwise, no new experiment jobs will start until the doe-suite is running again.
While running, the doe-suite periodically checks the status of the experiments and downloads finished results.


A suite defines a collection of experiments that can be executed in different cloud environments, i.e., backends.
Currently, the following **clouds** are supported:

1. **AWS**: In this cloud environment, the `host_types` specified in the suite are mapped to AWS EC2 instance types.
The doe-suite first creates the instances (including network setup), runs the experiments on them, and then terminates the instances.

2. **Euler (or any SLURM cluster)**: This refers to a batch compute cluster managed by the `SLURM workload manager <https://slurm.schedmd.com/documentation.html>`_.
In this cloud, the doe-suite automates the submission of experiments as jobs to `SLURM` and automatically retrieves the results, removing the necessity for manual job submission and result retrieval.
In this cloud, **only single-instance** experiments are supported, i.e., no support for client-server experiments.

3. **Ansible Inventory (Manual Hostsfile)**: This option is suitable if you have a predefined set of machines where you wish to run the experiments.
However, it's important to note that when using this mode, the doe-suite assumes that you can SSH into the machines and that they are currently exclusively available for use.
This means the doe-suite will **not check** whether the machines are **already in use** or **running other experiments**.
The inventory is a regular `Ansible inventory file <https://docs.ansible.com/ansible/latest/inventory_guide/intro_inventory.html>`_ in YAML format, where you list the hosts.
See `demo_project/doe-suite-config/inventory/inv-template.yml` for an example.


.. toctree::
    :caption: Contents:
    :maxdepth: 1

    hosts
    jobs
    results
