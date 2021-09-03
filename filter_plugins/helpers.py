from collections.abc import Iterable

def _flatten(tuple):

    for x in tuple:
        if isinstance(x, str) or not isinstance(x, Iterable):
            yield x
        else:
            yield from _flatten(x)
    

def tuple2flat2dict(tuple, keys):

    # TODO [nku] write documentation

    tuple_flat = list(_flatten(tuple))

    
    
    if len(tuple_flat) != len(keys):
        raise ValueError(f"tuple_flat length must match keys length: tuple={tuple}, tuple_flat={tuple_flat}, keys={keys}")
    
    d = {}
    for k, v in zip(keys, tuple_flat):
        d[k] = v

    return d

def tuple2dict(tuple, keys):
    
    # TODO [nku] write documentation
    
    if len(tuple) != len(keys):
        raise ValueError(f"tuple length must match keys length: tuple={tuple}, keys={keys}")
    
    d = {}
    for k, v in zip(keys, tuple):
        d[k] = v

    return d


class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            'tuple2flat2dict': tuple2flat2dict,
            'tuple2dict': tuple2dict
        }