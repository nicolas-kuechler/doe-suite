from collections.abc import Iterable

def _flatten(tuple):

    for x in tuple:
        if isinstance(x, str) or not isinstance(x, Iterable):
            yield x
        else:
            yield from _flatten(x)
    

def tuple2flat2dict(tuple, keys):
    """
    first flattens a nested tuple and then converts the flat tuple to a dict by using the provided keys
    
    tuple: potentially nested tuple
    keys: list of keys to use in output dictionary 

    Example: tuple=(0, (1, 2)) keys=["a", "b", "c"] -> {"a": 0, "b": 1, "c": 2}
    """

    tuple_flat = list(_flatten(tuple))

    
    if len(tuple_flat) != len(keys):
        raise ValueError(f"tuple_flat length must match keys length: tuple={tuple}, tuple_flat={tuple_flat}, keys={keys}")
    
    d = {}
    for k, v in zip(keys, tuple_flat):
        d[k] = v

    return d

def tuple2dict(tuple, keys):
    """
    converts the tuple to a dict by using the provided keys (without flattening)
    
    tuple: potentially nested tuple
    keys: list of keys to use in output dictionary 

    Example: tuple=(0, (1, 2)) keys=["a", "b"] -> {"a": 0, "b": (1,2)}
    """
    
    if len(tuple) != len(keys):
        raise ValueError(f"tuple length must match keys length: tuple={tuple}, keys={keys}")
    
    d = {}
    for k, v in zip(keys, tuple):
        d[k] = v

    return d

def collect_items2dict(lst, key_name, multiset=False):

    """
    group by the `lst` by the value at `key_name`

    lst: list of dictionaries
    key_name: a key that appears on the top level of every dictionary in `lst`
    multiset: bool indicating whether lst contains multiple entries with the same key (key is not unique)

    return: a dict that "collects" the dicts in the lst by their value at key_name


    Example: [{"a": "test0", ...},{"a": "test1", ...}, ...] and key_name="a" -> {"test0": {"a": "test0"}, ...}
    
    """

    d = {}

    for x in lst:
        if key_name not in x:
            raise ValueError(f"missing key_name={key_name} in {x}")
        
        key = x[key_name]

        if multiset:

            if key not in d:
                d[key] = []
            d[key].append(x)
            
        else:
            
            if key in d:
                raise ValueError(f"duplicate key={key}")
            
            d[key] = x
    
    return d


class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            'tuple2flat2dict': tuple2flat2dict,
            'tuple2dict': tuple2dict,
            'collect_items2dict': collect_items2dict,
        }