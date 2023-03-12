Quickstart
==========

Follow :doc:`install` to set up a project and install the DoE-Suite first.

A Minimal Example
-----------------

.. literalinclude:: ../../../demo_project/doe-suite-config/designs/example01-minimal.yml
   :language: yaml
   :caption: doe-suite-config/designs/example01-minimal.yml

What does this design do?

1. It runs on a single instance of type ``small``

2. The design contains of two ``$FACTOR$``: ``arg2`` and ``arg3``, with two levels each.
   In total there are 2 x 2 = 4 runs, i.e., configurations:

   - echo "hello world."
   - echo "hello world!"
   - echo "hello universe."
   - echo "hello universe!"

Save it as :file:`example01-minimal.yml` or something similar under ``doe-suite-config/designs``.
To start the experiment, use the ``make`` target ``run``.
You need to specify the name of the suite ``suite`` that you want to start.
Further, ``id=new`` specifies that you want to start a new suite and not continue i


Afterward, we can execute the experiment with

.. code-block:: sh

   make run suite=example01-minimal id=new cloud=aws


.. collapse:: Show Resulting Commands

   .. command-output:: make design suite=example01-minimal
      :cwd: ../../..
      :shell:




To get started, the DoE-Suite provides a [demo project](demo_project) that shows the required structure to integrate DoES into an existing project.
After completing the getting started section, it should be possible to run the [example suite designs](demo_project/doe-suite-config/designs) of the demo project.

Afterward, you can change the environment variable `DOES_PROJECT_DIR` to point to your own project (instead of the demo project) and continue from there.



Command Reference
-----------------

Running Experiments
~~~~~~~~~~~~~~~~~~~

Start an experiment suite:

   .. code-block:: sh

      make run suite=example01-minimal id=new


Continue the last experiment suite:

   .. code-block:: sh

      make run suite=example01-minimal id=last

Start an experiment suite on a specific cloud:

  .. code-block:: sh

      make run suite=example01-minimal id=new cloud=euler

Start an experiment suite with the explicit choice (`run-keep`, `run-stop`, `run-terminate`) what to do after suite is complete:

   .. code-block:: sh

      make run-keep suite=example01-minimal id=new
      make run-stop suite=example01-minimal id=new
      make run-terminate suite=example01-minimal id=new


ETL - (Local) Results Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run ETL results pipeline:

   .. code-block:: sh

      # can replace `id=last` with actual id, e.g., `id=1655831553`
      make etl suite=example01-minimal id=last

Run Super-ETL results pipeline:

   .. code-block:: sh

      # can set `out` for example to a figures folder of a paper
      make etl-super config=demo_plots out=.

Status and Info
~~~~~~~~~~~~~~~

Get information about available suites and experiments:

   .. code-block:: sh

      make info

Get progress information about the last suite run:

  .. code-block:: sh

      # w/o suite filter (all suites)
      make status id=last

  .. code-block:: sh

      # w/ suite filter
      make status suite=example01-minimal id=last

Cleanup
~~~~~~~

Terminate all remote resources, e.g., terminate all EC2 instances, and local cleanup, e.g., pycache:

  .. code-block:: sh

      make clean

Developing
~~~~~~~~~~

:warning: Ensure that the environment variable `DOES_PROJECT_DIR` points to the project directory.

Configure Project: Initialize `doe-suite-config` from a template

  .. code-block:: sh

      make new

List all commands that a suite design defines (+ Visualize ETL pipelines)

  .. code-block:: sh

      make design suite=example01-minimal

Validate a design and show  the design with default values assigned:

   .. code-block:: sh

      make design-validate suite=example01-minimal

Developing ETL pipeline by using the pipeline from the design:

   .. code-block:: sh

      # can replace `id=last` with actual id, e.g., `id=1655831553`
      make etl-design suite=example01-minimal id=last

      # The same as: `make etl suite=example01-minimal id=last`
      #   but uses the etl pipeline defined in `doe-suite-config/designs`
      #   compared to the etl pipeline in `doe-suite-results/example01-single_<ID>/suite_design.yml`



Overview
~~~~~~~~~
To get an overview of the functionality use `make` or `make help`:

.. program-output:: make help --no-print-directory
      :caption: make help
      :cwd: ../../..
      :shell:
