import argparse
from doespy.etl import etl_base
from doespy import util


def main():

    # TODO [nku] validate the super-etl design with pydantic?

    # TODO [nku] allow for super-etl to be located in a different directory? -> specifically, the results of the super-etl should be in the same directory as the super-etl config

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument(
        "--output_path",
        type=str,
        default=util.get_super_etl_output_dir(),
        required=False,
    )
    parser.add_argument(
        "--output_dir_config_name_disabled",
        action="store_true",
        help="Whether to output in a subdir with the name of the super_etl config.",
    )
    parser.add_argument(
        "--output_dir_pipeline",
        action="store_true",
        help="Whether to output in a subdir with the name of the pipeline.",
    )

    parser.add_argument(
        "--load_from_design",
        action="store_true",
        help="Use the pipelines from doe-suite-config/designs or suite_design.yml",
    )


    parser.add_argument(
        "--pipelines",
        nargs="+",
        required=False,
        help="ETL super pipelines to run. If not specified, all pipelines will be run.",
    )

    args = parser.parse_args()

    etl_base.run_multi_suite(
        super_etl=args.config,
        etl_output_dir=args.output_path,
        flag_output_dir_config_name=not args.output_dir_config_name_disabled,
        flag_output_dir_pipeline=not args.output_dir_pipeline,
        etl_from_design=args.load_from_design,
        pipeline_filter=args.pipelines,
        return_df=False,
    )


if __name__ == "__main__":
    main()
