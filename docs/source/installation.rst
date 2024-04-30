============
Installation
============


Prerequisites
-------------

We assume that you already have an existing project available in a remote repository, e.g., GitHub, where you want to integrate the DoE-Suite.
If not, create a dummy project to work with.



**Before starting:**

* Make sure you have  `Poetry <https://python-poetry.org/docs/>`_ installed (**version >= 1.4.0**). The DoE-Suite uses Poetry to manage all required Python packages.

* Ensure you have `Cookiecutter <https://cookiecutter.readthedocs.io/en/stable/installation.html>`_ installed. Cookiecutter is a tool that helps you generate project templates, which is used by the DoE-Suite to create the necessary configuration structure.

* Verify that you can clone remote repositories with SSH. This is necessary to access your project repository from the remote experiment environment. If you need help setting up SSH for GitHub, check out the `official documentation <https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh>`_.

* (For parallel running of integration tests) Install `GNU Parallel <https://www.gnu.org/software/parallel/>`_.

AWS - Specific Prerequisites
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To run experiments on AWS, you need to create a ``key pair for AWS`` in the region ``eu-central-1``.
You can find detailed instructions on how to create a key pair in the `official AWS documentation <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/getstarted-keypair.html>`_.


Manual Inventory - Specific Prerequisites
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To run experiments using a manual inventory, you must ensure that you can connect to all the hosts with SSH.


ETHZ Euler - Specific Prerequisites
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To run experiments on ETHZ Euler, you must ensure that you can connect to ``euler.ethz.ch`` with SSH.
Check the instructions provided by ETHZ Euler for `accessing the clusters using SSH <https://scicomp.ethz.ch/wiki/Accessing_the_clusters#SSH>`_.

Docker - Specific Prerequisites
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To run experiments on (local) Docker containers, you need to have `Docker installed <https://docs.docker.com/get-docker/>`_ and running.



Base Installation
-----------------


To run the :repodir:`example designs <demo_project/doe-suite-config/designs>` of the demo project, you need to complete the steps below.


Add the DoE-Suite repository as a submodule to your project repository by running the following command from the root of your project:

.. code-block:: sh

    git submodule add git@github.com:nicolas-kuechler/doe-suite.git


Configuring SSH-Agent
~~~~~~~~~~~~~~~~~~~~~

To clone repositories on a remote instance (e.g., from GitHub) without copying the private key or entering credentials, you need to add the SSH private key for cloning repositories to ssh-agent.
The `official GitHub documentation <https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh>`_ offers detailed instructions on how to configure ssh-agent.
In principle, you need to follow these steps to configure ssh-agent in your environment:


1. Start ssh-agent in the background by running the following command in your terminal:

   .. code-block:: sh

        eval "$(ssh-agent -s)"


2. Add your SSH private key to ssh-agent. Replace `<YOUR-PRIVATE-SSH-KEY-FOR-GIT>` with the name of your private key file. Run the following command:

   .. code-block:: sh

        ssh-add ~/.ssh/<YOUR-PRIVATE-SSH-KEY-FOR-GIT>


3. On a Mac, you may also need to add your private key to the Keychain Access app.



General Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To configure your environment for the DoE-Suite, you need to set the following environment variables:

The root directory of your project repository. Later, we will expect the `does-config-dir` to be located in this folder. For now, set this variable to the absolute path of the demo project (`doe-suite/demo_project`). Run the following command in your terminal:

.. code-block:: sh
    :caption: .envrc

    # The root directory of your project repository.
    # Later, we will expect the `does-config-dir` to be located in this folder.
    # For now, replace `<PATH>` with the absolute path of the demo project,
    # i.e., (`doe-suite/demo_project`).
    export DOES_PROJECT_DIR=<PATH>


    #  Your unique short name, such as your organization's acronym or your initials.
    export DOES_PROJECT_ID_SUFFIX=<SUFFIX>


The DoE-Suite uses environment variables to enable multiple people to work on the same project together.
The ``DOES_PROJECT_ID_SUFFIX`` needs to be a unique identifier among all project collaborators to ensure that everyone working on the project can run experiments independently without interfering with each other.


..  tip::

    To make it easier to manage project-specific environment variables, you can use a tool like `Direnv <https://direnv.net/>`_. Direnv allows you to create project-specific `.envrc` files that set environment variables when you enter the project directory. This is a natural fit to use with the DoE-Suite.



AWS-Specific
------------

To run experiments on AWS, you need to complete the following steps:

AWS CLI
~~~~~~~

1. Install AWS CLI version 2 `(see instructions for AWS) <https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html>`_.

2. Configure AWS credentials for Boto `(see instructions for Boto) <https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html>`_:

    .. code-block:: sh

        aws configure

    By default, credentials should be stored in ``~/.aws/credentials``.


SSH Config (AWS)
~~~~~~~~~~~~~~~~

To configure SSH access to AWS EC2 instances, you need to add a section to your ``~/.ssh/config`` file:

.. code-block::
    :caption: ~/.ssh/config

    Host ec2*
        IdentityFile ~/.ssh/<YOUR-PRIVATE-SSH-KEY-FOR-AWS>
        User ubuntu
        ForwardAgent yes


Please replace ``<YOUR-PRIVATE-SSH-KEY-FOR-AWS>`` with the actual name of the AWS key file that you created during the :ref:`installation:AWS - Specific Prerequisites` process.
By using the pattern ``Host ec2*``, we match all AWS EC2 hosts.
Since the DoE-Suite creates new hosts on demand, it is essential to use a pattern that can match all hosts and we cannot be more restrictive.
The default user for EC2 instances that are based on Ubuntu is ubuntu.
To enable SSH agent forwarding, which is required for cloning repositories on a remote instance (such as from GitHub) without entering credentials or copying the private key, it is necessary to include the ForwardAgent yes option.


Environment Variables (AWS)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

In addition to the environment variables defined in :ref:`installation:General Environment Variables`, you need to set the following environment variable for AWS:

.. code-block:: sh

    # name of ssh key used for setting up access to aws machines
    export DOES_SSH_KEY_NAME=<YOUR-PRIVATE-SSH-KEY-FOR-AWS>

    # Replace <SSH-USERNAME> with your ssh username on the AWS instances (defaults to 'ubuntu')
    export DOES_AWS_USER=<SSH-USERNAME>

    # Note: don't forget DOES_PROJECT_DIR and DOES_PROJECT_ID_SUFFIX from above

The environment variable ``DOES_SSH_KEY_NAME`` defines the key used when creating new EC2 instances and needs to match the IdentityFile specified in the SSH config.


Check Installation (AWS)
~~~~~~~~~~~~~~~~~~~~~~~~

To ensure that your setup for AWS is configured correctly, you can test the first example ``example01-minimal`` of the :repodir:`demo project <demo_project>`.
Navigate to the ``doe-suite`` folder and run the following command:

.. code-block:: sh
    :caption: Verify that AWS installation is complete

    make test-example01-minimal cloud=aws


The test will take about ~4 minutes to complete.
It will set up an EC2 instance on AWS and run the minimal example on it.
Once the experiment completes, the results will be fetched to your local machine compared to the expected results structure found in the :repodir:`demo_project/doe-suite-results/example01-minimal_$expected <demo_project/doe-suite-results/example01-minimal_$expected/>` directory.
If the example test runs successfully, you are ready to start with the :ref:`tutorial:tutorial` for your own project.


Manuel Inventory - Specific
---------------------------



SSH Config (Inventory)
~~~~~~~~~~~~~~~~~~~~~~

To configure SSH access to all hosts listed in the inventory, you need to modify the ``~/.ssh/config`` file:

.. code-block::
    :caption: ~/.ssh/config

    Host <IP-ADDRESS or DNS>  # same as in the inventory file
        IdentityFile <YOUR-PRIVATE-SSH-KEY>
        User <YOUR-USERNAME-ON-THE-HOST>
        ForwardAgent yes


If the ssh-config is correct, you should be able to connect to the hosts listed in the inventory by running the following command:

.. code-block:: sh
    :caption: Check that you can connect to the hosts in the inventory

    ssh <HOST-NAME>


Setting up Inventory
~~~~~~~~~~~~~~~~~~~~

To run experiments using a manual inventory, you need to modify the inventory file:
:repodir:`demo_project/doe-suite-config/inventory/inv-minimal.yml <demo_project/doe-suite-config/inventory/inv-minimal.yml/>`


.. literalinclude:: ../../demo_project/doe-suite-config/inventory/inv-minimal.yml
   :language: yaml
   :caption: doe-suite-config/inventory/inv-minimal.yml


Check Installation (Inventory)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To ensure that your setup for Euler is configured correctly, you can run the first example ``example01-minimal`` of the :repodir:`demo project <demo_project>`.
Navigate to the ``doe-suite`` folder and run the following command:

.. code-block:: sh
    :caption: Verify that Euler installation is complete

    make test-example01-minimal cloud=inv-minimal


The test will connect to the host that you specified in `inv-minimal.yml` and schedule the jobs of the minimal example using the `task spooler`.
Once the experiment completes, the results will be fetched to your local machine and compared to the expected results structure found in the :repodir:`demo_project/doe-suite-results/example01-minimal_$expected <demo_project/doe-suite-results/example01-minimal_$expected/>` directory.
If the example runs successfully, you are ready to start with the :ref:`tutorial:tutorial` for your own project.



ETHZ Euler - Specific
---------------------

The `ETHZ Euler scientific computing cluster <https://scicomp.ethz.ch/wiki/Main_Page>` is an HPC cluster that uses the `Slurm <https://slurm.schedmd.com/documentation.html>` batch system to manage computing jobs.
To use the DoE-Suite to run experiments on Euler, you need to complete the following steps:

SSH Config (Euler)
~~~~~~~~~~~~~~~~~~

To configure SSH access to the Euler login node, you need to add a section to your ``~/.ssh/config`` file:

.. code-block::
    :caption: ~/.ssh/config

    Host *euler.ethz.ch
        IdentityFile <YOUR-PRIVATE-SSH-KEY-FOR-EULER>
        User <YOUR-NETHZ>
        ForwardAgent yes


Environment Variables (Euler)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In addition to the environment variables defined in :ref:`installation:General Environment Variables`, you need to set the following environment variable for Euler:

.. code-block:: sh

    # Replace <YOUR-NETHZ> with your NETHZ username
    export DOES_EULER_USER=<YOUR-NETHZ>

    # Note: don't forget DOES_PROJECT_DIR and DOES_PROJECT_ID_SUFFIX from above

The environment variable ``DOES_EULER_USER`` is required to determine the home directory.



Check Installation (Euler)
~~~~~~~~~~~~~~~~~~~~~~~~~~

To ensure that your setup for Euler is configured correctly, you can run the first example ``example01-minimal`` of the :repodir:`demo project <demo_project>`.
Navigate to the ``doe-suite`` folder and run the following command:

.. code-block:: sh
    :caption: Verify that Euler installation is complete

    make test-example01-minimal cloud=euler


The test will connect to the Euler login nodes and schedule the jobs of the minimal example in the Slurm batch system.
It typically only takes a few minutes to complete, however, the time depends on how long the jobs remain in the scheduling queue.
Once the experiment completes, the results will be fetched to your local machine and compared to the expected results structure found in the :repodir:`demo_project/doe-suite-results/example01-minimal_$expected <demo_project/doe-suite-results/example01-minimal_$expected/>` directory.
If the example runs successfully, you are ready to start with the :ref:`tutorial:tutorial` for your own project.


Docker-Specific
---------------

The  ``doe-suite`` supports running experiments on Docker containers, which can be useful for e.g., local testing.
By default we build on the `Ubuntu 20:04 LTS` Dockerfile and make small ``doe-suite`` related adjustments (e.g., make reachable via ssh).

However, you also have the option to provide a project-specific Dockerfile.
To do so, create a file named ``Dockerfile-<image_name>`` in the ``inventory/docker`` in your ``doe-suite-config`` directory,
where ``<image_name>`` corresponds to the ``docker_image_id`` in the host specific variables for the host type (see :ref:`tutorial:(Add) Host Type`).

Once this setup is complete (or you opt for the default Dockerfile), you can proceed with running experiments using Docker by following the steps below:





SSH Keys (Docker)
~~~~~~~~~~~~~~~~~

You must ensure that you can connect to all the running docker containers with SSH using a keypair.


First, ensure that the **public** key is listed in the ``authorized_keys`` folder of the Docker container.
The default docker image of the doe-suite handles this automatically, but you'll need to specify the path to the key as an environment variable (see ``DOES_DOCKER_SSH_PUBLIC_KEY`` below).
Additionally, make sure that the Docker container exposes the SSH port, which is also already done in the default docker image of the doe-suite.

You can then configure your ssh config to use the corresponding private key to connect to the Docker containers, as described in :ref:`installation:SSH Config (Docker)`.


SSH Config (Docker)
~~~~~~~~~~~~~~~~~~~

To configure SSH access to Docker instances, you need to add a section to your ``~/.ssh/config`` file:

.. code-block::
    :caption: ~/.ssh/config

    Host 0.0.0.0
        IdentityFile ~/.ssh/<YOUR-PRIVATE-SSH-KEY-FOR-DOCKER>
        User <IMAGE_USER>
        ForwardAgent yes


Please replace ``<YOUR-PRIVATE-SSH-KEY-FOR-DOCKER>`` with the actual name of the AWS key file that you used in :ref:`installation:Docker - Specific Prerequisites`.
By using the pattern ``Host 0.0.0.0``, we match all containers listening on localhost (with SSH listening to different host ports).
Since the DoE-Suite creates new hosts on demand, it is essential to use a pattern that can match all hosts and we cannot be more restrictive.
Replace <IMAGE_USER> with the user that you use in your Docker image.
For the default provided image `Ubuntu 20.04 LTS`, the user is ubuntu.
To enable SSH agent forwarding, which is required for cloning repositories on a remote instance (such as from GitHub) without entering credentials or copying the private key, it is necessary to include the ForwardAgent yes option.


Environment Variables (Docker)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In addition to the environment variables defined in :ref:`installation:General Environment Variables`, you need to set the following environment variable for Docker:

.. code-block:: sh

    export DOES_DOCKER_USER=<SSH-USERNAME>  # [optional] defaults to ubuntu
    export DOES_DOCKER_SSH_PUBLIC_KEY=<SSH-PUBLIC-KEY>  # e.g., ~/.ssh/id_rsa.pub
    export DOCKER_HOST=<DOCKER-HOST> # [optional]  defaults to unix://var/run/docker.sock

    # Note: don't forget DOES_PROJECT_DIR and DOES_PROJECT_ID_SUFFIX from above


Check Installation (Docker)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

To ensure that your setup for Docker is configured correctly, you can run the first example ``example01-minimal`` of the :repodir:`demo project <demo_project>`.
Navigate to the ``doe-suite`` folder and run the following command:

.. code-block:: sh
    :caption: Verify that Docker installation is complete

    make test-example01-minimal cloud=docker