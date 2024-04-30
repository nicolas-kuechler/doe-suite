========
Tutorial
========


We assume that you already have a project repo where you want to integrate the doe-suite, otherwise you can create a directory and init a new repository:

.. code-block:: sh

    mkdir my-project
    cd my-project
    git init

Afterward, follow the :doc:`installation instructions </installation>` to integrate the doe-suite in your project as a submodule.

At the end of the installation section, you can run the suite designs from the ``demo_project``.
To use the suite in your project, you need to change the environment variable ``DOES_PROJECT_DIR`` from pointing to the ``demo_project`` to your project.
As a summary, these environment variables should now be set:

.. code-block:: sh

    # path to your project
    export DOES_PROJECT_DIR=<PATH-TO-YOUR-PROJECT>

    # your unique shortname, e.g., nku
    export DOES_PROJECT_ID_SUFFIX=<SUFFIX>

    # choose default cloud: aws, euler
    export DOES_CLOUD=<DEFAULT-CLOUD>

    # for AWS
    export DOES_SSH_KEY_NAME=<YOUR-PRIVATE-SSH-KEY-FOR-AWS>

    export DOES_AWS_USER=<SSH-USERNAME>

    # for Euler
    export DOES_EULER_USER=<YOUR-NETHZ>

    # for Docker
    export DOES_DOCKER_USER=<SSH-USERNAME>  # [optional] defaults to ubuntu
    export DOES_DOCKER_SSH_PUBLIC_KEY=<SSH-PUBLIC-KEY>  # e.g., ~/.ssh/id_rsa.pub
    export DOCKER_HOST=<DOCKER-HOST> # [optional]  defaults to unix://var/run/docker.sock

..  tip::

    `Direnv <https://direnv.net/>`_ allows project-specific env vars in an `.envrc` file.




Move to the ``doe-suite`` repository and create your project-specific ``doe-suite-config`` with the help of a `Cookiecutter <https://www.cookiecutter.io/>`_ project template.
For a start, it should be fine to accept default values except for the **repo** you should use the repo of your project instead of the ``doe-suite`` repo.

.. code-block:: sh

    cd doe-suite
    make new


Note that ``make new`` first checks whether there is already a ``doe-suite-config`` in the ``DOES_PROJECT_DIR``.

--------------

Project Layout
--------------

Your project repository should have a folder ``doe-suite-config`` which contains a skeleton of the whole configuration.

Overall, the DoE - Suite adds three top level folders to a project repository: ``doe-suite``, ``doe-suite-config``, and ``doe-suite-results``.
The ``doe-suite`` folder is the doe-suite repo as a submodule.
The ``doe-suite-config`` folder contains the whole configuration of how to run experiments + project specific extensions of the suite.
In the ``doe-suite-results`` folder all the result files are stored.

The complete folder structure for a project looks as follows:

..  tabs::

    ..  tab:: Collapsed

        .. code-block:: sh

            <your-project-repository>
            ├── doe-suite                  # the doe-suite repo as a submodule
            ├── doe-suite-config
            │   ├── designs                # experiment suite designs
            │   ├── does_etl_custom        # custom steps for processing results
            │   ├── group_vars             # host type config (e.g.,instance type)
            │   ├── inventory              # manual inventories for ansible
            │   ├── roles                  # setup host types setup roles
            │   ├── super_etl              # multi suite results processing
            |   └── pyproject.toml
            ├── doe-suite-results          # all experiment results
            │   └── ...
            └── ...                        # your project files

    ..  tab:: Expanded

        .. code-block:: sh

            <your-project-repository>
            ├── doe-suite                  # the doe-suite repo as a submodule
            ├── doe-suite-config
            │   ├── designs                # experiment suite designs
            │   │   ├── design_vars        # shared variables
            │   │   │   └── <vars>.yml
            │   │   ├── etl_templates      # shared results processing
            │   │   │   └── <etl>.yml
            │   │   ├── <suite1>.yml
            │   │   └── <suite2>.yml
            │   ├── does_etl_custom        # custom steps for processing results
            │   │   └── <steps>.py
            │   ├── group_vars             # host type config (e.g., instance type)
            │   │   ├── all                # shared config
            │   │   │   └── main.yml
            │   │   ├── <host-type1>
            │   │   │   └── main.yml
            │   │   └── <host-type2>
            │   │       └── main.yml
            |   ├── inventory              # manual inventories for ansible (custom clouds)
            |   |   ├── euler.yml          # euler cloud is implemented as inventory
            |   |   ├── <cloud-inventory1>.yml
            |   |   └── <cloud-inventory2>.yml
            │   ├── roles                  # setup host types setup roles
            │   │   ├── <setup-1>
            │   │   │   └── tasks
            │   │   │       └── main.yml
            │   │   └── <setup-2>
            │   │       └── tasks
            │   │           ├── aws.yml    # cloud specific roles
            │   │           └── euler.yml
            │   ├── super_etl              # multi suite results processing
            |   |    └── <analysis.yml>
            |   └── pyproject.toml
            ├── doe-suite-results          # all experiment results
            │   └── ...
            └── ...                        # your project files


..
    ..  tab:: Intermediate

        .. code-block::

            <your-project-repository>
            ├── doe-suite                  # the doe-suite repo as a submodule
            ├── doe-suite-config
            │   ├── designs                # experiment suite designs
            |   |   ├── <suite1>.yml
            │   │   └── <suite2>.yml
            │   ├── does_etl_custom        # custom steps for processing results
            │   ├── group_vars             # host type config (e.g.,instance type)
            │   │   ├── all                # shared config
            │   │   │   └── main.yml
            │   │   ├── <host-type1>
            │   │   │   └── main.yml
            │   │   └── <host-type2>
            │   │       └── main.yml
            │   ├── roles                  # setup host types setup roles
            │   │   ├── <setup-1>
            │   │   │   └── ...
            │   │   └── <setup-2>
            │   │   │   └── ...
            │   └── super_etl              # multi suite results processing
            ├── doe-suite-results          # all experiment results
            │   └── ...
            └── ...                        # your project files


------------
Suite Design
------------

.. todo::

    TODO: Add description of designs and maybe include make design


The figure above shows that a suite design consists of one or more experiments.
Each experiment defines the computational environment (i.e., how many machines of which type) and a list of run configurations (i.e., concrete parameters) that we want to execute.
Within the run configurations we distinguish between constants and factors.
Constant remain the same across all runs, while for factors, we use in each run a unique combination of their levels.
To improve validity, we support repeating a run multiple times.

Different experiments in the suite are executed on a different set of host instances **in parallel**, while run configurations within an experiment are executed **sequentially** on the same set of host instances.

For each experiment, one instance is the controller which is logically responsible for coordination.


The experiment suite runs experiments based on `YAML` files in `doe-suite-config/designs`.
The `YAML` files represent the structure discussed above.


---------------
(Add) Host Type
---------------

The host type config follows the structure of Ansible ``group_vars``.

The variables defined in ``all/main.yml`` are applying to all hosts, while the variables under ``<host-type1>/main.yml`` correspond specifically to the host type of name ``<host-type1>``.

The name of the folder, e.g., placeholder ``<host-type1>``, is then referenced by a suite design.

.. code-block::

    <your-project-repository>
    └── doe-suite-config
        ├── ...
        └── group_vars
            ├── all
            │   └── main.yml
            ├── <host-type1>
            │   └── main.yml
            └── <host-type2>
                └── main.yml


To add a new host type, create a corresponding folder under ``doe-suite-config/group_vars/`` and ensure that the required variables are set.

For example, the host type ``small`` of the ``demo_project``:

.. literalinclude:: ../../demo_project/doe-suite-config/group_vars/small/main.yml
   :language: yaml
   :caption: doe-suite-config/group_vars/small/main.yml

----------------
(Add) Setup Role
----------------

The host type setup roles are regular `Ansible Roles <https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_reuse_roles.html>`_ and can be used to perform all sorts of tasks required before running experiments.
For example: install packages, download data, and building the system artefact.

The name of the role, e.g., placeholder ``<setup-1>``, is then referenced by a suite design.

The name of the file under ``tasks/`` determines whether they are the same on all clouds, i.e., ``main.yml`` or there are cloud specific tasks, e.g., ``aws.yml`` or ``euler.yml``.


.. code-block::

    <your-project-repository>
    ├── ...
    └── doe-suite-config
        ├── ...
        └── roles
            ├── <setup-1>
            │   └── tasks
            │       └── main.yml
            └── <setup-2>
                └── tasks
                    ├── aws.yml
                    └── euler.yml


--------------
(Add) ETL Step
--------------

The ``doe-suite-config`` folder is also a `Poetry <https://python-poetry.org/>`_ project with a package package ``does_etl_custom`` to allow adding project-specific results processing.

.. code-block:: sh

    <your-project-repository>
    ├── ...
    └── doe-suite-config
        ├── ...
        ├── does_etl_custom
        │   └── <steps>.py
        └── pyproject.toml


The DoE-Suite already provides a few steps that implement common features.
However, the majority of projects will need custom processing, e.g., for building a plot.
Below, we discuss how to add custom ``Extractor``, ``Transformer``, and ``Loader``.

The ``pyproject.toml`` file allows installing custom Python packages not yet used in .
For example, to add the `Seaborn <https://seaborn.pydata.org/>`_ visualization library navigate to the ``doe-suite-config`` directory and use Poetry to add the dependency:

.. code-block:: sh

    cd doe-suite-config
    poetry add seaborn


Extractor
~~~~~~~~~

The ``Extractor`` steps are responsible for bringing all generated results into a table form (data frame) together with the configuration.
Extracting information about the suite and the run config are done automatically.
For extracting the results itself, we configure a set of Extractors.


.. todo::

    maybe remove the details on the extractor here

During the extract phase, we loop over all produced result files and assign them to exactly one extractor through a regex on the filename. The mapping must be 1:1, otherwise the phase aborts with an error.
The reason behind this is that an experiment job should only generate expected files.
Each extractor has a default regex on the filename. For example, the ``YamlExtractor`` matches all files ending in ``.yml`` and ``.yaml``. However, it is possible to overwrite this default list in the ETL config of the suite design.

To add a custom ``Extractor`` extend the ``Extractor`` base class in the ``does_etl_custom`` package and implement the required methods.

.. code-block:: py

    from doespy.etl.steps.extractors import Extractor

    class MyExtractor(Extractor):

        def default_file_regex() -> List[str]:
            # your implementation

        def extract(self, path: str, options: Dict) -> List[Dict]:
            # your implementation


.. todo::

    add link to etl section

More details can be found in the   or by consulting the already provided ``Extractor``.

.. collapse:: Extractor [Show Source]

    .. literalinclude:: ../../doespy/doespy/etl/steps/extractors.py
        :language: python
        :caption: doespy/doespy/etl/steps/extractors.py


Tranformer
~~~~~~~~~~

The ``Transformer`` steps are responsible for bringing the table into a suitable form. For example, since we have an experiment with repetition, it is useful to aggregate over the repetitions and calculate error metrics.

The list of ``transformers`` in the ``$ETL$`` design is executed as a chain: the first entry receives the dataframe from the extract phase and passes the modified dataframe to the next transformer in the list.

To add a custom ``Transformer`` extend the ``Transformer`` base class in the ``does_etl_custom`` package and implement the required methods.

.. code-block:: py

    from doespy.etl.steps.transformers import Transformer

    class MyTransformer(Transformer):

        def transform(self, df: pd.DataFrame, options: Dict) -> pd.DataFrame:
            # your implementation

.. todo::

    add link to etl section

More details can be found in the   or by consulting the already provided ``Transformer``.

.. collapse:: Transformer [Show Source]

    .. literalinclude:: ../../doespy/doespy/etl/steps/transformers.py
        :language: python
        :caption: doespy/doespy/etl/steps/transformers.py

Loader
~~~~~~

The ``Loader`` steps are responsible for taking the dataframe from the transform phase and produce different representations of the results.
For example, storing results in a database, producing different plots of the data or storing a summary as a csv file.

All the ``loaders`` specified in the ETL config of the suite design, receive the resulting table (data frame) from the transform phase.

To add a custom ``Loader`` extend the ``Loader`` base class in the ``does_etl_custom`` package and implement the required methods.

.. code-block:: py

    from doespy.etl.steps.loaders import Loader

    class MyLoader(Loader):

         def load(self, df: pd.DataFrame, options: Dict, etl_info: Dict) -> None:
            # your implementation

.. todo::

    add link to etl section

More details can be found in the   or by consulting the already provided ``Loader``.

.. collapse:: Loader [Show Source]

    .. literalinclude:: ../../doespy/doespy/etl/steps/loaders.py
        :language: python
        :caption: doespy/doespy/etl/steps/loaders.py



------------

Execution
---------

We are done with configuring experiments and now want to execute them.
For this we need to move to the ``doe-suite`` folder because you interact with the DoE-Suite with a ``Makefile`` located there.

.. code-block:: sh

    cd doe-suite


You can call ``make`` or ``make help`` to see an overview of the functionality:

.. code-block:: sh

    make help

.. collapse:: Show Output

   .. command-output:: make help
      :cwd: ../..
      :shell:


..  warning::

    The DoE-Suite can easily start many instances in a remote cloud. If there is an error in the execution, or the suite finishes before all jobs are complete, then these remote resources are not terminated and can generate high costs.
    Always check that resources are terminated. We also provide the following command to ensure that the previously started instances are terminated:

    .. code-block:: sh

        make clean


To start a new suite on the default cloud, you use:

.. code-block:: sh

    make run suite=<YOUR-SUITE-DESIGN> id=new


When we start a new experiment suite, it receives a unique ID (epoch timestamp). Each experiment of the suite must have a unique name in the experiment design specification.

The playbook periodically checks whether an experiment run is finished and then downloads the results.
The variable `job_n_tries` controls the maximum number of times to check whether the job finished.
In between checking, the playbook waits for `job_check_wait_time` seconds (see `doe-suite-config/group_vars/all/main.yml`).
After the number of `job_n_tries` is exceeded, the playbook aborts.

Experiments that involve multiple instances (e.g., client-server experiment) require the experiment-suite playbook to start the next job after the previous finished. The consequence is that when the playbook aborts because `job_n_tries` is exceeded,  an already running job will continue to run on AWS, but the next job won't start unless the `experiment-suite.yml` playbook runs.

For experiments that run on a single instance, all jobs are scheduled on the instance from the beginning. As a consequence, after a job completes, the next job automatically starts even when the `experiment-suite.yml` playbook does not run. In this case, the playbook is only required to fetch results.


To continue checking a previously started experiment, we can specify the ID of the experiment when starting the playbook:

.. comment
    This will assign the suite execution a unique id, create the defined experiment environment(s), and execute all experiment jobs. After a job is finished, the DoE-Suite automatically fetches the results and places them in the directory structure under ``doe-suite-results``.

    While jobs are running, the DoE-Suite periodically connects and checks whether a job finished.
    There are two variables in ``doe-suite-config/group_vars/all/main.yml`` that control this.
    First, ``job_n_tries`` specifies how many unsuccessful attempts are allowed until we stop and
    second, ``job_check_wait_time`` specifies the delay in between tries.

    After a suite stops before all jobs are finished, we can continue the suite with:

.. code-block:: sh

    # can replace `id=last` with actual id, e.g., `id=1655831553`
    make etl suite=<YOUR-SUITE-DESIGN> id=last


After fetching new results, ETL pipelines are executed locally on your machine.
It's also possible to re-run the ETL pipelines on the result files without re-running experiments.

.. code-block:: sh

    # can replace `id=last` with actual id, e.g., `id=1655831553`
    make etl suite=<YOUR-SUITE-DESIGN> id=last


Keep Experimenting
------------------
