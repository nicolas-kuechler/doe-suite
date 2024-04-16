import jinja2
import argparse
import sys
import ruamel.yaml

from doespy import util
from doespy.design import validate
from doespy.design import extend

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

    # ignore if {{ }} is undefined
    undefined = (
        util.DebugChainableUndefined if ignore_undefined_vars else jinja2.StrictUndefined
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

    suite_design = ruamel.yaml.safe_load(suite_design)

    # validate the suite design
    prj_id = util.get_project_id()
    suite_design = validate.validate(
        suite_design, suite=suite, exp_filter=exp_filter
    )

    # output suite design
    if suite_design_dest is not None:
        with open(suite_design_dest, "w+") as f:
            ruamel.yaml.round_trip_dump(suite_design, f, default_flow_style=False, indent=2, width=10000)

    # if we only validate and not extend have early return
    if only_validate_design:
        return suite_design, None

    # extend the suite design design -> job list (resolve [% %])
    use_cmd_shellcheck = not ignore_undefined_vars
    suite_design_ext = extend.extend(suite_design, exp_specific_vars, use_cmd_shellcheck=use_cmd_shellcheck)

    # output suite design
    if suite_design_ext_dest is not None:
        with open(suite_design_ext_dest, "w+") as f:
            ruamel.yaml.round_trip_dump(suite_design_ext, f, default_flow_style=False, indent=2, width=10000)

    return suite_design, suite_design_ext



def output_design(suite_design):
    # dump to std out
    ruamel.yaml.round_trip_dump(suite_design, stream=sys.stdout, default_flow_style=False, indent=2, width=10000)



def output_commands(suite_design_ext):
    for exp, runs in suite_design_ext.items():
        print(f"\nExperiment={exp}")
        for run_idx, run in enumerate(runs):
            for host, cmds in run["$CMD$"].items():
                for host_idx, cmd in enumerate(cmds):
                    if len(cmd) == 1:
                        print(
                            f"\n  run={run_idx:03d} host={host}-{host_idx}: {cmd['main']}"
                        )
                    else:
                        print(f"  run={run_idx:03d} host={host}-{host_idx}")
                        align = max(len(x) for x in cmd.keys()) + 4

                        offset = (align - 4) * " "
                        print(f"\n{offset}main: {cmd['main']}")

                        for name, c in cmd.items():
                            if name != "main":
                                offset = (align -len(name)) * " "
                                print(f"\n{offset}{name}: {c}")


def output_etl_pipelines(suite_design):

    from doespy.etl import etl_util

    for name, etl_pipeline in suite_design["$ETL$"].items():
        if name not in ["experiments"]:
            etl_util.print_etl_pipeline(etl_pipeline, name)


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
