
import pandas as pd

def expand_factors(df: pd.DataFrame, factor_columns: list) -> list:
    """
    Helper method to easily include factors from experiments
    Looks for magic value `$FACTORS$` to expand into experiment factors.
    For now, it aggregates over all experiments for all factors and unionizes them.

    :param df: etl data
    :param factor_columns: user-provided list of factor columns.
    :return: list with factor columns
    """
    MAGIC_KEY = '$FACTORS$'
    if MAGIC_KEY not in factor_columns:
        return factor_columns

    # look through dataframe and take union of all factor columns (Note: across _all_ experiments in df)
    elements = df['factor_columns'].tolist()
    flat_list = [item for sublist in elements for item in sublist]
    factors = list(set.union(set(flat_list)))

    # replace in original list at same position
    i = factor_columns.index(MAGIC_KEY)  # This raises ValueError if there's no 'b' in the list.
    factor_columns[i: i +1] = factors
    return factor_columns