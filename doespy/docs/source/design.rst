=================
Experiment Design
=================

.. autopydantic_model:: doespy.design.design.Suite
    :noindex:
    :validator-list-fields: True
    :model-show-field-summary: False


Experiment
==========
.. autopydantic_model:: doespy.design.design.Experiment
    :noindex:
    :validator-list-fields: True
    :field-list-validators: False

|

.. autoclass:: doespy.design.design.BaseExperiment
    :members:


Host Type
---------
.. autopydantic_model:: doespy.design.design.HostType
    :noindex:
    :validator-list-fields: True

|

.. autoenum:: doespy.design.design.HostTypeId
    :members:

|

.. autoenum:: doespy.design.design.SetupRoleId
    :members:
    :inherited-members:
    :undoc-members:



ETL Pipeline
============
.. autopydantic_model:: doespy.design.design.ETLPipeline
    :noindex:
    :validator-list-fields: True

Extractor
---------
.. autopydantic_model:: doespy.design.design.Extractor
    :noindex:
    :validator-list-fields: True


.. autoclass:: doespy.design.design.ExtractorId
    :members:
    :inherited-members:
    :undoc-members:

Transformer
-----------
.. autopydantic_model:: doespy.design.design.Transformer
    :noindex:
    :validator-list-fields: True


Loader
------
.. autopydantic_model:: doespy.design.design.Loader
    :noindex:
    :validator-list-fields: True


.. autopydantic_model:: doespy.loaders.CsvSummaryLoader
    :noindex:
    :validator-list-fields: True
