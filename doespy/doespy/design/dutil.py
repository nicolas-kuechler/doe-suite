from collections import abc

def nested_dict_iter(nested, path=[]):
    for key, value in nested.items():
        path_c = path + [key]

        if isinstance(value, abc.Mapping):
            yield from nested_dict_iter(value, path=path_c)
        else:
            yield path_c, value


def set_nested_value(base, path, value, overwrite=False):

    is_value_included = False

    d = base
    for i, k in enumerate(path):

        if k not in d:
            if i == len(path) - 1:  # last
                d[k] = value
                is_value_included = True
            else:
                d[k] = {} #
        elif overwrite and i == len(path) - 1:  # last + overwrite
            d[k] = value
            is_value_included = True

        d = d[k]
    return is_value_included

def include_vars(base, vars):

    skipped = []
    included = []

    for path, value in nested_dict_iter(vars):
        is_value_included = set_nested_value(base, path, value)
        info_str = f"{'.'.join(['d'] + path)}: {value}"
        if is_value_included:
            included.append(info_str)
        else:
            skipped.append(info_str)

    return skipped, included