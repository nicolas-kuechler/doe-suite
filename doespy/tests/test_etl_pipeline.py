import os, shutil
from distutils.dir_util import copy_tree

from doespy import util
from doespy.etl import etl
from doespy.comp import dircomp

def check_suite_etl_pipelines(suite, suite_id):

    """runs the etl pipelines of the suite and compares the results with the existing results
    """

    ETL_OUTPUT_DIR = "$tmp_etl_results"

    src = util.get_etl_results_dir(suite=suite, id=suite_id)

    results_dir, etl_results = os.path.split(src)

    dest = os.path.join(results_dir, ETL_OUTPUT_DIR)

    # run the etl on the copy
    etl.run(suite_id=suite_id, suite=suite, use_etl_from_design=False, etl_output_dir=ETL_OUTPUT_DIR)

    if os.path.isdir(src):
        # only compare if the src directory exists
        is_same = dircomp.compare_dir(src, dest, ignore_infiles=[])
        assert is_same

    # delete the newly created etl folder (not created if no etl pipeline exists)
    if os.path.isdir(dest):
        shutil.rmtree(dest, ignore_errors=False)


def test_etl_pipelines():
    for x in util.get_does_results():
        if "$expected" != x["suite_id"]:
            print(f"Checking suite {x['suite']}  with id {x['suite_id']}")
            check_suite_etl_pipelines(suite=x["suite"], suite_id=x["suite_id"])