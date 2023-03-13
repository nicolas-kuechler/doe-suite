Quickstart
==========

Follow :ref:`installation:installation` to set up a project and install the DoE-Suite first.

The DoE-Suite provides a ``demo_project`` in the root of the repository that shows the required structure to integrate DoES into an existing project.
After completing the :ref:`installation:installation` section, it should be possible to run the examples , i.e., under ``demo_project/doe-suite-config/designs``, of the demo project.

Afterward, you can change the environment variable `DOES_PROJECT_DIR` to point to your own project (instead of the demo project) and continue from there as described in the :ref:`tutorial:tutorial`.

A Minimal Example
-----------------

We start with the minimal example of a suite design:

.. literalinclude:: ../../demo_project/doe-suite-config/designs/example01-minimal.yml
   :language: yaml
   :caption: doe-suite-config/designs/example01-minimal.yml


What does this design do?

1. It runs on a single instance of type ``small``

2. The design contains two ``$FACTOR$``: ``arg2`` and ``arg3``, with two levels each.
   In total there are 2 x 2 = 4 runs, i.e., configurations:

   - ``echo "hello world."``
   - ``echo "hello world!"``
   - ``echo "hello universe."``
   - ``echo "hello universe!"``


.. collapse:: Show Resulting Commands

   .. command-output:: make design suite=example01-minimal
      :cwd: ../..
      :shell:


Save it as :file:`example01-minimal.yml` or something similar under ``doe-suite-config/designs``.
Afterwards, you can run the experiment suite with:

.. code-block:: sh
   :caption: Start the experiment

   make run suite=example01-minimal id=new cloud=aws

This will start the experiment suite on AWS.
First, it creates a VPC and an EC2 instance corresponding to the ``host_type: small``.
The ``doe-suite-config/group_vars/small/main.yml`` file contains the configuration for the instance.

.. collapse:: Show Source

   .. literalinclude:: ../../demo_project/doe-suite-config/group_vars/small/main.yml
      :language: yaml
      :caption: doe-suite-config/group_vars/small/main.yml


After creating the instance, the DoE-Suite runs the four shell commands sequentially on the instance.
Whenever, a command finishes, the resulting ``stdout`` and ``stderr`` together with potential result files are fetched and saved under ``doe-suite-results`` on your local machine.


Quick Command Reference
-----------------------

These are the most important commands to get started with the DoE-Suite.

.. code-block:: sh
   :caption: Start a new experiment suite run

   make run suite=example01-minimal id=new


.. code-block:: sh
   :caption: Continue the last experiment suite

   make run suite=example01-minimal id=last


.. code-block:: sh
   :caption: Terminate all remote resources, e.g., terminate all EC2 instances, and local cleanup, e.g., pycache:

   make clean


To get an overview of the functionality use `make` or `make help`:

.. program-output:: make help --no-print-directory
      :caption: make help
      :cwd: ../..
      :shell:


.. todo::

   We could potentially include here a bit more extensive example as in the comment below

.. COMMENT:

   <a align="center">
      <img src="docs/resources/example.png" alt="Overview">
   </a>
   <!-- TODO [nku] improve styling and quality of the overview figure-->

   <!--
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
   -->


   #### Detailed Explanation

   The suite design consists of a single experiment `experiment_1` that runs on a single machine of type `small`, e.g., an EC2 instance.
   The experiment runs a script `demo_latency.py` that takes three command line arguments: `--opt`, `--size` (i.e., `payload_size_mb`), and `--out`.
   Naturally, the experiment config in `base_experiment` consists of these three arguments.
   In the experiment, we want to measure the latency for different sizes `--size` with and without the optimization `--opt`.
   As a result, these two parameters are marked as factors, i.e., with  `$FACTOR$` and a list of `levels` in each run, we use a different combination of the levels when running the script `demo_latency.py`.

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