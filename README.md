<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="https://github.com/nicolas-kuechler/doe-suite">
    <img src="docs/resources/flask.png" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">DoES - Design of Experiments Suite</h3>

  <p align="center">
   Orchestrate multi-instance, e.g., client-server, or single-instance experiments on AWS EC2 instances.
  </p>
</p>


## About The Project

DoES automatically orchestrates and executes a set of experiments, i.e., an experiment suite, based on a simple declarative `YAML`  design file.
Each experiment of a suite defines the involved computing resources (AWS EC2 instances) as well as a list of run configurations.
DoES follows the naming conventions of [DoE](https://en.wikipedia.org/wiki/Design_of_experiments):
A `factor` is the parameter that changes between different runs, and in each run, a `factor` takes a particular `level`, i.e., value.
DoES automatically downloads generated result files and processes them in an ETL pipeline to generate summaries and plots.

<!--
TODO [nku] unify these two parts
The AWS Ansible Experiment Suite automates the process of running experiments on AWS.
On a high level, the experiment suite creates AWS resources (VPC, EC2 instances), installs required packages, and builds the artifact.

Afterward, the suite sequentially executes jobs of an experimental design (DOE).
The suite supports a multi-factor and multi-level experiment design with repetition,
i.e., it is possible to vary multiple parameters and repeat each run.
A `YAML`file in [experiments/designs](experiments/designs) describes the full experiment design.

After completing a job, the suite downloads all result files and provides helper scripts for processing.

Finally, after completing the experiment (all jobs), the suite can clean up the created AWS resources.
-->

### Example: Suite Design

The core of DoES are suite design files that define a set of experiments and how to process results:

```YAML
experiment_1:
  n_repetitions: 3
  host_types:
    small:
      n: 1
      init_roles: setup-small
      $CMD$: "{{ exp_code_dir }}/demo_project/.venv/bin/python {{ exp_code_dir }}/demo_project/demo_latency.py --opt [% my_run.opt %] --size [% my_run.payload_size_mb %] --out [% my_run.out %]"
  base_experiment:
    out: json
    payload_size_mb:
      $FACTOR$: [10, 20, 30, 40]
    opt:
      $FACTOR$: [True, False]

$ETL$:
  pipeline1:
    experiments: [experiment_1]
    extractors:
      JsonExtractor: {}
      ErrorExtractor: {}
      IgnoreExtractor: {}
    transformers:
      - name: RepAggTransformer
        data_columns: [latency]
    loaders:
      CsvSummaryLoader: {}
      DemoLatencyPlotLoader: {}

```

In a nutshell, the above suite runs 8 configurations (cross-product of the two factors `payload_size_mb` and `opt`) and repeats each run 3 times. Note that suite designs are not limited to the cross-product of factors.
Finally, the ETL pipeline processes the results and creates a plot:

<a href="https://github.com/othneildrew/Best-README-Template">
    <img src="docs/resources/plot.png" alt="Plot">
</a>

#### Explanation

The suite design consists of a single experiment `experiment_1` that runs on a single EC2 instance of type `small`.
The experiment runs a script `demo_latency.py` that takes three command line arguments: `--opt`, `--size` (i.e., `payload_size_mb`), and `--out`.
Naturally, the experiment config in `base_experiment` consists of these three arguments.
In the experiment we want to measure the latency for different sizes `--size` with and without the optimization `--opt`.
As a result, these two parameters are marked as factors i.e., with  `$FACTOR$` and a list of `levels`: in each run we use a different combination of the levels when running the script `demo_latency.py`.

The factor `payload_size_mb` has 4 levels, while the factor `opt` has 2 levels.
In this format we run the cross-product of all factors which results in 4x2=8 different runs.
We repeat each run `n_repetitions: 3` times and hence we end up with 3*8=24 experiment jobs.

Once an experiment job is complete, we process the resulting files (produced by the job) in an ETL pipeline.
In the Extract stage we use the listed extractors to create a result table (dataframe) based on the result files of the job.
We assign each file to exactly one extractor by matching a regex on the filename. (e.g., all files ending in `.json` are processed by the `JsonExtractor`)
In the following Transform stage, we apply a chain of Transformers on the table from the Extract stage.
Here, the `RepAggTransformer` aggregates over the repetitions of an experiment run config, i.e., calculates mean, std, etc. over the repetitions.
Finally, in the Load stage, we execute all Loaders with the table from the Transform stage.
Here, the `CsvSummaryLoader`stores the table in form of a csv and the `DemoLatencyPlotLoader` creates an experiment-specific plot for the experiment.


#### Built With

* [Ansible](https://www.ansible.com/)
* [YAML](https://yaml.org/)
* [Jinja](https://jinja.palletsprojects.com/en/3.0.x/)

After discussing an example, the remainder of the readme is structured as follows:

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

## Cheatsheet

Start the experiment suite:
```
poetry run ansible-playbook src/experiment-suite.yml -e "suite=example id=new"
```

Cmd to clean:
```
TODO [nku] missing command
```

Configure Project:
```
TODO [nku] missing command
```

Run ETL results pipeline:
```
TODO [nku] missing command
```



<!-- GETTING STARTED -->
## Getting Started

After completing the getting started section, it should be possible to run the [example suite designs](demo_project/does_config/designs) of the [demo project](demo_project).
The demo project shows how to integrate DoES into an existing project.
<!-- TODO [nku] maybe here we should just point to a concrete design?-->


We assume that you have an existing project for which you want to run benchmarks with DoES.

### Prerequisites

* Before starting, ensure that you have `poetry` installed [(see instructions)](https://python-poetry.org/docs/)

* Moreover, create a `key pair for AWS` in the region `eu-central-1` [(see instructions)](https://docs.aws.amazon.com/servicecatalog/latest/adminguide/getstarted-keypair.html)

* and ensure that you can clone remote `repositories with SSH` [(see instructions for GitHub)](https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh).

* you have an existing repository for which you want to use DoES


### Installation

1. Add the DoES repository as a submodule to your project repository.

<!-- TODO describe how to do this -->

2. Move to the root of the DoES repository

    ```sh
    cd doe-suite
    ```

3. Install the Python packages (for Ansible)

    ```sh
    poetry install
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
    poetry run ansible-galaxy install -r requirements-collections.yml
    ```


7. Run the repository initialization helper script and configure the experiment suite

    <!--
    TODO [nku] describe this process (re-design it) -> Q: maybe for the demo-project it's a bit strange that we need to generate the group_vars etc.?
    However, setting a prj_id might be sensible, + setting github repository

    and the example host types `client` and `server`.

    This prompts user input to perform variable substitution using the `resources/repotemplate/group_vars/*/main.yml.j2` templates. By default, it creates four groups: `all`, `server`, `client`, and `ansible_controller`.

    When unsure, set the unique `project id` and the AWS `key name` from the prerequisites and otherwise use the default options.

    ```sh
    pipenv run python scripts/repotemplate.py
    ```

    -->

8. Try running the minimal example experiment design (see [demo_project/does_config/designs/example01-minimal.yml](demo_project/does_config/designs/example01-minimal.yml))

    ```sh
    poetry run ansible-playbook src/experiment-suite.yml -e "suite=example01-minimal id=new"
    ```


<!-- USAGE -->
## Usage

<!-- TODO [nku] write an overview -->

* project folder
* does config
* does results

* terminology image from presentation?

### Moving beyond the Demo Project

After the getting started section we are able to run the suite designs from the demo_project.
<!-- TODO [nku] questionable if this requires its own section -->

### Running an Experiment Suite

We run an experiment suite by starting the Ansible playbook.
We provide the name of an experiment suite design from `does_config/designs` (e.g., `example01-minimal`), and we use `id=new` to run a new complete experiment.

```sh
poetry run ansible-playbook src/experiment-suite.yml -e "suite=example01-minimal id=new"
```

The playbook reads the **environment variable** `DOES_PROJECT_DIR` which must point to the project folder.
For example, when we want to run the `demo_project` then we set `DOES_PROJECT_DIR=<...>/doe-suite/demo_project`.
Within the project folder, the suite expects that there is a `does_config` folder that controls how to run the suite.

When we start a new experiment suite, it receives a unique ID (epoch timestamp). Each experiment of the suite must have a unique name in the experiment design specification.

The playbook periodically checks whether an experiment run is finished and then downloads the results.
The variable `job_n_tries` controls the maximum number of times to check whether the job finished.
In between checking, the playbook waits for `job_check_wait_time` seconds (see `does_config/group_vars/all/main.yml`).
After the number of `job_n_tries` is exceeded, the playbook aborts.

Experiments that involve multiple instances (e.g., client-server experiment) require the experiment-suite playbook to start the next job after the previous finished. The consequence is that when the playbook aborts because `job_n_tries` is exceeded,  an already running job will continue to run on AWS, but the next job won't start unless the `experiment-suite.yml` playbook runs.

For experiments that run on a single instance, all jobs are scheduled on the instance from the beginning. As a consequence, after a job completes, the next job automatically starts even when the `experiment-suite.yml` playbook does not run. In this case, the playbook is only required to fetch results.


To continue checking a previously started experiment, we can specify the ID of the experiment when starting the playbook:

```sh
poetry run ansible-playbook src/experiment-suite.yml -e "suite=example01-minimal id=<ID>"
```

For convenience, we can also use `id=last` to continue executing the most recent experiment suite (the one with the highest suite ID).

```sh
poetry run ansible-playbook src/experiment-suite.yml -e "suite=example01-minimal id=last"
```

### Cleaning up AWS

By default, after an experiment suite is complete, all _experiment_ resources created on AWS are terminated.
To deactivate this default behavior, provide the flag: `awsclean=false`.

Creating resources on AWS and setting up the environment takes a considerable amount of time. So, for debugging and short experiments, it can make sense not to terminate the instances. If you use this flag, be sure to check that instances are terminated when you are done.

Example:
```sh
poetry run ansible-playbook src/experiment-suite.yml -e "suite=example id=new awsclean=false"
```

Furthermore, we also provide a playbook to terminate all AWS resources:
```sh
poetry run ansible-playbook src/clear.yml
```

:warning: The ansible controller instance, if used, is not removed. It is intended to be left running and trigger individual experiment runs. To remove it, use the flag `awscleanall=true`.

### Experimental Results

The experiment suite creates a matching folder structure on the localhost and the remote EC2 instances.

Locally, each experiment job (repetition of an experiment run with a specific config) receives a separate folder, i.e., working directory:

`<DOES_PROJECT_DIR>/does_results/<SUITE>_<SUITE ID>/<EXPERIMENT>/run_<RUN>/rep_<REPETITION>`

- `RUN` is the index of the run (starts at 0)
- `REPETITION`is the index of the repetitions (starts at 0)

In this folder, we group the involved hosts by host type and have a separate folder for each involved EC2 instance where all result files are downloaded.

`<HOST TYPE>/host_<HOST INDEX>`

- `HOST TYPE` is the host type from the suite design
- `HOST INDEX` is the index of the host (starts for each host type at 0)


Example:
The folder `does_results/example04-multi_1634661802/exp_client_server/run_2/rep_1/client/host_0` contains all result files from the 1st client host, from the 2nd repetition (rep starts with 0) of the 3rd run (run starts at 0) from the experiment named `exp_client_server` that is part of the suite `example04-multi` with id `1626423613`.

The artifact (code) is executed on the remote machine in the experiment job's working directory. There are two folders in this working directory: `results` and `scratch`. Only the files in `results` are download at the end of the experiment job to the local machine.


## Suite Design

* list series of examples

### AWS Environment

* host types -> group_vars, init roles
* script to add host types

### Run Configuration

* constant vs factor -> levels
* different ways to express

### ETL

* extractor + available default (regex pattern)
* transformer + available default
* loaders + available default


## More Documentation
More documentation can be found [here](./docs).

<!-- LICENSE -->
## License

Distributed under the Apache License. See `LICENSE` for more information.


<!-- CONTACT -->
## Contact

Nicolas Küchler - [nicolas-kuechler](https://github.com/nicolas-kuechler)

Miro Haller - [Miro-H](https://github.com/Miro-H)

Project Link: [https://github.com/pps-lab/aws-simple-ansible](https://github.com/pps-lab/aws-simple-ansible)



<!-- ACKNOWLEDGEMENTS
## Acknowledgements

-->