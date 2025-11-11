# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the DoE-Suite framework.

## Overview

**DoE-Suite** (Design of Experiments Suite) is a framework for automating computational experiments across multiple cloud backends. It provides a structured way to:

- Define experiment suites with factorial designs (factors and levels)
- Execute experiments on various backends (AWS, SLURM clusters, Docker, manual inventory)
- Process results through ETL (Extract-Transform-Load) pipelines
- Generate visualizations and analyses from experimental data

The framework uses **Ansible** for orchestration, **Poetry** for Python dependency management, and a **Makefile** interface for all operations.

## Project Structure

```
doe-suite/
├── Makefile                    # Main interface for all commands
├── ansible.cfg                 # Ansible configuration
├── src/                        # Ansible playbooks for experiment orchestration
├── doespy/                     # Python package for ETL, design validation, etc.
├── docs/                       # Sphinx documentation
├── cookiecutter-doe-suite-config/  # Template for project configuration
└── demo_project/               # Example project showing structure
```

## Prerequisites

Before using DoE-Suite, ensure you have:

- **Poetry** (>= 2.0.1): Python dependency management
- **Cookiecutter**: For generating project configuration templates
- **SSH access**: Ability to clone repositories via SSH
- **GNU Parallel** (optional): For running integration tests in parallel

### Cloud-Specific Prerequisites

- **AWS**: Key pair in `eu-central-1`, AWS CLI configured with credentials
- **Euler/SLURM**: SSH access to the cluster
- **Docker**: Docker installed and running
- **Manual Inventory**: SSH access to all listed hosts

## Environment Variables

DoE-Suite requires these environment variables (typically set in `.envrc` using direnv):

```bash
# REQUIRED: Root directory of your project repository containing doe-suite-config/
export DOES_PROJECT_DIR=/path/to/your/project

# REQUIRED: Unique identifier (initials or org acronym) to avoid conflicts with collaborators
export DOES_PROJECT_ID_SUFFIX=abc

# AWS-specific
export DOES_SSH_KEY_NAME=your-aws-key-name
export DOES_AWS_USER=ubuntu

# Euler-specific
export DOES_EULER_USER=your-nethz

# Docker-specific
export DOES_DOCKER_USER=ubuntu
export DOES_DOCKER_SSH_PUBLIC_KEY=~/.ssh/id_rsa.pub
export DOCKER_HOST=unix://var/run/docker.sock  # optional

# Optional: Override default cloud backend
export DOES_CLOUD=aws  # [aws, euler, docker, or inventory name]

# Optional: Override state management
export DOES_CLOUD_STATE=terminate  # [terminate, keep, stop]
```

## Common Commands

All DoE-Suite operations use `make` from the `doe-suite/` directory. The Makefile requires `DOES_PROJECT_DIR` to be set.

### Getting Help

```bash
# Show all available commands
make help
```

### Running Experiments

```bash
# Start a new experiment suite run on default cloud (AWS)
make run suite=<SUITE> id=new

# Continue the last run of a suite
make run suite=<SUITE> id=last

# Run on a specific cloud backend
make run suite=<SUITE> id=new cloud=aws       # AWS EC2
make run suite=<SUITE> id=new cloud=euler     # SLURM cluster
make run suite=<SUITE> id=new cloud=docker    # Local Docker
make run suite=<SUITE> id=new cloud=custom    # Manual inventory

# Run only experiments matching a regex pattern
make run suite=<SUITE> id=new expfilter=<REGEX>

# Keep instances running after completion (useful for debugging)
make run-keep suite=<SUITE> id=new
```

### Cleanup

```bash
# Terminate all cloud resources and local cleanup
make clean

# Delete all incomplete results
make clean-result

# Terminate AWS instances only
make clean-aws

# Terminate Docker containers only
make clean-docker
```

### ETL (Results Processing)

ETL pipelines run locally and process experimental results.

```bash
# Run ETL pipeline for a specific suite run
make etl suite=<SUITE> id=last

# Run ETL for all available results
make etl-all

# Use design pipeline instead of saved pipeline (for development)
make etl-design suite=<SUITE> id=last

# Run super-ETL to combine results from multiple suites
make etl-super config=<CONFIG> out=<OUTPUT_DIR>

# Run only specific pipelines in super-ETL
make etl-super config=<CONFIG> out=<OUTPUT_DIR> pipelines="pipeline1 pipeline2"

# Clean ETL results (can be regenerated)
make etl-clean suite=<SUITE> id=last
make etl-clean-all
```

### Status and Information

```bash
# List available suite designs
make info

# Show progress of a specific suite run
make status suite=<SUITE> id=last

# Show progress of all suites
make status id=last
```

### Design Development

```bash
# Initialize doe-suite-config from template
make new

# List all commands that a suite design defines
make design suite=<SUITE>

# Validate a suite design
make design-validate suite=<SUITE>
```

### Testing

```bash
# Run a suite and compare results to expected
make test-<SUITE> cloud=aws

# Run minimal test suite
make aws-mini-test    # AWS
make docker-mini-test # Docker
make euler-mini-test  # Euler

# Re-run all ETL pipelines and compare to current state
make etl-test-all
```

## Suite Design Concepts

Suite designs are YAML files in `doe-suite-config/designs/` that define experiments.

### Basic Structure

```yaml
experiment_name:
  n_repetitions: 3  # Repeat each run configuration 3 times
  host_types:
    small:          # Host type (defined in group_vars/small/main.yml)
      n: 1          # Number of instances
      init_roles: [setup-role1, setup-role2]  # Ansible roles for setup
      $CMD$: "command to run"  # Command template with Jinja2 variables

  base_experiment:
    # Configuration options for the experiment
    param1:
      $FACTOR$: [value1, value2, value3]  # Factor with 3 levels
    param2:
      $FACTOR$: [optionA, optionB]        # Factor with 2 levels
    constant_param: fixed_value            # Constant across runs

# Optional ETL pipeline
$ETL$:
  pipeline1:
    experiments: [experiment_name]  # Or "*" for all experiments
    extractors:
      JsonExtractor: {}
      ErrorExtractor: {}
    transformers:
      - name: RepAggTransformer
        data_columns: [metric1, metric2]
    loaders:
      CsvSummaryLoader: {}
```

### Factors and Levels

- **Cross-product format**: Use `$FACTOR$` as key with list of levels
  - `param: {$FACTOR$: [a, b, c]}` creates 3 levels
  - Multiple factors create full cross-product (e.g., 3×2 = 6 runs)

- **Level-list format**: Specify exact combinations using `factor_levels`
  - Useful when you don't want full cross-product

### Special Variables

- `exp_host_lst`: Runtime information about all hosts in the experiment
  - Access with filters: `[% exp_host_lst | to_private_dns_name('server', 0, '???') %]`
  - Get runtime vars: `[% 'exp_code_dir' | at_runtime(exp_host_lst) %]`

- `run`: Run ID of the current experiment run

- `$slurm_job_minutes$`: Time limit for SLURM jobs (Euler only)

## ETL Pipeline

ETL pipelines process experimental results in three stages:

1. **Extract**: Traverse `doe-suite-results/` and aggregate raw data into a Pandas DataFrame
   - Each extractor has a regex pattern to match filenames
   - Common extractors: `JsonExtractor`, `CsvExtractor`, `ErrorExtractor`, `IgnoreExtractor`

2. **Transform**: Process the DataFrame through a chain of transformers
   - Each transformer takes DataFrame input and returns modified DataFrame
   - Common transformers: `RepAggTransformer` (aggregate repetitions)

3. **Load**: Generate visualizations or persist processed data
   - Common loaders: `CsvSummaryLoader`, plotting loaders

### Custom ETL Components

Define project-specific extractors, transformers, and loaders in:
`doe-suite-config/does_etl_custom/`

## Cloud Backends

### AWS (Amazon Web Services)

- Creates EC2 instances with VPC and security group setup
- Supports both single and multi-instance experiments
- Automatically terminates instances after completion (unless `run-keep`)
- Host types map to EC2 instance types in `group_vars/<host_type>/main.yml`

### Euler (SLURM Cluster)

- Submits experiments as SLURM jobs
- **Single-instance experiments only** (no client-server support)
- Automatically retrieves results when jobs complete
- Host types control SLURM queue and resource allocation

### Docker

- Runs experiments in local Docker containers
- Useful for testing and development
- Uses Ubuntu 20.04 LTS by default
- Can provide custom Dockerfile in `doe-suite-config/inventory/docker/`

### Manual Inventory (Ansible Inventory)

- Use predefined hosts listed in YAML inventory file
- Assumes exclusive access to hosts (no conflict checking)
- Regular Ansible inventory format in `doe-suite-config/inventory/<name>.yml`

## Execution Models

### Single-Instance Experiments

- Jobs scheduled on remote instance using `task spooler`
- Jobs continue even if DoE-Suite connection is lost
- Reconnect with `make run suite=<SUITE> id=<ID>` to retrieve results

### Multi-Instance Experiments

- DoE-Suite orchestrates each job across multiple hosts
- DoE-Suite **must remain running** for jobs to proceed
- Useful for client-server experiments

## Results Organization

```
doe-suite-results/
└── <suite>_<id>/
    ├── suite_design.yml        # Saved suite design
    ├── .inventory              # Ansible inventory used
    ├── <experiment>/
    │   └── <run_id>/
    │       ├── config.json     # Run configuration
    │       ├── stdout.log      # Standard output
    │       ├── stderr.log      # Standard error
    │       └── <result_files>  # Files produced by experiment
    └── etl_results/
        └── <pipeline>/
            └── <etl_outputs>   # ETL-generated files (CSV, plots, etc.)
```

## Integration with Parent Project

When DoE-Suite is a submodule of a larger project:

1. **Project Configuration**: Create `doe-suite-config/` in parent project
   - `designs/`: Suite design YAML files
   - `group_vars/`: Host type configurations
   - `roles/`: Ansible roles for setup
   - `inventory/`: Manual inventory files
   - `does_etl_custom/`: Custom ETL components
   - `super_etl/`: Super-ETL configurations

2. **Environment Setup**: Set `DOES_PROJECT_DIR` to parent project root

3. **Git Repository**: Set `git_remote_repository` in `group_vars/all/main.yml`
   - Code will be cloned on each remote host

4. **Custom Commands**: Add project-specific make targets in `doe-suite-config/Makefile`

## Important Notes

- **SSH Agent Forwarding**: Required for cloning private repositories on remote hosts
  - Add SSH keys to ssh-agent: `ssh-add ~/.ssh/<key>`
  - Enable in SSH config: `ForwardAgent yes`

- **Cost Management**: Always verify cloud resources are terminated
  - Use `make clean` after experiments
  - Set up budget alerts on cloud providers

- **Timeouts**: Configure `job_n_tries` and `job_check_wait_time` in `group_vars/all/main.yml`
  - Max runtime per experiment: `#jobs × job_n_tries × job_check_wait_time` seconds

- **Parallel Tests**: Use GNU Parallel for running multiple test suites concurrently

- **Documentation**: Full documentation available in `doe-suite/docs/`
  - Build with: `make docs-build`
  - View with: `make docs` (opens in browser)

## Typical Workflow

1. **Setup**: Initialize configuration and install dependencies
   ```bash
   make new      # Initialize doe-suite-config
   make install  # Install dependencies
   ```

2. **Design**: Create suite design in `doe-suite-config/designs/<suite>.yml`
   ```bash
   make design-validate suite=<suite>  # Validate design
   make design suite=<suite>            # Preview commands
   ```

3. **Execute**: Run experiments. (This command polls routinely for the status, keep it running with large timeout)
   ```bash
   make run suite=<suite> id=new cloud=aws
   ```

4. **Monitor**: Check progress
   ```bash
   make status suite=<suite> id=last
   ```

5. **Process**: Run ETL on results
   ```bash
   make etl suite=<suite> id=last
   ```

6. **Analyze**: Use super-ETL to combine multiple suite results
   ```bash
   make etl-super config=paper_plots out=./figures
   ```

7. **Cleanup**: Terminate resources
   ```bash
   make clean
   ```

## Troubleshooting

- **Connection Issues**: Check SSH config and agent forwarding
- **Cloud Resources Not Terminating**: Run `make clean` or check cloud console
- **Job Timeouts**: Increase `job_n_tries` in `group_vars/all/main.yml`
- **ETL Errors**: Use `make etl-design` to test pipeline changes
- **Design Validation Errors**: Use `make design-validate` to check syntax