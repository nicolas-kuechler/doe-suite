import argparse
from doespy.etl import etl_base

from doespy import util


def main():

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--suite", type=str, required=False)
    parser.add_argument("--id", type=str, required=False)
    parser.add_argument("--all", action="store_true", required=False)

    # by setting the --load_from_design flag, we can make the etl pipeline be run using
    # # the etl definition in `doe-suite-config/designs`
    # rather than the on in the results directory
    parser.add_argument(
        "--load_from_design",
        action="store_true",
        help="Use the pipelines from doe-suite-config/designs or suite_design.yml",
    )

    parser.add_argument("--output_path", type=str, required=False)

    args = parser.parse_args()

    # ensure that exactly one of --all or (--suite and --id) are set
    if not (
        (args.all and args.id is None and args.suite is None)
        or (not args.all and args.id is not None and args.suite is not None)
    ):
        parser.error(
            "either --all or --suite and --id are required but both are not possible"
        )

    if args.suite is not None and args.id is not None:

        etl_base.run_single_suite(
            suite=args.suite,
            suite_id=args.id,
            etl_output_dir=args.output_path,
            etl_from_design=args.load_from_design
        )

    elif args.all:
        for x in util.get_does_results():
            etl_base.run_single_suite(
                suite=x["suite"],
                suite_id=x["suite_id"],
                etl_output_dir=args.output_path,
                etl_from_design=args.load_from_design
            )
    else:
        raise ValueError(
            "the xor between the options should ensure that this cannot be the case"
        )


if __name__ == "__main__":
    main()
