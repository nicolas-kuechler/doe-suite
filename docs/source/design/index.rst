============
Suite Design
============


.. toctree::
    :caption: Contents:
    :maxdepth: 1

    byexample
    design


..

    The `base_experiment` consists of all the configuration options.
    All configuration options that vary between runs (i.e., the factors of the experiment) are marked with the placeholder `$FACTOR$`. The remaining configuration options are filled with a constant.
    See the example [example03-format.yml](demo_project/doe-suite-config/designs/example03-format.yml) design to see the three different options of expressing factors.

    The  2(+1) different formats are:
    - the `cross` format which is the concise form for a cross product of all factors
    - the `level-list` format which allows to specify a list with a concrete level for each factor (i.e., not full cross-product)
    - a mix between `cross` and `level-list` format that combines the advantages of both formats.

    The `cross` format uses the keyword `$FACTOR$` as a YAML key, while the `factor list` uses `$FACTOR$` as a YAML value and expects a corresponding level in the `factor_levels` list.

    When we use the `level-list` format or the mixed format, then we have the `factor_levels` that specify the levels that the factors take in a particular experiment run. For example, in the first run of the experiment, the framework replaces the `$FACTOR$` placeholder with the first entry values in the `factors_levels` list.

    For each suite design you can optionally configure multiple ETL pipelines to process result files.

    The reason for this is that between experiments from different domains, there are a lot of common steps which can be covered by shared implementations
    For example, experiments may report results in a CSV and hence extracting this CSV file from the results folder structure is a common step.
    In case an experiment has some unique requirements, a project can define its own extractors, transformers, and loaders.


Special Experiment Design Variables
-----------------------------------

There are some special variables that can be used in the experiment configuration under ``base_experiment`` (or under ``factor_levels``):


- **Host Runtime Information**: ``exp_host_lst``


    The exp_host_lst variable stores runtime information for all hosts involved in the experiment. This includes details on how other hosts can be reached, as well as other runtime-dependent variables. It is represented as a list of dictionaries following this schema:

    .. code:: yaml

      [
        {
          'host_type': x,
          'exp_host_type_idx': x,
          'exp_host_type_n': x,
          'public_dns_name': x,
          'private_dns_name': x,
          'ansible_host_id': x,
          'hostvars': {..}
        },
        ...
      ]


    Each project includes a set of pre-defined Jinja filters to simplify using this variable, available in: ``doe-suite-config/designs/filter_plugins/helper.py``

    The two most important use cases are:

    - **DNS / IP address Lookup**: In multi-instance experiments, Jinja filters allow retrieving connection details for other instances. For example, to get the private DNS name of the first server host type, with a fallback default if undefined: ``[% exp_host_lst | to_private_dns_name('server', 0, '<???>') %]``

    - **Accesing Host Group Vars**: To retrieve host variables defined in ``doe-suite-config/group_vars/<host_type>/main.yml``, use the special ``at_runtime`` Jinja filter. This indirection is necessary because some variables depend on runtime conditions (e.g., cloud-specific folder paths). For example, to get the source code directory path on the remote host: ``[% 'exp_code_dir' | at_runtime(exp_host_lst) %]``


    These are all the available filters:

    .. automodule:: helper
        :members:
        :exclude-members: FilterModule


- **Run ID**: The variable ``run`` is available in the experiment design and allows referencing the run ID of the respective run. This can be useful, for example, for implementing special behavior for the first run or referencing file names that include the run ID.

- **Euler Job Timeout**: In the Euler cloud, the host type controls the SLURM job submission queue (e.g., how many cores). Unlike other schedulers, SLURM also enforces a time limit on jobs. This limit can be configured either in the host type group vars or through a special variable in the experiment design, allowing fine-grained control at the level of individual runs. For example, setting the following variable in the experiment design specifies a time limit of 240 minutes: ```$euler_job_minutes$: 240```. Other clouds ignore this variable.
