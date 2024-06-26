Extractors
==========

The `Extractor` stage processes files generated by experiment jobs and creates a Pandas data frame.
Each file needs to be assigned to exactly one `Extractor` by setting the `file_regex` field.
The provided extractors provide reasonable defaults that can be adjusted for specific use cases.


Yaml Files
----------

.. autopydantic_model:: doespy.etl.steps.extractors.YamlExtractor
    :exclude-members: extract

Json Files
----------

.. autopydantic_model:: doespy.etl.steps.extractors.JsonExtractor
    :exclude-members: extract


Csv Files
---------

.. autopydantic_model:: doespy.etl.steps.extractors.CsvExtractor
    :exclude-members: extract


Raising Attention to Errors
---------------------------

.. autopydantic_model:: doespy.etl.steps.extractors.ErrorExtractor
    :exclude-members: extract


Ignoring Result Files
---------------------

.. autopydantic_model:: doespy.etl.steps.extractors.IgnoreExtractor
    :exclude-members: extract