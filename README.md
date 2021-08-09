<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="https://github.com/othneildrew/Best-README-Template">
    <img src="resources/flask.png" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">AWS Ansible Experiment Suite</h3>

  <p align="center">
    An experiment suite for running client-server or single-instance experiments on AWS EC2 instances.
  </p>
</p>

In a nutshell, the suite automatically runs experiments where multiple factors are varied based on simple `YAML` files:
```YAML
# experiment design with two factors with two levels each
seed: 1234                  # a constant in the experiment
payload_size_mb:            # a factor with two levels
  $FACTOR$: [1, 128]
opt:                        # a factor with two levels
  $FACTOR$: [true, false]

# -> Results in 4 runs (combinations of parameters) that are executed.
#    Note, the repeated execution of runs is possible.
```
and outputs an experiment result table:

| exp_name | exp_id     | run   | host     | seed | payload_size_mb | opt   | rt_mean | rt_std |
|----------|------------|-------|----------|------|-----------------|-------|---------|--------|
| simple   | 1626440718 | run_0 | client_0 | 1234 | 1               | true  | 5.2     | 0.3    |
| simple   | 1626440718 | run_1 | client_0 | 1234 | 1               | false | 32.9    | 1.5    |
| simple   | 1626440718 | run_2 | client_0 | 1234 | 128             | true  | 67.3    | 2.1    |
| simple   | 1626440718 | run_3 | client_0 | 1234 | 128             | false | 1356.2  | 10.2   |


Note, in this experiment `simple`, the `client_0` records in each repetition of a run the response time (`rt`).
In the table, we show for each configuration the mean and the standard deviation of the response time over multiple runs.

The experiment suite follows the naming conventions of [DoE](https://en.wikipedia.org/wiki/Design_of_experiments):
A `factor` is the parameter that changes between different runs, and in each run, a `factor` takes a particular `level`, i.e., value.

Moreover, under [Design of Experiments](#design-of-experiments), we show how to design and run experiments that are not a cross-product of factor levels.

<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li>
      <a href="#usage">Usage</a>
      <ul>
        <li><a href="#moving-beyond-the-example-experiment">Moving beyond the Example Experiment</a></li>
        <li><a href="#design-of-experiments">Design of Experiments</a></li>
        <li><a href="#running-an-experiment">Running an Experiment</a></li>
        <li><a href="#cleaning-up-aws">Cleaning up AWS</a></li>
        <li><a href="#experimental-results">Experimental Results</a></li>
      </ul>
    </li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  <!--<li><a href="#acknowledgements">Acknowledgements</a></li> -->
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

The AWS Ansible Experiment Suite automates the process of running experiments on AWS.
On a high level, the experiment suite creates AWS resources (VPC, EC2 instances), installs required packages, and builds the artifact.

Afterward, the suite sequentially executes jobs of an experimental design (DOE).
The suite supports a multi-factor and multi-level experiment design with repetition,
i.e., it is possible to vary multiple parameters and repeat each run.
A `YAML`file in [experiments/designs](experiments/designs) describes the full experiment design.

After completing a job, the suite downloads all result files and provides helper scripts for processing.

Finally, after completing the experiment (all jobs), the suite can clean up the created AWS resources.

### Built With

* [Ansible](https://www.ansible.com/)
* [YAML](https://yaml.org/)
* [Jinja](https://jinja.palletsprojects.com/en/3.0.x/)


<!-- GETTING STARTED -->
## Getting Started

After completing the getting started section, it should be possible to run the [example](experiments/design/example.yml) experiment that creates one client and one server instance runs the python scripts in [demo](demo) and fetches the results.

### Prerequisites

* Before starting, ensure that you have `pipenv` installed:
    ```sh
    pip install pipenv
    ```

* Moreover, create a `key pair for AWS` in the region `eu-central-1` [(see instructions)](https://docs.aws.amazon.com/servicecatalog/latest/adminguide/getstarted-keypair.html)
* and ensure that you can clone remote `repositories with SSH` [(see instructions for GitHub)](https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh).



### Installation

1. Create a repository from this template
2. Clone the newly created repository
    ```sh
    git clone https://github.com/<YOUR REPOSITORY>.git
    ```
3. Install the Python packages (for Ansible)

    ```sh
    pipenv install
    ```

4. Configure `ssh` and `ssh-agent`.

      * Configure ~/.ssh/config:  (add to file and replace the key for AWS, for example, with aws_ppl.pem)
          ```
          Host ec2*
          IdentityFile ~/.ssh/{{ exp_base.key_name }}
          User ubuntu
          ForwardAgent yes
          ```
      * Add the GitHub private key to ssh-agent.
        This allows cloning a GitHub repository on an EC2 instance without copying the private key or entering credentials.
        The process depends on your environment but should be as follows [(source)](https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh):

          1. Start ssh-agent in the background:
              ```sh
              eval "$(ssh-agent -s)"
              ```
          2. Add SSH private key to ssh-agent (replace with your key):
              ```sh
              ssh-add ~/.ssh/<YOUR PRIVATE KEY>
              ```
          3. (On a MAC, need add to keychain)


5. Install AWS CLI (version 2) and configure Boto

      * Install AWS CLI version 2 [(see instructions)](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)

      * Configure AWS credentials for Boto [(see instructions)](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html)
        ```sh
        aws configure
        ```
        By default, credentials should be in `~/.aws/credentials`.


6. Install the required Ansible collections

    ```sh
    pipenv run ansible-galaxy install -r requirements-collections.yml
    ```

7. Run the repository initialization helper script and configure the experiment suite and the example host types `client` and `server`.

    This prompts user input to perform variable substitution in the `group_vars/*/main.yml.j2` variable templates for the groups [all](group_vars/all/main.yml.j2), [client](group_vars/all/client.yml.j2), and [server](group_vars/all/server.yml.j2). Moreover, it configures the inventory template file [inventory/aws_ec2.yml.j2](inventory/aws_ec2.yml.j2).

    When unsure, set the unique `project id` and the AWS `key name` from the prerequisites and otherwise use the default options.

    ```sh
    pipenv run python scripts/repotemplate.py
    ```

8. Try running the example experiment design (see [experiments/designs/example.yml](experiments/designs/example.yml))

    ```sh
    pipenv run ansible-playbook experiment.yml -e "exp=example id=new"
    ```

<!-- USAGE EXAMPLES -->
## Usage

The following section discusses: (i) How to adapt the template for your artifact? (ii) How to design (define) experiments? (iii) How to run experiments? (iv) How to clean up AWS resources? (v) How to work with the experimental results?

The experiment suite splits an experiment into individual jobs.
A job is a single run of the benchmark with one specific configuration.
The relation between an experiment run and a job is that a run is repeated multiple times (see `n_repetitions` in experiment design).

The jobs are derived from the experiment design in [experiment/designs](experiment/designs).
The design contains a base configuration (`base_experiment`) that marks which options are factors of the experiment (i.e., what is varied in the experiment).
Moreover, the design contains a list of runs (`factor_levels`) that specifies the level of the factor in the run (i.e., what concrete value to use for a factor in a particular run).

The suite derives a list of jobs for the experiment in combination with the number of repetitions (see `n_repetitions` in experiment design).
Each job of an experiment receives an id: `<RUN>_<REP>`.


### Moving beyond the Example Experiment

The template repository contains `TODO`s in places where things typically need to be adjusted for a specific project.
For example, configuring the AWS EC2 instances (how many? which type? etc.), installing additional packages, and running the code.

For the basic configurations, we provide a script [scripts/repotemplate.py](scripts/repotemplate.py) that provides reasonable default options for the most important parameters (already done in the installation section).

```sh
pipenv run python scripts/repotemplate.py
```

#### Writing Systemd Services
Jobs are started as systemd services. You need to define there, how host service should be started and with which arguments.

In those service files, the following variables are available:
- `exp_run_config`: the run config to pass as parameters and access arguments stored in the experiment config. Alternatively, in the working directory there is a file called `config.json` with the run config.

- `host_ips` is a variable with a dictionary containing the private IPs of other hosts belonging to this experiment. For example, for the host types `client` (2 instances) and `server` (1 instance), this could look as follows:

  ```YAML
  host_ips = { 'client': [ '10.100.0.15', '10.100.0.77' ], 'server': [ '10.100.0.77' ] }
  ```

#### Further Examples

These are examples of projects that use the experiment-suite template and what the project implements additionally:

- [pps-lab/bthesis-emanuel-exp-suite](https://github.com/pps-lab/bthesis-emanuel-exp-suite) runs experiments on a single instance and also measures memory usage (in a second service).


### Design of Experiments

The experiment suite runs experiments based on `YAML` files in [experiments/designs](experiments/designs).

An experiment design `YAML` file consists of one or more experiments. Each experiment consists of the following parts:
1. **General configuration**:
  - The `n_repetitions` variable specifies how many times to repeat each experiment run. (i.e., how many times to execute an experiment run with the same configurations).
  - The `common_roles` variable specifies an ansible role that is executed once on the initial instance set up.

2. **Host types**: this section configures different host types. Each host has its own initial setup role `init_role` and `n` active instances of at most `n_max` instances. `n_check` of those instances are checked to determine whether a host is done.

3. **Base experiment**: The `base_experiment` consists of all the configuration options. All configuration options that vary between runs (i.e., the factors of the experiment) are marked with the placeholder `$FACTOR$`. The remaining configuration options are filled with a constant.

4. **Factor levels**: The list of `factor_levels` specifies the levels that the factors take in a particular experiment run. For example, in the first run of the experiment, the framework replaces the `$FACTOR$` placeholder with the first entry values in the `factors_levels`list.  


Example experiment design:
```YAML
experiments:
- simple:
    n_repetitions: 3
    common_roles:
    - setup-common
    host_types:
      single:
        n: 1
        init_role: setup-single
        n_max: 1
        n_check: 1
    base_experiment:
      seed: 1234
      payload_size_mb: $FACTOR$
      opt: $FACTOR$
    factor_levels:
    # 3 runs where we vary the factors payload and opt.
    # However, for the 1 MB payload, we don't run the opt.
    - payload_size_mb: 1
      opt: false
    - payload_size_mb: 128
      opt: true
    - payload_size_mb: 128
      opt: false

# experiments/designs/xyz.yml
```

#### Table File

For convenience when running a complete factorial design, i.e., experiment with every possible combination of all factor levels, we provide a script (see [scripts/expdesign.py](scripts/expdesign.py)) to generate the required config files based on a more concise representation.

When given a concise experiment configuration with a set of factors and each factor with multiple levels in a "table" form, the script expands the concise "table" form configuration into the experiment design by performing a cross-product of all factor levels.

Simple Example:

```sh
  pipenv run python scripts/expdesign.py --exps simple
```

Experiment in "table" form:

```YAML
n_repetitions: 2  # how often each run is repeated (i.e. each level config)
common_roles:     # roles that are run for all hosts during the initial setup
  - setup-common
host_types:
  single:
    n: 1                    # number of current instances
    init_role: setup-single # role run on the initial instance setup
base_experiment:
  seed: 1234                  # a constant in the experiment
  payload_size_mb:            # a factor with two levels
    $FACTOR$: [1, 128]
  opt:                        # a factor with two levels
    $FACTOR$: [true, false]

# experiments/table/simple.yml
```

transforms into the cross product of all factor levels:

An experiment in "design" form:
```YAML
experiments:
- simple:
    n_repetitions: 2
    common_roles:
    - setup-common
    host_types:
      single:
        n: 1
        init_role: setup-single
        n_max: 1
        n_check: 1
    base_experiment:
      seed: 1234
      payload_size_mb: $FACTOR$
      opt: $FACTOR$
    factor_levels:
    - payload_size_mb: 1
      opt: true
    - payload_size_mb: 1
      opt: false
    - payload_size_mb: 128
      opt: true
    - payload_size_mb: 128
      opt: false

# experiments/designs/simple.yml
```


### Running an Experiment

We run an experiment by starting the Ansible playbook.
We provide the name of an experiment design from `experiments/designs` (e.g., `example`), and we use `id=new` to run a new complete experiment.  

```sh
pipenv run ansible-playbook experiment.yml -e "exp_suite=example id=new"
```

When we start a new experiment, each specified experiment receives an experiment ID (a counter incremented based on the state folders stored in `experiments/state/example`). I.e., when there are multiple experiments specified in the config, each one of them will have its own ID.

The experiment suite periodically checks whether an experiment run is finished and then starts the next one according to the experiment design.

The variable `exp_n_tries` controls the maximum number of times to check whether the experiment finished.
In between checking, the playbook waits for `exp_check_wait_time` seconds (see `group_vars/all/main.yml`).

After the number of `exp_n_tries` is exceeded, the playbook stops. An already running job will continue to run on AWS, but the next job won't start unless the `experiments.yml` playbook runs.

To continue checking a previously started experiment, we can specify the ID of the experiment when starting the playbook:

```sh
pipenv run ansible-playbook experiment.yml -e "exp_suite=example id=<ID>"
```

For convenience, we can also use `id=last` to continue with the most recent experiment(s) with the provided name. If there are multiple experiments defined in the config, then this command will continue to run all of them (i.e., also multiple experiment IDs).

```sh
pipenv run ansible-playbook experiment.yml -e "exp_suite=example id=last"
```

### Cleaning up AWS


By default, after an experiment is complete, all resources created on AWS are terminated.
To deactivate this default behavior, provide the flag: `awsclean=false`.

Creating resources on AWS and setting up the environment takes a considerable amount of time. So, for debugging and short experiments, it can make sense not to terminate the instances. If you use this flag, be sure to check that instances are terminated when you are done.

Example:
```sh
pipenv run ansible-playbook experiment.yml -e "exp=example id=new awsclean=false"
```

Furthermore, we also provide a playbook to terminate all AWS resources:
```sh
pipenv run ansible-playbook clear.yml
```

### Experimental Results

The experiment suite creates a matching folder structure on the localhost and the remote EC2 instances.

Locally, each experiment job (repetition of an experiment run with a specific config) receives a separate folder, i.e., working directory:

`results/exp_<EXPERIMENT NAME>_ <EXPERIMENT ID>/run_<RUN>/rep_<REPETITION>`

- `RUN` is the index of the run (starts at 0)
- `REPETITION`is the index of the repetitions (starts at 0)

In this folder, we have a separate folder for each involved EC2 instance where all result files are downloaded.

`<HOST>_<HOST INDEX>`

- `HOST` is either `server` or `client`
- `HOST INDEX` is the index of the host (starts for both clients and servers at 0)


Example:
The folder `results/exp_example_1626423613/run_2/rep_1/server_0` contains all result files from the 1st server, from the 2nd repetition (rep starts with 0) of the 3rd run (run starts at 0) from the experiment named `example` with id `1626423613`.

The artifact (code) is executed on the remote machine in the experiment job's working directory. There are two folders in this working directory: `results` and `scratch`. Only the files in `results` are download at the end of the experiment job to the local machine.


#### Result Files

The script [scripts/results.py](scripts/results.py) supports loading experiment results in multiple formats into a panda data frame.
The data frame contains:
General info (exp name, exp id, run, host).
The run config (the parameters).
The experiment run results from your artifact.
Note, do not include the config in your results file because the script automatically adds the configuration to the data frame.

Example: `example`
```python
# use results from experiment "example" with id "1626083535" and "1626091111"
exp = {
    "example" : ["1626083535", "1626091111"]
}

# build a panda dataframe
df = read_df(results_dir, exp)

# or alternatively provide explicit regex lists for how to treat files (these are the defaults)
df = read_df(results_dir, exp,
                    regex_error_file=[re.compile(r".*_stderr\.log$")],    # output a warning if we there is a non-empty file matching the regex
                    regex_ignore_file = [re.compile(r".*_stdout\.log$")], # ignore these files
                    regex_csv_result_file=[re.compile(r".*\.csv$")],      # result file in csv format
                    regex_json_result_file=[re.compile(r".*\.json$")],    # result file in json format
                    regex_yaml_result_file=[re.compile(r".*\.yml$"), re.compile(r".*\.yaml$")]) # result file in yaml format
```

The provided script can handle the following result files if they follow the conventions:

* `CSV: Ideally, the result file should end in `.csv` and contain a header and then one or multiple result rows. Columns in the header and each row should be separated by `,`. See the notebook [scripts-demo.ipynb](scripts-demo.ipynb) for how to change the column type from string to a number column.
* `JSON`/`YAML`:  Ideally, the result file should end in `.json`, `.yaml`, or `.yml` respectively and contain a **flat (unnested) object** with a single result or a **list of flat objects** with multiple results. A list of objects corresponds to multiple rows in the dataframe. Nested JSON objects are flattened (e.g., `{"a": {"b": 1}}` turns to `{"a.b": 1}`) for the dataframe.

If your result files follow different conventions, please adapt [scripts/results.py](scripts/results.py) for your needs.

For more details, see the example in the notebook [scripts-demo.ipynb](scripts-demo.ipynb) that shows how to work with the data frame.

<!-- LICENSE -->
## License

Distributed under the Apache License. See `LICENSE` for more information.


<!-- CONTACT -->
## Contact

Nicolas Küchler - [nicolas-kuechler](https://github.com/nicolas-kuechler)

Project Link: [https://github.com/pps-lab/aws-simple-ansible](https://github.com/pps-lab/aws-simple-ansible)



<!-- ACKNOWLEDGEMENTS
## Acknowledgements

-->
