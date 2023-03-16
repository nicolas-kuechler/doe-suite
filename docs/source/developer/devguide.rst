Developer Ansible Guide
=======================

.. warning::

    The documentation is not up to date.


.. todo::

    TODO [nku] update documentation for developers -> can delete a lot and
    refer to the documentation within the role.

    TODO [nku] mention the logic of the ec2 dynamic inventory with the
    prf_id and suite filter => can use all, exp_name, check_status_yes,
    check_status_no, is_controller_yes, is_controller_no

    TODO [nku] remove mention of host_type ``all``

This document contains some useful information on the internals of this
Ansible project. E.g., how to update/extend certain parts.

Adding A Variable to the Experiment State
-----------------------------------------

To add a variable to the experiment state, do: 1. Add it to the
`experiment-state
template <../roles/experiment-state/templates/state.yml.j2>`__. 2. Add
it to ``exp_facts`` in the role called “Set experiment variables (facts)
based on loaded state” in the `experiment-state
tasks <../roles/experiment-state/tasks/main.yml>`__. 3. To more
generally integrate it to the project, add it to the `example
designs <../experiments/designs>`__ and the
`expdesign <../scripts/expdesign.py>`__ script (the latter to translate
experiment table specifications).

Important Data Structures
-------------------------

-  ``exp_facts``: This data structure is a dictionary with the
   experiment name as key and information about the status of the
   experiment as values.

   Example:

   .. code:: yaml

      exp_facts: {
        'experiment_1': {
          'exp_id': '5',
          'exp_runs_ext': [...],
          'exp_job_ids': ['5_0_0', ...],
          'exp_job_ids_unfinished': ['5_0_0', ...],
          'exp_job_ids_pending': ['5_0_0', ...],
          'exp_job_ids_running': [],
          'n_repetitions': '2',
          'common_roles': ['setup-common']
        },
        'experiment_2': {...}
      }

   Naming:

   -  ``exp_facts[exp_name]`` -> ``exp_fact``

-  ``host_types``: This data structure is a dictionary with the host
   type as a key. For each host type, it stores a dictionary with the
   experiment name as key and the host configuration (for this host type
   and experiment) as value. ``all`` is a special entry that collects
   the total number of instances for each ``host_type`` summed over all
   experiments (attention: its second key is the host type and not the
   experiment name!). The ``...`` below are just an ellipsis to make the
   example more concise and do not represent actual values.

   Example:

   .. code:: yaml

      host_types: {
        'client': {
          'experiment_1': {
            'init_roles': 'setup-client',
            'n': 1,
            'check_status': false
          },
          'experiment_2': {
            'init_roles': 'setup-client',
            'n': 1,
            'check_status': false
          }
        },
        'server': {
          'experiment_1': {...},
          'experiment_2': {...}
        }
        'all': {
          'client': {
            'n': 2
          }
          'server': {
            'n': ...
          }
        }
      }

   Naming:

   -  ``host_types[group]`` -> ``host_type``
   -  ``host_types[group][exp_name]`` -> ``host_facts``

-  ``host_type_names``: A list of all host types, without the special
   key ``all`` (i.e., not equal to ``host_types.keys()``). This is
   convenient to loop through host types.

-  ``exp_hosts``: variable set on “controller” hosts which contains a
   list of hosts involved in the current experiment.

-  ``host_group_name`` and ``host_group_name_long``:

   -  The first is the “short” group name used in the experiment suite
      config file, e.g. ``server``.
   -  The second is the group name used in the ansible inventory,
      defined by the EC2 plugin. It’s of the form
      ``tag_Name_<prj_id>_<host_group_name>_SEP_<exp_name>``.

      -  ``_SEP_`` is a separator defined in
         `group_vars/all <group_vars/all/main.yml.j2>`__ in the variable
         ``separator``. This is used to split ``host_group_name`` and
         ``exp_name`` when we recover those two variables from the group
         name.

-  ``suite_all``: Group of EC2 hosts belonging to this project ID.

Roles
-----

An (incomplete) list of roles and their purpose:

-  ``experiment-aws``: General role to handle creating AWS EC2
   instances.

-  ``experiment-aws-ec2-create``: Create EC2 instances for a specific
   host type and experiment.

-  ``experiment-aws-ec2-manage``: This is an optimization.
   ``experiment-aws`` first launches all instances using
   ``experiment-aws-ec2`` and only then waits for SSH to come up. Thus,
   instances can boot up concurrently and the next one is not only
   started after the current one is completely initialized.

-  ``experiment-vpc*``: Roles to create or remove a VPC (Virtual Private
   Cloud) for this project. We use a single VPC for the entire project.

-  ``experiment-clear``: Role to terminate all running EC2 instances
   from the current project. It prints the instance IDs to remove and
   gives the operator 10s to double check those IDs. By pressing
   ``CTRL+C``, the counter can be stopped. Pressing ``A`` next aborts
   and does not delete those instances. Pressing ``C`` instead continues
   the play.

-  ``experiment-job*``: Roles to manage the initial setup, start,
   scheduling, and status checking of jobs. There is a job for every run
   and repetition.

-  ``experiment-load``: This role initializes the jobs by loading them
   from the experiment config.

-  ``experiment-parse-config``: Parse the experiment suite, check
   assertions, and set default values. The ``dict_default`` filter is in
   this folder.

-  ``experiment-set-vars``: This role sets variables for a host. This is
   somewhat a hack and derives the experiment name and host group from
   the inventory group name. This workaround was necessary, since AFAIK
   the EC2 plugin doesn’t allow us to set host variables when launching
   new EC2 instances.

-  ``experiment-state``: This role handels the storing and loading of
   the experiment state. There is one JSON file for every experiment in
   the current suite.

-  ``setup-*``: Example roles that show how (individual or all) hosts
   can be set up.

Custom JINJA2 Filters
---------------------

-  ``dict_default``: Set a default value for a dictionary at the
   specified query.

   The query supports the wildcard character ’*’ and expects dot
   notation (i.e., d.plants and not d[‘plants’]). The wildcard tolerates
   lists.

   Example usage:

   Data:

   .. code-block:: json
    :caption: data

      {
          "animals": {
              "cats": 10,
              "dogs": 1
          }
          "plants": {
              "bushes": 2,
              "pot plants": 3
          }
      }

   Examples:

   -  Set a default for the plants “cacti”:
      ``{{ data | dict_default("plants", "cacti", 0) }}``

      Results in the new dictionary:

      .. code-block:: json
        :caption: data

            {
                "animals": {
                    "cats": 10,
                    "dogs": 1
                }
                "plants": {
                    "bushes": 2,
                    "pot plants": 3,
                    "cacti": 0
                }
            }

   -  Set a default category “other” for all entries if its not present:
      ``{{ data | dict_default("*", "other", 0) }}``

      Results in the new dictionary:

      .. code-block:: json
        :caption: data

            {
                "animals": {
                    "cats": 10,
                    "dogs": 1,
                    "other": 0
                }
                "plants": {
                    "bushes": 2,
                    "pot plants": 3,
                    "other": 0
                }
            }

   Remarks:

   -  Note that this filter can only add key/value pairs to an existing
      dictionaries:

      -  *WRONG*:
         ``{{ data | dict_default("plants.house", "cacti", 0) }}``
         because ``data["plants"]`` does not contain a dictionary for
         key ``house``.
      -  *CAREFUL*:
         ``{{ data | dict_default("plants", "house.cacti", 0) }}`` adds
         the entry ``house.cacti: 0``. It does **not** add a dictionary
         under key ``house`` with the entry ``cacti: 0``

Job scheduling
--------------

There is a group of hosts for every experiment. Those are created
dynamically by adding the tag ``tag:Exp`` with the experiment name as
value to every EC2 instance.

The first host in the group is the “controller”, which is used to
monitor the job status of the experiment and to advance to the next job
when the current one is done. At every job-switch, the controller pulls
all results and stores them on the localhost. It also updates the state
YAML files and distributes the updated ``exp_facts`` variable to all
hosts involved in this experiment (``exp_hosts`` and ``localhost``).

Inventory Host Groups
---------------------

**Important:** do not use ``all``. The EC2 plugin adds other
EC2 instances to the inventory even if they do not belong to the current
project. When we use ``all``, Ansible tries to connect to them, which
can cause SSH connection errors (if no public key for those hosts is
defined) or even **unintended configration overwriting** of other
instances!

Use ``suite_all`` instead to specify a play for all EC2 instances
belonging to the current project.