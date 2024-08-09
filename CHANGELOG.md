# Changelog

The project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html): `major.minor.patch` i.e., `breaking.feature.bugfix`.

We use annotated git tags for each release commit:
1. Create a new tag locally: `git tag -a <tag-name> -m"<annotation>" [commit]`
(Example for Head: `git tag -a v1.0.0 -m "release 1.0.0"`)
2. Push the tag to remote repo: `git push origin tag <tag_name>`
3. Create a release from the tag on Github


<!--
## [Unreleased] - yyyy-mm-dd


-->
## [1.2.0] - 2024-08-09

### Added

- Add `DOES_RESULTS_DIR` environment variable to change the default results dir `<DOES_PROJECT_DIR>/doe-suite-results` (can be useful for artefact evaluation)

### Changed

- Extend `etl_debug.py` to include an option to specify `overwrite_suite_id_map` that will overwrite specific suite ids in a super_etl.
  The `overwrite_suite_id_map` can now also be used to filter `pipeline.experiments` in super etl designs.

## [1.1.1] - 2024-05-30

### Fixed

- update Python dependencies
- allow referencing suite names in (super) ETL that do not have a design but instead have an existing result.

## [1.1.0] - 2024-04-30

### Added

- **Introduce Docker cloud (run suites locally)**:
    - uses the Docker API to create hosts as docker containers.  `cloud=docker`
    - uses Ubunutu 20.04 LTS as default image (but custom Dockerfiles can be used)

- **Add `docker-test.yml` for CI via Github Action**:
    Runs all the example design tests with `cloud=docker` within the Github checks.

### Changed

- runs the local tests with GNU parallel (instead of `make -j`).

### Fixed

- fixed non-determinism issues in the ETL of the test suite by adding an explicit sorting transformer in certain steps.

## [1.0.0] - 2024-04-16


### Upgrade Process

Existing project should update the following in their `doe-suite-config` to use this version of doe-suite:

- Add inventory folder containing euler.yml (can be found in the `inventory` dir inside the `cookiecutter-doe-suite-config` or the `demo_project`). See [demo_project/doe-suite-config/inventory/euler.yml](demo_project/doe-suite-config/inventory/euler.yml).

- Update `poetry.lock` file in `doe-suite-config` using `poetry update doespy`, to update the lockfile with new dependencies added to the doespy project

- [Optional] In order to use the new custom machine cloud backend, update the path definition in `groups_vars/all/main.yml` to:
    ```yaml
    remote:
    dir: "{{ remote_dir | default('/home/' + ansible_user | mandatory('ansible_user must be set') + '/doe-suite/' + prj_id + '/' + suite) }}"
    results_dir: "{{remote_results_dir | default('/home/' + ansible_user + '/doe-suite-results') }}"
    ```

### Added

- **Support cloud definitions based on an Ansible Inventory File**:

    - In addition to running experiments on AWS and ETHZ Euler, an Ansible inventory file can now also define the remote experiment environment. This allows the doe-suite to run experiments on any set of machines that are reachable with SSH.

    - With introducing more potential clouds/backends, we need support for cloud-specific (potentially even host-specific) variables in the experiment design, e.g., defining a path. This is supported via the existing variable `exp_host_lst`, which already contained the dns_name/ip of all hosts in the experiment. Each host in this list now also has an entry `hostvars`, which provides access to all variables on that host. The new jinja2 filter `[% 'test' | at_runtime(exp_host_lst) %]` allows accessing the value of a variable at runtime. Without additional arguments, it will raise an error if the variable has different values on different hosts participating in the experiment.

    - The `euler` cloud is now also implemented as a cloud by inventory file. (see `doe-suite/cookiecutter-doe-suite-config/{{cookiecutter.repo_name | default("doe-suite-config") }}/inventory/euler.yml`)

    - We have renamed/removed a lot of `euler` specific task files (because now if experiments can be run not only on aws and euler).


- **Custom jinja filter in experiment design**:
To simplify the experiment design, we added the possibility to define project-specific custom Jinja2 filters under `doe-suite-config/design/filter_plugins`, which can then be used in the experiment design. For example, when accessing a host-specific (cloud-dependent) variable at runtime, we have an `at_runtime` Jinja filter.

- **Multi-Command runs (main and background tasks on same host)**:
We support `multi-command` runs (see, `example05-complex`). We always have a main cmd, but then we can have an arbitrary number of background tasks that are bound to the lifetime of the main command. If the main command finishes, we also ensure that the background tasks are terminated.

- **Demo Notebook developing ETL steps**:
We added can example for developing etl steps (with caching the inputs to the step) `demo_project/doe-suite-config/super_etl/debug_etl.ipynb`.

- **Introduce `ColCrossPlotLoader`**:
    -  We add the `ColCrossPlotLoader` which is an advanced loader that allows building complex plots based on the data. (see the documentation for more details)
    - Add super etl examples that use the  `ColCrossPlotLoader` (see `doe-suite/demo_project/doe-suite-config/super_etl`)
    - We added a new example design: `example08-superetl`, which generates some fake data that is used to showcase etl plotting features.

### Changed

- in setup roles for doe-suite, ensure that sudo is only required if a package is missing (otherwise) non-sudo access is sufficient.
- update the way poetry is installed in role `setup-small`.

- For extractors, the `file_regex` defaults can now be defined by overriding the class property.

- By default, super etls have the output path `doe-suite-results-super` next to `doe-suite-results`



### Fixed

- in docs: for etl steps replace the broken automodule with manual docs.

- Bugfix tsp pattern in case the command contains a `[`.

## [0.4.1] - 2024-01-23

### Changed

- update python dependencies


## [0.4.0] - 2024-01-23

### Added

- use pydantic for super etl (+ support include)

- add save data option to plot loader

### Changed

- only run docs deploy action on main branch

### Fixed

- **tsp status module consistency of jobs between servers**:
 In tsp status module, add check to see if there is an inconsistent set of jobs between servers, which can happen if one of the servers loses the job in tsp for some reason. Before doe-suite would get in some kind of inexplicable loop, now it checks if there are inconsistencies. In some cases there are still issues when some jobs are still running, but this should fix most of the issues.

- **tsp_info regex**:
Update regex in tsp_info to handle negative exit code



## [0.3.0] - 2023-12-22

### Added

- **Add support for `$SUITE_ID$` dict replacement of super etl via command line**:
Each super ETL configuration starts with a $SUITE_ID$ dictionary, specifying the run ids for the results. With this update, we introduce support to replace this dictionary via the command line.

- **ETL Extractors now receive the run config as part of their options:**
This enhancement enables more intricate extractors to implement advanced functionalities, such as implementing filters during the extraction stage. As this does not change the Extractors' interface, we ensure backward compatibility.



## [0.2.0] - 2023-08-11


### Added

- **New Experiment Design Feature `except_filters`**:
We added a basic implementation of #71 that allows filtering out certain combinations.

- **New Super ETL Feature: `pipelines` filter**:
We add the possibility when running  a super_etl via make to run only a subset of pipelines (see `pipelines="a b"`)

- **ETL Step**:
We add a new ETL Loader that allows storing a data frame as a pickle.

- **Option to save ETL results to Notion**:
We add a utility function that allows storing the results of a loader to a Notion page.

### Changed

- **Optimize config/dir creation**:
As part of the setup, before running experiments, we create all working directories and place the `config.json` in the folder.
Until now, this relied on pure Ansible. However, for many jobs, this creation becomes a bottleneck.
Now, there is a custom module that does this more efficiently.

- **Optimize result fetching**:
We replaced the slow fetching of results with an additional custom module.
More efficiency is possible because now `tsp` or `slurm` do not need to process a completing job id one-by-one.
Instead, they can report that a list of job ids finished and can be downloaded.

- **ETL Extract Optimization**:
We only flatten results that require flattening, which speeds up the processing.


## [0.1.0] - 2023-05-16

### Added

- **Documentation**: start sphinx documentation

### Changed

- **Design Validation**: switch design validation to pydantic models (experiment design schema)



[unreleased]: https://github.com/nicolas-kuechler/doe-suite/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/nicolas-kuechler/doe-suite/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/nicolas-kuechler/doe-suite/compare/v0.4.1...v1.0.0
[0.4.1]: https://github.com/nicolas-kuechler/doe-suite/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/nicolas-kuechler/doe-suite/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/nicolas-kuechler/doe-suite/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/nicolas-kuechler/doe-suite/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/nicolas-kuechler/doe-suite/releases/tag/v0.1.0



<!--
## [0.0.1] - yyyy-mm-dd

### Added

- ...

### Changed

- ...

### Fixed

- ...

### Removed

- ...

[0.0.1]: https://github.com/olivierlacan/keep-a-changelog/releases/tag/v0.0.1

-->
