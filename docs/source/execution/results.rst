==================
Experiment Results
==================


Result Directory
----------------

.. todo::

    TODO: discuss the result directory structure


The experiment suite creates a matching folder structure on the localhost and the remote EC2 instances.

Locally, each experiment job (repetition of an experiment run with a specific config) receives a separate folder, i.e., working directory:

``<DOES_PROJECT_DIR>/doe-suite-results/<SUITE>_<SUITE ID>/<EXPERIMENT>/run_<RUN>/rep_<REPETITION>``

- ``RUN`` is the index of the run (starts at 0)
- ``REPETITION`` is the index of the repetitions (starts at 0)

In this folder, we group the involved hosts by host type and have a separate folder for each involved EC2 instance where all result files are downloaded.

``<HOST TYPE>/host_<HOST INDEX>``

- ``HOST TYPE`` is the host type from the suite design
- ``HOST INDEX`` is the index of the host (starts for each host type at 0)


Example:
The folder ``doe-suite-results/example04-multi_1634661802/exp_client_server/run_2/rep_1/client/host_0`` contains all result files from the 1st client host, from the 2nd repetition (rep starts with 0) of the 3rd run (run starts at 0) from the experiment named ``exp_client_server`` that is part of the suite ``example04-multi`` with id ``1626423613``.

The artifact (code) is executed on the remote machine in the experiment job's working directory. There are two folders in this working directory: ``results`` and ``scratch``. Only the files in ``results`` are download at the end of the experiment job to the local machine.

ETL
---

.. todo::

    TODO: discuss the ETL pipeline execution



Super ETL
---------

.. todo::

    TODO: discuss the super ETL pipeline execution