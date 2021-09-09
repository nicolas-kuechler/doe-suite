import yaml

def _add_default(d, keys, attr, default):
    """
    Recursive function to add { attr: default } (if not present) to the dictionary
    at the end of the wildcard query keys.
    """
    if len(keys) == 0:
        d.setdefault(attr, default)
    else:
        key = keys[0]
        keys = keys[1:]

        if key != "*":
            if not isinstance(d, dict):
                raise ValueError(f"Received wrong type: '{d}' is not a dictionary")
            elif key not in d:
                raise ValueError(f"Query contains invalid key '{key}' not in '{d}'")
            _add_default(d[key], keys, attr, default)
        else:
            if isinstance(d, dict):
                for key in d.keys():
                    _add_default(d[key], keys, attr, default)
            else:
                for elem in d:
                    _add_default(elem, keys, attr, default)

def dict_default(d, query, attr, default):
    """
    Set a default value for a dictionary at the specified query.

    The query supports the wildcard character '*' and expects dot notation (i.e., d.plants and not d['plants']).
    The wildcard tolerates lists.

    # Example usage:

    ## Dictionary
    data = {
        "animals": {
            "cats": 10,
            "dogs": 1
        }
        "plants": {
            "bushes": 2,
            "pot plants": 3
        }
    }

    ## Example 1

    Set a default for the plants "cacti":
    {{ data | dict_default("plants", "cacti", 0) }}

    Results in the new dictionary:
    data = {
        "animals": {
            "cats": 10,
            "dogs": 1
        }
        "plants": {
            "bushes": 2,
            "pot plants": 3,
            "cacti": 0
        }
    }

    ## Example 2

    Set a default category "other" for all entries if its not present:
    {{ data | dict_default("*", "other", 0) }}

    Results in the new dictionary:
    data = {
        "animals": {
            "cats": 10,
            "dogs": 1,
            "other": 0
        }
        "plants": {
            "bushes": 2,
            "pot plants": 3,
            "other": 0
        }
    }

    # Remarks

    Note that this filter can only add key/value pairs to an existing dictionaries:
    - WRONG: {{ data | dict_default("plants.house", "cacti", 0) }} because data["plants"] does not contain a dictionary for key "house".
    - CAREFUL: {{ data | dict_default("plants", "house.cacti", 0) }} adds the entry "house.cacti": 0. It does NOT add a dictionary under key "house" with the entry "cacti": 0
    """

    keys = query.split(".")
    _add_default(d, keys, attr, default)

    return d



def validate_yaml(file):
    class UniqueKeyLoader(yaml.SafeLoader):
        def construct_mapping(self, node, deep=False):
            mapping = []
            for key_node, value_node in node.value:
                key = self.construct_object(key_node, deep=deep)
                if key in mapping:
                    raise AssertionError(f"duplicate key={key}")
                mapping.append(key)

            return super().construct_mapping(node, deep)

    try:
        with open(file) as f:
            x = yaml.load(f, Loader=UniqueKeyLoader)
    except AssertionError as e:
        return False

    
    return True




class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            'dict_default': dict_default,
            'validate_yaml': validate_yaml,
        }
