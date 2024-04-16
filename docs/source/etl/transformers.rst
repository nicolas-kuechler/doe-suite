Transformers
============

The `Transformer` stage manipulates the raw Pandas results data frame created by the `Extractor` stage.
There are two different syntax available:

- The stage can directly invoke functions defined on the data frame, see :py:class:`Pandas.DataFrameFunction`.

- The stage can invoke custom Transformer Classes, e.g., :py:class:`doespy.transformers.ConditionalTransformer`.



Pandas DF Transformers
----------------------

.. py:module:: Pandas
.. py:class:: DataFrameFunction

    Can directly call all functions defined on pandas data frames: https://pandas.pydata.org/docs/reference/frame.html
    The syntax is different from regular transformers, use ``df.*`` and replace ``*`` with the function name.
    The dictionary under ``df.*`` can be used to pass named arguments of the selected function.

    :param \*\*args: Pass argument ot the function selected with ``df.*``

    .. code-block:: yaml
       :caption: Example ETL Pipeline Design

        $ETL$:
            transformers:
                # remove all cols except
                - df.filter: {items: ["exp_name", "x", "y"]}
                # add column to df
                - df.eval: {expr: "color = 'black'"}


Conditional Replacement
-----------------------

.. autopydantic_model:: doespy.etl.steps.transformers.ConditionalTransformer
    :exclude-members: transform


Group By Aggregates
-------------------

.. autopydantic_model:: doespy.etl.steps.transformers.GroupByAggTransformer
    :exclude-members: transform, custom_tail_build
