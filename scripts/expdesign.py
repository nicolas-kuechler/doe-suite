import yaml, itertools, os, collections, argparse

def main():

    parser = argparse.ArgumentParser(description='Transform experiment definition in table form into design form required by the experiment suite')

    parser.add_argument('--suite', help='experiment suite name', type=str)

    parser.add_argument('--exps', help='experiment name(s) (experiment file name without .yml ending)', nargs="+", type=str, required=True)

    parser.add_argument('--inputdir', help='path to folder of experiment in "table" form', type=str, default="experiments/table")

    parser.add_argument('--outpath', help='output path for generated of experiment in "design" form', type=str)

    args = parser.parse_args()

    suite   = args.suite
    inputdir    = args.inputdir
    outpath     = args.outpath
    exps        = args.exps

    if not suite:
        suite = exps[0]

    if not outpath:
        outpath = f"experiments/designs/{suite}.yml"

    with open(outpath, 'w') as out_fp:
        print(f"Writing experiment design to: {outpath}\n")

        out_fp.write(f"# AUTOGENERATED FROM {inputdir}/{{{', '.join(exps)}}}.yml WITH build_config_product(...)\n\n\n")

        experiments = []
        for exp in exps:
            infile = os.path.join(inputdir, f"{exp}.yml")
            if not os.path.isfile(infile):
                raise ValueError(f"input experiment file not found: {infile}")

            experiment_yml = build_config_product(infile)
            experiments.append({exp: experiment_yml})

        experiments_yml = {"experiments": experiments}
        yaml.dump(experiments_yml, out_fp, sort_keys=False)


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


def build_config_product(infile):

    """Converts an experiment config in `table` form (concise) into the experiment design form required for the experiment suite.

        The function builds a cartesian product of all configuration options marked as `$FACTOR$` with a list of levels.

        The experiment in table form is a yaml file.
        Each factor of the experiment is a yaml object with a single entry with key `$FACTOR$` and as a value the list of levels.

        Example:
            [...] # General config (omitted, see examples)
            base_experiment:
                abc:
                  $FACTOR$: ['v1', 'v2']
                xyz:
                  $FACTOR$: [1,2,3]

        Given this example, the function creates an experiment design with 6 runs (all combinations of levels of the two factors).
        In each run, the config options `abc` and `xyz`take a concrete value (level) from the list.

        Parameters:
        infile: the location where the experiment in table form is placed

        Returns:
        a dict with the experiment design


    """

    with open(infile, 'r') as f:
        exp_table = yaml.load(f, Loader=yaml.SafeLoader)

    base_experiment = {}

    factors = []

    for k, v, path in _nested_dict_iter(exp_table['base_experiment']):

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
    exp_design = exp_table
    exp_design["base_experiment"] = base_experiment
    exp_design["factor_levels"] = factor_levels

    return exp_design

if __name__ == "__main__":
    main()
