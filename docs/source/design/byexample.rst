=======================
Suite Design By Example
=======================

In this section we show a series of examples that demonstrate the features for suite designs.
The examples start with the minimal suite design and then become more complex.

More information, about the design format and defaults, can be found in :ref:`design/design:experiment design`.


example01-minimal
-----------------

The ``suite=example01-minimal`` shows the minimal suite design with a single experiment on a single host and no ETL pipeline.

.. literalinclude:: ../../../demo_project/doe-suite-config/designs/example01-minimal.yml
   :language: yaml
   :caption: doe-suite-config/designs/example01-minimal.yml


.. collapse:: Show Resulting Commands

   .. command-output:: make design suite=example01-minimal
      :cwd: ../../..
      :shell:


example02-single
----------------

The ``suite=example02-single`` demonstrates that:

- a suite can consist of multiple experiments that are executed in parallel (here 2 experiments)

- ``init_roles`` in host_type defines an ansible role to install packages etc. on a host

- a ``config.json`` file with the run config is within the working directory of the ``$CMD$`` -> can be used to pass config parameters

- we can repeat each run configuration multiple times (``n_repetitions``).

- an ``$ETL$`` pipeline can automatically process result files (e.g., extract from result structure, transform into a suited df, load a summary)


.. literalinclude:: ../../../demo_project/doe-suite-config/designs/example02-single.yml
   :language: yaml
   :caption: doe-suite-config/designs/example02-single.yml


.. collapse:: Show Resulting Commands

   .. command-output:: make design suite=example02-single
      :cwd: ../../..
      :shell:


example03-format
----------------

The ``suite=example03-format`` demonstrates the use of the two (three) formats for expressing factors (varying parameters).

.. literalinclude:: ../../../demo_project/doe-suite-config/designs/example03-format.yml
   :language: yaml
   :caption: doe-suite-config/designs/example03-format.yml


.. collapse:: Show Resulting Commands

   .. command-output:: make design suite=example03-format
      :cwd: ../../..
      :shell:

example04-multi
---------------

The ``suite=example04-multi`` demonstrates:

- an experiment involving multiple instances (e.g., client-server)

- that ``common_roles`` lists roles executed on all host_types, while ``init_roles`` is a host_type specific role.

- the use of the variable ``exp_host_lst`` in  to get the dns name of of other instances (e.g., get dns name of server)

- the use of ``check_status``, to control when an experiment job is considered to be over. If set to ``True``, then the experiment job waits until the  stops. default(True)

.. literalinclude:: ../../../demo_project/doe-suite-config/designs/example04-multi.yml
   :language: yaml
   :caption: doe-suite-config/designs/example04-multi.yml


.. collapse:: Show Resulting Commands

   .. command-output:: make design suite=example04-multi
      :cwd: ../../..
      :shell:

example05-complex
-----------------

The ``suite=example05-complex`` shows complex experiments with:

- a mix of formats

- multiple experiments

- running different commands on different instances

.. literalinclude:: ../../../demo_project/doe-suite-config/designs/example05-complex.yml
   :language: yaml
   :caption: doe-suite-config/designs/example05-complex.yml

.. collapse:: Show Resulting Commands

   .. command-output:: make design suite=example05-complex
      :cwd: ../../..
      :shell:


example06-vars
--------------

The ``suite=example06-vars`` demonstrates the re-usability of variables in the design.

.. literalinclude:: ../../../demo_project/doe-suite-config/designs/example06-vars.yml
   :language: yaml
   :caption: doe-suite-config/designs/example06-vars.yml

.. collapse:: Show Resulting Commands

   .. command-output:: make design suite=example06-vars
      :cwd: ../../..
      :shell:

example07-etl
-------------

The ``suite=example07-etl`` demonstrates advance usages of ETL results processing.


.. literalinclude:: ../../../demo_project/doe-suite-config/designs/example07-etl.yml
   :language: yaml
   :caption: doe-suite-config/designs/example07-etl.yml


.. collapse:: Show Resulting Commands

   .. command-output:: make design suite=example07-etl
      :cwd: ../../..
      :shell:


example08-superetl
------------------

The ``example08-superetl`` generates dummy data that is used to showcase advanced (super) etil processing.


.. literalinclude:: ../../../demo_project/doe-suite-config/designs/example08-superetl.yml
   :language: yaml
   :caption: doe-suite-config/designs/example08-superetl.yml


.. collapse:: Show Resulting Commands

   .. command-output:: make design suite=example08-superetl
      :cwd: ../../..
      :shell: