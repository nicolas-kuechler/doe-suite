import argparse
import os
import shutil


from doespy import util


def main():

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--suite", type=str, required=False)
    parser.add_argument("--id", type=str, required=False)
    parser.add_argument("--all", action="store_true", required=False)

    parser.add_argument("--output", type=str, default="etl_results", required=False)

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
        run(suite=args.suite, suite_id=args.id, etl_output_dir=args.output)
    elif args.all:
        for x in util.get_does_results():
            run(suite=x["suite"], suite_id=x["suite_id"], etl_output_dir=args.output)
    else:
        raise ValueError(
            "the xor between the options should ensure that this cannot be the case"
        )


def run(suite, suite_id, etl_output_dir):
    etl_results_dir = util.get_etl_results_dir(suite, suite_id, etl_output_dir)

    print(
        f"Deleting etl results for suite={suite}  id={suite_id} (dir={etl_results_dir})"
    )
    if os.path.isdir(etl_results_dir):
        shutil.rmtree(etl_results_dir, ignore_errors=False)


if __name__ == "__main__":
    main()
