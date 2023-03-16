Experiment Configuration
========================


.. warning::

    The documentation is not up to date.

.. todo::

    TODO    [nku] update documentation -> try to build the documentation by including the top comments of the ansible roles

The experiment configuration defines the experiments to run. For each
experiment, it specifies the host types to use, how they are setup, and
how the experiments are started.

General Syntax
--------------

There are two possibilities to define experiments: - *Experiment
design:* this is the general approach, where one specifies all factors
(for different experiment runs) manually. - *Experiment table:* this is
a convenient shorthand to define experiments that use the cross-product
of all specified factors. It provides the option to concisely specify
the experiment and can then be translated to an experiment design using
the `expdesign <../scripts/expdesign.py>`__ script.

Experiment Design
~~~~~~~~~~~~~~~~~

The general layout is as follows:

.. code:: yaml

   << experiment_1 >>:
     n_repetitions: << nr >>
     common_roles:
       - << ansible-role-name >>
     host_types:
       << host_type_1 >>:
         n: << nr >>
         check_status: << boolean (optional) >>
         init_roles: << ansible-role-name >>
     base_experiment:
       << global_variable_1 >>: << nr, str, or $FACTOR$ >>
       host_vars:
         << host_type_1 >>:
           << host_arg_1 >>: << nr, str, or $FACTOR$ >>
       $CMD$:
         << host_type_1 >>: << str >>
     factor_levels:
       - << global_variable_1 >>: << nr, str >>
         host_vars:
           << host_type_1 >>:
             << host_arg_1 >>: << nr, str >>

Terms marked with ``<< >>`` are placeholders that can be replaced by
user-chosen values and the rest are keywords. Placeholders with the
suffix ``_1`` signal that there could be arbitrarily more entries like
them.

Examples are in the `designs folder <../experiments/designs>`__.

Keywords
^^^^^^^^

A suite design is a dict (YAML object) of experiments. The keys of the
dict are the (unique) experiment names of the suite. In addition, there
are special keywords that start with a ``$`` and are used to configure
the suite.

+---------------------------+------------------+---+------------------+
| Keyword                   | Required         | T | Short            |
|                           |                  | y | Description      |
|                           |                  | p |                  |
|                           |                  | e |                  |
+===========================+==================+===+==================+
| ``<< experiment_name >>`` | yes              | d | Definition of an |
|                           |                  | i | `expe            |
|                           |                  | c | riment <#experim |
|                           |                  | t | ent-keywords>`__ |
|                           |                  |   | of the suite     |
|                           |                  |   | (suite can have  |
|                           |                  |   | multiple         |
|                           |                  |   | experiments).    |
+---------------------------+------------------+---+------------------+
| ``$ETL$``                 | no (default: {}) | d | Definition of    |
|                           |                  | i | ETL pipeline for |
|                           |                  | c | processing       |
|                           |                  | t | results (e.g,    |
|                           |                  |   | generate plot).  |
+---------------------------+------------------+---+------------------+
| ``$SUITE_VARS$``          | no (default: {}) | d | Definition of    |
|                           |                  | i | default          |
|                           |                  | c | variables that   |
|                           |                  | t | are available in |
|                           |                  |   | all experiments  |
|                           |                  |   | of the suite.    |
+---------------------------+------------------+---+------------------+

Experiment Keywords
'''''''''''''''''''

+-----------------+-----------------------+----+-----------------------+
| Keyword         | Required              | Ty | Short Description     |
|                 |                       | pe |                       |
+=================+=======================+====+=======================+
| ``              | yes                   | i  | Number of repetitions |
| n_repetitions`` |                       | nt | of each run           |
|                 |                       |    | (i.e. each level      |
|                 |                       |    | config)               |
+-----------------+-----------------------+----+-----------------------+
| `               | no (default: [])      | s  | One or more Ansible   |
| `common_roles`` |                       | tr | role(s) that are run  |
|                 |                       | or | for all hosts during  |
|                 |                       | li | the initial setup. A  |
|                 |                       | st | single role can be    |
|                 |                       |    | specified as string,  |
|                 |                       |    | multiple roles need   |
|                 |                       |    | to use list notation. |
+-----------------+-----------------------+----+-----------------------+
| ``host_types``  | yes                   | di | Dictionary of hosts   |
|                 |                       | ct | used for the given    |
|                 |                       |    | experiment. The keys  |
|                 |                       |    | are the name of the   |
|                 |                       |    | host type, the value  |
|                 |                       |    | is another dictionary |
|                 |                       |    | with configurations   |
|                 |                       |    | (see values).         |
+-----------------+-----------------------+----+-----------------------+
| ``ba            | yes                   | di | Dictionary of         |
| se_experiment`` |                       | ct | variables defined for |
|                 |                       |    | this experiment       |
+-----------------+-----------------------+----+-----------------------+
| ``              | yes if                | li | List of dictionaries  |
| factor_levels`` | ``base_experiment``   | st | for each run. Each    |
|                 | contains at least one |    | dictionary specifies  |
|                 | factor, no otherwise  |    | the values for        |
|                 |                       |    | variables marked with |
|                 |                       |    | ``$FACTOR$`` in       |
|                 |                       |    | ``base_experiment``.  |
+-----------------+-----------------------+----+-----------------------+

Host Type Keywords
''''''''''''''''''

+-----------------+----------------------+-----+----------------------+
| Keyword         | Required             | T   | Short Description    |
|                 |                      | ype |                      |
+=================+======================+=====+======================+
| ``n``           | yes                  | int | Number of EC2        |
|                 |                      |     | instances            |
+-----------------+----------------------+-----+----------------------+
| ``$CMD$``       | yes                  | d   | Dictionary of hosts  |
|                 |                      | ict | with their run       |
|                 |                      |     | starting commands.   |
+-----------------+----------------------+-----+----------------------+
| `               | no (default: True)   | b   | Boolean set to true  |
| `check_status`` |                      | ool | when the status of   |
|                 |                      |     | this host type       |
|                 |                      |     | should be checked    |
|                 |                      |     | when evaluating      |
|                 |                      |     | whether a job        |
|                 |                      |     | finished             |
+-----------------+----------------------+-----+----------------------+
| ``init_roles``  | no (default: [])     | str | One or more Ansible  |
|                 |                      | or  | role(s) that are run |
|                 |                      | l   | for hosts of this    |
|                 |                      | ist | type during the      |
|                 |                      |     | initial setup. A     |
|                 |                      |     | single role can be   |
|                 |                      |     | specified as string, |
|                 |                      |     | multiple roles need  |
|                 |                      |     | to use list          |
|                 |                      |     | notation.            |
+-----------------+----------------------+-----+----------------------+

Base Experiment Keywords
''''''''''''''''''''''''

``base_experiment`` contains variable definitions and the commands to
start the experiment run. By convention, global variables for all host
types are stored directly as key/value pairs.

+-----------------+----------+----------------+-----------------------+
| Keyword         | Required | Type           | Short Description     |
+=================+==========+================+=======================+
| ``$             | no       | str or list    | Load default          |
| INCLUDE_VARS$`` |          |                | variables from a file |
|                 |          |                | in                    |
|                 |          |                | ``doe-suite-config/d  |
|                 |          |                | esigns/design_vars``. |
+-----------------+----------+----------------+-----------------------+
| ``host_vars``   | no       | dict           | Defines variables for |
|                 |          |                | the different host    |
|                 |          |                | types here.           |
+-----------------+----------+----------------+-----------------------+

Note, it is only a convention to group variables by host type. In
practice, e.g., also a host of type “client” can use variables from
“server”. The ``$CMD$`` property can also be defined as a factor:
``$FACTOR$`` and then ``$CMD$`` needs to be defined in
``factor_levels``.

Factor Levels
'''''''''''''

``factor_levels`` is a list of dictionaries. Each dictionary must have
an entry for every variable that is marked with the value ``$FACTOR$``
in ``base_experiment`` (also ``$CMD$`` is possible).

The number of dictionaries defines the number of runs for the
experiment. Each dictionary should therefore contain a unique variable
assignment (otherwise, there are duplicate runs).

Defining Commands
~~~~~~~~~~~~~~~~~

The ``$CMD$`` property in ``base_experiment`` contains for each host
type the starting command of the software artifact (e.g., command to
start the benchmark software).

Within a command, there are two different types of variables available:
- ``{{ }}``: these are global variables from ``group_vars/all`` -
``[% %]``: these are variables that correspond to factors or other of
the current run. In most cases, they have the form ``[% my_run.* %]``.
If there is a factor ``a`` (i.e., ``base_experiment: a: $FACTOR$``),
then the variable ``[% my_run.a %]`` refers to the level of this factor
in the respective run.

There are two options on how to pass configurations to the artefact with
a command: - Pass factor levels as command line arguments (e.g., use the
factor ``a`` as an argument to echo: ``echo [% my_run.a %]``). - Pass
factor levels via the ``config.json`` file. For convenience, there is a
``config.json`` file in the working directory that contains the run
config.

Moreover, for multi-instance experiments there is a variable
``exp_host_lst`` that contains information on all involved hosts of the
experiment. The format of the list is as follows:

.. code:: yaml

   [{"host_type": x, "exp_host_type_idx": x, "exp_host_type_n": x, "is_controller": x, "public_dns_name": x, "private_ip_address": x}, ... ]

Unfortunately, at the moment it is not supported to use this variable
within the experiment design (e.g., within a command). TODO [nku] build
functionality to provide access to host list of experiment: should be
able to use ``[% exp_host_lst %]`` in ``$CMD$``