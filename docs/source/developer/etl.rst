ETL Processing
==============

.. warning::

    This is a work in progress. The ETL pipeline is currently under
    development and may change in the future.
    The documentation is not up to date.

Instructions for defining ETL pipelines, and descriptions of base
components

Dev Transformers
----------------

Factor-dependent transformers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We are often interested in output differences split out by the different
factor values for each run. Instead of manually specifying what columns
we are interested in, some transformers support the use of the
``$FACTORS$`` tag in the ETL design files, which will automatically be
expanded to the factor columns of the experiment.

The ETL pipeline provides the per-experiment factor information to the
transformers in the dataframe as additional information. On the
transformer side, the ``Transformer`` base class provides the
``_expand_factors`` helper to automatically expand ``$FACTORS$`` into
the right values. An example is provided below.

.. code:: yaml

   transformers:
   - name: GroupByAggTransformer
     data_columns:
     - accuracy
     - total_time
     groupby_columns:
     - exp_name
     - audit
     - $FACTORS$ # will be expanded to factor_columns of the experiment

The ``$FACTORS$`` tag must be explicitly provided as a column value to
be expanded to the experiment factors. For an example, see
``GroupByAggTransformer``.

Dev Super ETL
=============

Doe suite supports the definition of suite-transcending (super-suite)
ETL pipelines that combines experiments from multiple suites, which we
refer to as super ETL.

Pipeline configs are defined in ``doe-suite-config/super_etl`` and can
be run similar to regular etl, using # TODO [nku] needs to use makefile
in commands

.. code:: bash

   poetry run python src/super_etl.py --config pipeline


Custom output location
----------------------

The default option is to place results in
``doe-suite-results/super_etl``. This may be overridden using the
``output_path`` option to specify a base directory for outputs. In the
following example, a pipeline named ``pipeline`` outputs a file
``plot.pdf`` defined in ``config.yml``.

.. code:: bash

   poetry run python src/super_etl.py --config config --output_path {paper_dir}
   # (Over)writes: paper_dir/config/plot.pdf

In the base directory, subdirectories per-pipeline and per-config file
can be created using ``--output_dir_config_name_disabled`` and
``output_dir_pipeline``.

.. code:: bash

   poetry run python src/super_etl.py --config config --output_path {paper_dir} --output_dir_config_name_disabled
   # (Over)writes: paper_dir/plot.pdf

   poetry run python src/super_etl.py --config config --output_path {paper_dir} --output_dir_pipeline
   # (Over)writes: paper_dir/config/pipeline/plot.pdf

   poetry run python src/super_etl.py --config_name config --output_path {paper_dir} --output_dir_config_name_disabled --output_dir_pipeline
   # (Over)writes: paper_dir/pipeline/plot.df

The default is to create a directory for each config file, but not for
each pipeline as generally the output files have the pipeline name. This
translates to ``output_dir_config_name_disabled=False`` and
``output_dir_pipeline=True``.

Config changes
--------------

There are two changes compared to a regular ETL pipeline. First is is
the ``experiments`` key. ``experiment`` now contains a dict of suites
with a list of the experiments of those suites to include. Note that the
other keys of the pipeline ``transformers``, ``loaders`` and
``extractors`` stay the same and can therefore often be easily
copy-pasted.

.. code:: yaml

   $ETL$:
     pipeline_name:
       experiments:
         suite_1: [ exp_1 ]
         suite_2: [ exp_2, exp_3 ]
       ...transformers, loaders, extractors etc.

The second change is that the runs must be specified to load data from
in the form of the ``suite_id``. The ``suite_id`` can be specified
per-suite and per-experiment. Specifying suite ids per-suite:

.. code:: yaml

   $SUITE_ID$:
     suite_1: 1648453067
     suite_2: 1651052734

Experiment-specific suite ids

.. code:: yaml

   $SUITE_ID$:
     suite_1: 1648453067
     suite_2:
       exp_1: 1651052734
       exp_2: 1651052743

Use the ``$DEFAULT$`` key to specify a default:

.. code:: yaml

   $SUITE_ID$:
     suite_1: 1648453067
     suite_2:
       $DEFAULT$: 1651052734
       exp_2: 1651052743

Full example:

.. code:: yaml

   $SUITE_ID$:
     suite_1: 1648453067
     suite_2: 1651052734

   $ETL$:
     pipeline_name:
       experiments:
         suite_1: [ exp_1 ]
         suite_2: [ exp_2, exp_3 ]
       extractors:
         JsonExtractor: {} # with default file_regex
         ErrorExtractor: {} # if a non-empty file exists matching the default regex -> then we throw an error using the ErrorExtractor
         IgnoreExtractor: {} # since we want that each file is processed by an extractor, we provide the IgnoreExtractor which can be used to ignore certain files. (e.g., stdout)
       transformers:
         - name: RepAggTransformer # aggregate over all repetitions of a run and calc `mean`, `std`, etc.
           data_columns: [latency] # the names of the columns in the dataframe that contain the measurements
       loaders:
         CsvSummaryLoader: # write the transformed detl_info["suite_dir"]ataframe across the whole experiment as a csv file
           output_dir: "pipeline1" # write results into an output dir
         DemoLatencyPlotLoader: # create a plot based on project-specific plot loader
           output_dir: "pipeline1" # write results into an output dir

Jupyter Notebook support
~~~~~~~~~~~~~~~~~~~~~~~~

The below code snippet can be used to use an ETL pipeline in a notebook
for quick debugging and analysis. The ETL’s loaders are skipped and
instead the DataFrame is returned (that would have been processed by the
loaders). Simply call
``super_etl.run_multi_suite("pipeline.yml", return_df=True)`` to return
the dataframe.

Full example

.. code:: python

    %env DOES_PROJECT_DIR= # place correct dir here
    import sys
    import os
    sys.path.insert(0, os.path.abspath('doe-suite/doespy'))
    display(sys.path)
    import doespy.etl.etl_base as etl_base

   df = super_etl.run_multi_suite("pipeline.yml", "etl_output", return_df=True)

   # inspect df
