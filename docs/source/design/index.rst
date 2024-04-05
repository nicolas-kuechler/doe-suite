============
Suite Design
============


.. toctree::
    :caption: Contents:
    :maxdepth: 1

    byexample
    design


.. todo::

    TODO: Talk about the available variables somewhere (exp_code_dir, exp_host_list)





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