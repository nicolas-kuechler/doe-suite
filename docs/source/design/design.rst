=================
Experiment Design
=================

.. autopydantic_model:: doespy.design.exp_design.Suite
    :validator-list-fields: True
    :model-show-field-summary: False

|

.. autopydantic_model:: doespy.design.exp_design.SuiteVarsConfigDict
    :inherited-members: BaseModel
    :validator-list-fields: True
    :model-show-field-summary: False
    :model-show-validator-members: True

Experiment
==========

.. autopydantic_model:: doespy.design.exp_design.Experiment
    :validator-list-fields: True
    :field-list-validators: False
    :model-show-field-summary: False
    :model-show-validator-members: True



.. autoclass:: doespy.design.exp_design.BaseExperimentConfigDict
    :members:


Host Type
---------
.. autopydantic_model:: doespy.design.exp_design.HostType
    :validator-list-fields: True

|

.. autoenum:: doespy.design.exp_design.HostTypeId
    :members:

|

.. autoenum:: doespy.design.exp_design.SetupRoleId
    :members:
    :inherited-members:
    :undoc-members:


ETL Pipeline
============
.. autopydantic_model:: doespy.design.etl_design.ETLPipeline
    :validator-list-fields: True

Extractor
---------
.. autopydantic_model:: doespy.design.etl_design.Extractor
    :validator-list-fields: True


.. autoclass:: doespy.design.etl_design.ExtractorId
    :members:
    :inherited-members:
    :undoc-members:

Transformer
-----------
.. autopydantic_model:: doespy.design.etl_design.Transformer
    :validator-list-fields: True


Loader
------
.. autopydantic_model:: doespy.design.etl_design.Loader
    :validator-list-fields: True
