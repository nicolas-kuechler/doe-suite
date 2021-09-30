# Experiment Configuration

TODO [nku] update documentation

The experiment configuration defines the experiments to run. For each experiment, it specifies the host types to use, how they are setup, and how the experiments are started.

## General Syntax

There are two possibilities to define experiments:
- _Experiment design:_ this is the general approach, where one specifies all factors (for different experiment runs) manually.
- _Experiment table:_ this is a convenient shorthand to define experiments that use the cross-product of all specified factors. It provides the option to concisely specify the experiment and can then be translated to an experiment design using the [expdesign](../scripts/expdesign.py) script.

### Experiment Design

The general layout is as follows:

```YAML
<< experiment_1 >>:
  n_repetitions: << nr >>
  common_roles:
    - << ansible-role-name >>
  host_types:
    << host_type_1 >>:
      n: << nr >>
      check_status: << boolean (optional) >>
      init_role: << ansible-role-name >>
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
```

Terms marked with `<< >>` are placeholders that can be replaced by user-chosen values and the rest are keywords. Placeholders with the suffix `_1` signal that there could be arbitrarily more entries like them.

Examples are in the [designs folder](../experiments/designs).

#### Keywords

| Keyword       | Required | Type | Short Description |
| ------------- | ----------------- | ---- | ----------------- |
| `experiments`   | yes               | dict | Dictionary of experiments that belong to an experiment _suite_. The keys are the (unique) experiment names and the values the experiment configurations. |

##### Experiment Keywords

| Keyword       | Required | Type | Short Description |
| ------------- | ----------------- | ---- | ----------------- |
| `n_repetitions`   | yes           | int  | Number of repetitions of each run (i.e. each level config) |
| `common_roles`    | no (default: [])  | str or list | One or more Ansible role(s) that are run for all hosts during the initial setup. A single role can be specified as string, multiple roles need to use list notation. |
| `host_types`      | yes           | dict | Dictionary of hosts used for the given experiment. The keys are the name of the host type, the value is another dictionary with configurations (see values). |
| `base_experiment` | yes           | dict | Dictionary of variables defined for this experiment |
| `factor_levels`   | yes if `base_experiment` contains at least one factor, no otherwise | list | List of dictionaries for each run. Each dictionary specifies the values for variables marked with `$FACTOR$` in `base_experiment`. |


##### Host Type Keywords

| Keyword       | Required | Type  | Short Description |
| ------------- | ----------------- | ----- | ----------------- |
| `n`           | yes               | int   | Number of EC2 instances |
| `check_status` | no (default: True) | bool | Boolean set to true when the status of this host type should be checked when evaluating whether a job finished |
| `init_role`   | no (default: [])  | str or list | One or more Ansible role(s) that are run for hosts of this type during the initial setup. A single role can be specified as string, multiple roles need to use list notation. |

##### Base Experiment Keywords

`base_experiment` contains variable definitions and the commands to start the experiment run. By convention, global variables for all host types are stored directly as key/value pairs.

| Keyword       | Required | Type  | Short Description |
| ------------- | ----------------- | ----- | ----------------- |
| `host_vars`   | no                | dict  | Defines variables for the different host types here. |
| `$CMD$`       | yes               | dict  | Dictionary of hosts with their run starting commands. |

Note, it is only a convention to group variables by host type. In practice, e.g., also a host of type "client" can use variables from "server".
The `$CMD$` property can also be defined as a factor: `$FACTOR$` and then `$CMD$` needs to be defined in `factor_levels`.

##### Factor Levels
`factor_levels` is a list of dictionaries. Each dictionary must have an entry for every variable that is marked with the value `$FACTOR$` in `base_experiment` (also `$CMD$` is possible).

The number of dictionaries defines the number of runs for the experiment. Each dictionary should therefore contain a unique variable assignment (otherwise, there are duplicate runs).


### Defining Commands

The `$CMD$` property in `base_experiment` contains for each host type the starting command of the software artifact (e.g., command to start the benchmark software).

Within a command, there are two different types of variables available:
- `{{ }}`: these are global variables defined within the experiment suite
- `[% %]`: these are variables that correspond to factors of the current run. In most cases, they have the form `[% my_run.* %]`. If there is a factor `a` (i.e., `base_experiment: a: $FACTOR$`), then the variable `[% my_run.a %]` refers to the level of this factor in the respective run.

There are two options on how to pass configurations to the artefact with a command:
- Pass factor levels as command line arguments (e.g., use the factor `a` as an argument to echo: `echo [% my_run.a %]`).
- Pass factor levels via the `config.json` file. For convenience, there is a `config.json` file in the working directory that contains the run config.


Moreover, for multi-instance experiments there is a variable `exp_host_lst` that contains information on all involved hosts of the experiment.
The format of the list is as follows:
```YAML
[{"host_type": x, "exp_host_type_idx": x, "exp_host_type_n": x, "is_controller": x, "public_dns_name": x, "private_ip_address": x}, ... ]
```

Unfortunately, at the moment it is not supported to use this variable within the experiment design (e.g., within a command).
TODO [nku] build functionality to provide access to host list of experiment: should be able to use `[% exp_host_lst %]` in `$CMD$`
