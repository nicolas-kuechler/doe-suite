==========
ETL Design
==========

This section outlines the design of the ETL framework.
The ETL pipeline is always **executed locally** following the retrieval of result data from the remote experiment environment.

In essence, it presents a structured methodology for constructing visualizations and conducting analyses based on the raw result data stored within the `doe-suite-results` directory.

An ETL pipeline can be defined as part of the suite design (see `demo_project/doe-suite-config/designs`), wherein it is automatically executed whenever new results are obtained, or as part of a super ETL (see `demo_project/doe-suite-config/super_etl`), which is triggered manually on demand.


The ETL pipeline comprises three stages:

1. **Extractor Stage**: Here, the directory structure of the `doe-suite-results` directory is traversed, and the raw result data is aggregated into a single Pandas dataframe.
Each extractor is equipped with a regex pattern designed to match the filenames of the raw result data files.

2. **Transformer Stage**: This stage processes the dataframe obtained from the extractor stage.
Each transformer step is a function that accepts the dataframe as input and returns a modified dataframe, which is subsequently passed to the next transformer step.

3. **Loader Stage**: Serving as the final stage of the ETL pipeline, it is tasked with generating visualizations or persisting the processed data to disk.
Each loader operates on the resulting dataframe from the transformer stage.

We provide a collection of default extractors, transformers, and loaders that are common building blocks of ETL pipelines.
However, it's possible to define project-specific steps to implement custom functionality (see `demo_project/doe-suite-config/does_etl_custom`).

Below we provide an overview of the default extractors, transformers, and loaders.

.. toctree::
    :maxdepth: 2

    extractors
    transformers
    loaders
