============
Installation
============


Prerequisites
-------------

We assume that you already have an existing project for which you want to run benchmarks with DoES (otherwise, just create a dummy project).

**Before starting:**

* Ensure that you have `Poetry <https://python-poetry.org/docs/>`_ installed.

* Ensure that you have `Cookiecutter <https://cookiecutter.readthedocs.io/en/stable/installation.html>`_ installed.

* Ensure you can clone remote repositories with SSH `(see instructions for GitHub) <https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh>`_.


AWS - Specific Prerequisites
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Create a ``key pair for AWS`` in the region ``eu-central-1`` `(see instructions for AWS Keypair) <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/getstarted-keypair.html>`_.


ETHZ Euler - Specific Prerequisites
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Ensure that you can connect to ``euler.ethz.ch`` with ssh `(see instructions for Euler) <https://scicomp.ethz.ch/wiki/Accessing_the_clusters#SSH>`_.


Base Installation
-----------------

After this section, it should be possible to run the example designs of the demo project.
For example:

.. code-block:: sh

    make run suite=example01-minimal id=new


First, add the DoES repository as a submodule to your project repository.

.. code-block:: sh

    git submodule add git@github.com:nicolas-kuechler/doe-suite.git


Configuring SSH-Agent
~~~~~~~~~~~~~~~~~~~~~

Afterward, configure ``ssh-agent`` - add the private key for cloning repositories to ssh-agent.
This allows cloning a repository (e.g., on GitHub) on an remote instance without copying the private key or entering credentials.
The process depends on your environment but should be as follows `(source) <https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh>`_

* Start ssh-agent in the background:

.. code-block:: sh

    eval "$(ssh-agent -s)"

* Add SSH private key to ssh-agent (replace with your key):

.. code-block:: sh

    ssh-add ~/.ssh/<YOUR-PRIVATE-SSH-KEY-FOR-GIT>

* (On a MAC, need to add to keychain)


General Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finally, set the environment variables listed below.

.. code-block:: sh

    # the root of your project repository, later we expect does-config-dir in this folder
    # !!! For now set to absolute path of demo project: `doe-suite/demo_project`
    export DOES_PROJECT_DIR=<PATH>

    # your unique shortname, e.g., nku
    export DOES_PROJECT_ID_SUFFIX=<SUFFIX>

..  tip::

    `Direnv <https://direnv.net/>`_ allows project-specific env vars in an `.envrc` file and is a natural fit to use with the DoE-Suite.


AWS-Specific
------------

AWS CLI
~~~~~~~

Install AWS CLI version 2 `(see instructions for AWS) <https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html>`_.

Configure AWS credentials for Boto `(see instructions for Boto) <https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html>`_:

.. code-block:: sh

    aws configure

By default, credentials should be in ``~/.aws/credentials``.


SSH Config (AWS)
~~~~~~~~~~~~~~~~

Configure SSH Config - add a section for EC2 instances:

.. code-block::
    :caption: ~/.ssh/config

    Host ec2*
        IdentityFile ~/.ssh/<YOUR-PRIVATE-SSH-KEY-FOR-AWS>
        User ubuntu
        ForwardAgent yes


Environment Variables (AWS)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add an additional environment variable:

.. code-block:: sh

    # name of ssh key used for setting up access to aws machines
    export DOES_SSH_KEY_NAME=<YOUR-PRIVATE-SSH-KEY-FOR-AWS>

    # Note: don't forget DOES_PROJECT_DIR and DOES_PROJECT_ID_SUFFIX from above



Check Installation (AWS)
~~~~~~~~~~~~~~~~~~~~~~~~

You can check that the ``example01-minimal.yml`` of the ``demo_project`` runs in your setup.
In the ``doe-suite`` repository, run the command below to run the example on AWS:

.. code-block:: sh
    :caption: Verify that AWS installation is complete

    make test-example01-minimal cloud=aws



ETHZ Euler - Specific
---------------------

SSH Config (Euler)
~~~~~~~~~~~~~~~~~~

Configure SSH Config - add a section for the Euler login node:

.. code-block::
    :caption: ~/.ssh/config

    Host *euler.ethz.ch
        IdentityFile <YOUR-PRIVATE-SSH-KEY-FOR-EULER>
        User <YOUR-NETHZ>
        ForwardAgent yes


Environment Variables (Euler)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add an additional environment variable:

.. code-block:: sh

    # for eth euler cluster: your nethz account
    export DOES_EULER_USER=<YOUR-NETHZ>

    # Note: don't forget DOES_PROJECT_DIR and DOES_PROJECT_ID_SUFFIX from above


Check Installation (Euler)
~~~~~~~~~~~~~~~~~~~~~~~~~~

Check that the ``example01-minimal.yml`` of the ``demo_project`` runs in your setup.
In the ``doe-suite`` repository, run the command below to run the example on Euler:

.. code-block:: sh
    :caption: Verify that Euler installation is complete

    make test-example01-minimal cloud=euler
