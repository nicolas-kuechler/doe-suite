import jinja2
import yaml
import argparse

from doespy import util
from doespy.design import validate, extend


def main(
    suite,
    design_files_dir=util.get_suite_design_dir(),
    only_validate_design=False,
    exp_filter=None,
    suite_design_dest=None,
    suite_design_ext_dest=None,
    template_vars={},
    exp_specific_vars={},
    ignore_undefined_vars=False,
):

    dirs = {
        "designvars": util.get_suite_design_vars_dir(),
        "groupvars": util.get_suite_group_vars_dir(),
        "roles": util.get_suite_roles_dir(),
    }

    # ignore if {{ }} is undefined
    undefined = (
        jinja2.DebugUndefined if ignore_undefined_vars else jinja2.StrictUndefined
    )

    # load suite design and apply templating (resolve {{ }} in design)
    env = util.jinja2_env(
        loader=jinja2.FileSystemLoader(design_files_dir), undefined=undefined
    )
    template = env.get_template(f"{suite}.yml")
    suite_design = template.render(**template_vars)

    if not ignore_undefined_vars:
        while "{{" in suite_design and "}}" in suite_design:
            template = env.from_string(suite_design)
            suite_design = template.render(**template_vars)

    suite_design = yaml.load(suite_design, Loader=UniqueKeyLoader)

    # validate the suite design
    prj_id = util.get_project_id()
    suite_design = validate.validate(
        suite_design, prj_id=prj_id, suite=suite, dirs=dirs, exp_filter=exp_filter
    )

    # output suite design
    if suite_design_dest is not None:
        with open(suite_design_dest, "w+") as f:
            yaml.dump(suite_design, f, sort_keys=False, width=10000)

    # if we only validate and not extend have early return
    if only_validate_design:
        return suite_design, None

    # extend the suite design design -> job list (resolve [% %])
    suite_design_ext = extend.extend(suite_design, exp_specific_vars)

    # output suite design
    if suite_design_ext_dest is not None:
        with open(suite_design_ext_dest, "w+") as f:
            yaml.dump(suite_design_ext, f, sort_keys=False, width=10000)

    return suite_design, suite_design_ext


def output_design(suite_design):
    s = yaml.dump(suite_design, sort_keys=False, width=10000)
    print(s)


def output_commands(suite_design_ext):
    for exp, runs in suite_design_ext.items():
        print(f"Experiment={exp}")
        for run_idx, run in enumerate(runs):
            for host, cmds in run["$CMD$"].items():
                for host_idx, cmd in enumerate(cmds):
                    if len(cmd) == 1:
                        print(
                            f"  run={run_idx:03d} host={host}-{host_idx}: {cmd['main']}"
                        )
                    else:
                        raise ValueError("not implemented yet")


def output_etl_pipelines(suite_design):

    from doespy.etl import etl_util

    for name, etl_pipeline in suite_design["$ETL$"].items():
        if name not in ["experiments"]:
            etl_util.print_etl_pipeline(etl_pipeline, name)


class UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        mapping = []
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise AssertionError(f"duplicate key={key}")
            mapping.append(key)
        return super().construct_mapping(node, deep)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--suite", type=str, required=True)

    parser.add_argument("--expfilter", type=str)

    parser.add_argument("--out-design", type=str)
    parser.add_argument("--out-design-ext", type=str)

    parser.add_argument("--only-validate", action="store_true")

    parser.add_argument("--ignore-undefined-vars", action="store_true")

    args = parser.parse_args()

    suite_design, suite_design_ext = main(
        suite=args.suite,
        only_validate_design=args.only_validate,
        exp_filter=args.expfilter,
        suite_design_dest=args.out_design,
        suite_design_ext_dest=args.out_design,
        ignore_undefined_vars=args.ignore_undefined_vars,
    )

    from pyfiglet import figlet_format

    if not args.only_validate:
        print(figlet_format("Run Commands", font="small"))
        output_commands(suite_design_ext)
    else:
        print(figlet_format("Design", font="small"))
        output_design(suite_design)

    print("\n")
    print(figlet_format("ETL", font="small"))
    output_etl_pipelines(suite_design)
