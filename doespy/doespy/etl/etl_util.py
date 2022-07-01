
import pandas as pd


def expand_factors(df: pd.DataFrame, columns: list) -> list:
    """
    Helper method to easily include factors from experiments
    Looks for magic value `$FACTORS$` to expand into experiment factors.
    For now, it aggregates over all experiments for all factors and unionizes them.

    **Example**: Assume that `df` contains a column called `factor_columns` containing the factor column names
        [exp_factor_1, exp_factor_2]

    The following effects will happen, depending on what is contained in `columns`:
    columns: `[ col_1, col_2, $FACTORS$, col_3] --> [ col_1, col_2, exp_factor_1, exp_factor_2, col_3]` ($FACTORS$ is replaced)
    columns: `[ col_1, col_2, col_3] --> [ col_1, col_2, col_3]` (no effect as $FACTORS$ did not exist in the list)

    :param df: etl data
    :param columns: user-provided list of columns.
    :return: list with factor columns
    """
    MAGIC_KEY = '$FACTORS$'
    if MAGIC_KEY not in columns:
        return columns

    # look through dataframe and take union of all factor columns (Note: across _all_ experiments in df)
    elements = df['factor_columns'].tolist()
    flat_list = [item for sublist in elements for item in sublist]
    factors = list(set.union(set(flat_list)))

    # replace in original list at same position
    i = columns.index(MAGIC_KEY)  # This raises ValueError if there's no 'b' in the list.
    columns[i: i + 1] = factors

    # check we do not have duplicates
    assert len(columns) == len(set(columns)), f"{columns} contains duplicate values!\n" \
                                              f"If $FACTORS$ was provided as a column value, " \
                                              f"one of the other values is also contained in $FACTORS$!"

    return columns


def convert_group_name_to_str(name):
    if type(name) == str:
        return name
    elif type(name) == int or type(name) == bool:
        return str(name)
    else:
        return "_".join([f"{n}" for n in name])
