========
Commands
========

.. is labeled as "commands:cleaning up cloud"

..  warning::

    The DoE-Suite can easily start many instances in a remote cloud. If there is an error in the execution, or the suite finishes before all jobs are complete, then these remote resources are not terminated and can generate high costs.
    Always check that resources are terminated. We also provide the following command to ensure that the previously started instances are terminated:

    .. code-block:: sh

        make clean


The interface of the DoE-Suite is defined in a ``Makefile``.
In the following, we focus on the most frequently used commands.

.. code-block:: sh
    :caption: Show all commands

    make help

.. collapse:: Show Output

   .. command-output:: make help
      :cwd: ../..
      :shell:



Running an Experiment Suite
---------------------------

Here we focus on the commands that are used to start and continue an experiment suite.
For more information on the experiment suite design, see :ref:`design/index:suite design` and on the execution, see  :ref:`execution/index:running experiments`.

.. code-block:: sh
    :caption: Start a new experiment suite

    make run suite=example01-minimal id=new


.. code-block:: sh
    :caption: Continue with the last experiment suite

    make run suite=example01-minimal id=last


.. code-block:: sh
    :caption: Continue the experiment suite with a specific ID

    make run suite=example01-minimal id=<ID>


.. code-block:: sh
    :caption: Start an experiment suite on non-default cloud

    make run suite=example01-minimal id=new cloud=euler


.. code-block:: sh
    :caption: Start suite with the explicit choice ``run-keep``: Keep instances running after suite is complete

    make run-keep suite=example01-minimal id=new

.. warning::

    If you use ``run-keep``, be sure to check that instances are terminated when you are done.


Cleaning up Cloud
-----------------

By default, after an experiment suite is complete, all `experiment` resources created on the cloud are terminated.

However, if something goes wrong, i.e. an error occurs, the suite times out, or the suite is stopped manually, the created resources on the cloud remain running.

Further, creating resources on a cloud and setting up the environment takes a considerable amount of time.
So, for debugging and short experiments, it can make sense not to terminate the instances.
If you use run experiments with ``run-keep``, be sure to check that instances are terminated when you are done.


.. code-block:: sh
    :caption: Terminate all remote resources, e.g., terminate all EC2 instances, and local cleanup, e.g., pycache

    make clean


.. tip::

    Double check on the cloud that all resources are terminated, and setup budget alerts.



ETL Results Processing
----------------------

The ETL pipeline is used to process the results of an experiment suite.
The results processing runs on your local machine and is triggered automatically when the new results are available locally, i.e., an experiment job is complete.

However, often it is also useful to trigger a run of the ETL pipeline manually, e.g., for styling a plot.


.. code-block:: sh
    :caption: Manually trigger a run of the ETL results pipeline (runs locally)

    # can replace `id=last` with actual id, e.g., `id=1655831553`
    make etl suite=example01-minimal id=last


:ref:`execution/results:super etl` pipelines can be used to process the results of multiple experiment suites together.

.. code-block:: sh
    :caption: Run Super-ETL results pipeline

     # can set `out` for example to a figures folder of a paper
    make etl-super config=demo_plots out=.



Status and Info
---------------

.. code-block:: sh
    :caption: Get information about available suites and experiments

    make info


.. code-block:: sh
    :caption: Get progress information about the last suite run

    # w/o suite filter (all suites)
    make status id=last

    # w/ suite filter
    make status suite=example01-minimal id=last


Developing Suite Designs
------------------------

.. tip::

    Ensure that the environment variable ``DOES_PROJECT_DIR`` points to the project directory.


.. code-block:: sh
    :caption:  Configure Project: Initialize ``doe-suite-config`` from a template

    make new


.. code-block:: sh
    :caption:  List all commands that a suite design defines (+ Visualize ETL pipelines)

    make design suite=example01-minimal


.. code-block:: sh
    :caption:  Validate a design and show  the design with default values assigned

    make design-validate suite=example01-minimal


.. code-block:: sh
    :caption:  Developing ETL pipeline by using the pipeline from the design

    # can replace `id=last` with actual id, e.g., `id=1655831553`
    make etl-design suite=example01-minimal id=last

    # The same as: `make etl suite=example01-minimal id=last`
    #   but uses the etl pipeline defined in `doe-suite-config/designs`
    #   compared to the etl pipeline in `doe-suite-results/example01-single_<ID>/suite_design.yml`
