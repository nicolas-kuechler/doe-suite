import yaml, itertools, os, collections, argparse

def main():

    parser = argparse.ArgumentParser(description='Transform experiment definition in table form into design form required by the experiment suite')

    parser.add_argument('--exp', help='experiment name (experiment file name without .yml ending)', type=str, required=True)

    parser.add_argument('--rep', help='number of repetitions of each experiment run', type=int, required=True)

    parser.add_argument('--inputdir', help='path to folder of experiment in "table" form', type=str, default="experiments/table")

    parser.add_argument('--outdir', help='path to folder of experiment in "design" form', type=str, default="experiments/designs")

    args = parser.parse_args()


    infile = os.path.join(args.inputdir, f"{args.exp}.yml")
    if not os.path.isfile(infile):
        raise ValueError(f"input experiment file not found: {infile}")

    build_config_product(exp_name=args.exp, n_repetitions=args.rep, input_dir=args.inputdir, output_dir=args.outdir)


def _nested_dict_iter(nested, p=[]):
    for key, value in nested.items():
        if isinstance(value, collections.abc.Mapping):
            yield from _nested_dict_iter(value, p=p + [key])
        else:
            yield key, value, p

def _insert_config(config, key, parent_path, value):
    d = config
    for k in parent_path:
        if k not in d:
            d[k] = {}
        d = d[k]
    d[key] = value
    

def build_config_product(exp_name, n_repetitions, input_dir="experiments/table", output_dir="experiments/designs"):
    
    """Converts an experiment config in `table` form (concise) into the experiment design form required for the experiment suite. 
        
        The function builds a cartesian product of all configuration options marked as `$FACTOR$` with a list of levels.
        
        The experiment in table form is a yaml file (with name `<exp_name>.yml` in `<input_dir>`).
        Each factor of the experiment is a yaml object with a single entry with key `$FACTOR$` and as a value the list of levels.
        
        Example:
            abc:
              $FACTOR$: ['v1', 'v2']
            xyz:
              $FACTOR$: [1,2,3]
            
        Given this example, the function creates an experiment design with 6 runs (all combinations of levels of the two factors). 
        In each run, the config options `abc` and `xyz`take a concrete value (level) from the list. 
        
        Parameters:
        exp_name: the (unique) name of the experiment
        n_repetitions: how many times to repeat each run with a specific config
        input_dir: the location where the experiment in table form is placed
        output_dir: the location where the experiment in the design form for the experiment suite is placed
        
        Returns:
        a dict with the experiment design
        
    
    """
    
    with open(os.path.join(input_dir, f"{exp_name}.yml"), 'r') as f:
        d = yaml.load(f, Loader=yaml.SafeLoader)
    
    base_experiment = {}

    factors = []

    for k, v, path in _nested_dict_iter(d):
        
        # k: the key (i.e. the name of the config option, unless it's a factor, than the content is just $FACTOR$)
        # v: the value or a list of levels in case it's a factor
        # path: to support nested config dicts, path keep tracks of all the parent nodes of k (empty if it is on the top level)

        if k == "$FACTOR$":

            levels = v
            
            # because of the specicial format of a factor where the key is always $FACTOR$, we need to look at the parent to see the name of the factor (xyz: $FACTOR$: [1,2,3])
            factor = path[-1]
            parent_path = path[:-1]

            # factor in experiment -> need to put placeholder `$FACTOR$` in base_experiment
            _insert_config(base_experiment, key=factor, parent_path=parent_path, value="$FACTOR$")

            
            # loop over the levels and for each level add an entry with the "factor name" and the path to this factor
            factor_levels = []
            for level in levels:
                factor_levels.append((factor, level, parent_path))
            factors.append(factor_levels)        

        else:
            # constant config value (over experiment runs)
            _insert_config(base_experiment, key=k, parent_path=path, value=v)

    factor_levels = []
    
    # create a cross product of all factors with their respective levels
    for factor_levels_raw in itertools.product(*factors):
        # loop over the different factors and put their level for the run in a dict d
        d = {}
        for k, v, path in factor_levels_raw:
            _insert_config(d, key=k, parent_path=path, value=v)
        factor_levels.append(d)

    # build the final exp config design
    experiment = {
        "n_repetitions": n_repetitions,
        "base_experiment": base_experiment,
        "factor_levels": factor_levels
    }

    exp_design_file = os.path.join(output_dir, f'{exp_name}.yml')

    print(f"Writing experiment design to: {exp_design_file}\n")
    # write exp config design file
    with open(exp_design_file, 'w') as file:

        file.write(f"# AUTOGENERATED FROM {input_dir}/{exp_name}.yml WITH build_config_product(...) \n\n\n")
        yaml.dump(experiment, file, sort_keys=False)
        
    return experiment

if __name__ == "__main__":
    main()