

def collect_items2dict(lst, key_name):

    d = {}

    for x in lst:
        if key_name not in x:
            raise ValueError(f"missing key_name={key_name} in {x}")
        
        key = x[key_name]
        if key in d:
            raise ValueError(f"duplicate key={key}")
        
        d[key] = x
    
    return d

class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            'collect_items2dict': collect_items2dict,
        }