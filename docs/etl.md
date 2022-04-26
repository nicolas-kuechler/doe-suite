# ETL Processing
Instructions for defining ETL pipelines, and descriptions of base components

## Transformers
### Factor-dependent transformers
We are often interested in output differences split out by the different factor values for each run.
Instead of manually specifying what columns we are interested in, some transformers support the use of the `$FACTORS$`
tag in the ETL design files, which will automatically be expanded to the factor columns of the experiment.

The ETL pipeline provides the per-experiment factor information to the transformers in the dataframe as additional
information.
On the transformer side, the `Transformer` base class provides the `_expand_factors` helper
to automatically expand `$FACTORS$` into the right values.
An example is provided below.

```yaml
transformers:
- name: FactorAggTransformer
  data_columns:
  - accuracy
  - total_time
  factor_columns:
  - exp_name
  - audit
  - $FACTORS$ # will be expanded to factor_columns of the experiment
```

The `$FACTORS$` tag must still be explicitly provided by the experiment designer, so this functionality is entirely opt-in.

For an example, see `FactorAggTransformer`.

# Super ETL

## Config changes
- Experiments are objects now

Doe suite also supports the definition of suite-transcending (super-suite) ETL pipelines that
combines experiments from multiple suites, which we refer to as super ETL.

### Jupyter Notebook support
The below code snippet can be used to use an ETL pipeline in a notebook for quick debugging and analysis.
The ETL's loaders are skipped and instead the DataFrame is returned (that would have been processed by the loaders).
Simply call `super_etl.run_multi_suite("pipeline.yml", return_df=True)` to return the dataframe.

Full example
```jupyterpython
%env DOES_PROJECT_DIR= # place correct dir here
import sys
import os
sys.path.insert(0, os.path.abspath('doe-suite/src/scripts'))
import super_etl

df = super_etl.run_multi_suite("pipeline.yml", return_df=True)

# inspect df
```
