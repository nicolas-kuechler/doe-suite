import os

from doespy import util
from doespy.comp import dircomp
from pytest import fixture



# poetry run pytest -q -s --suite example02-single --id 1655195952 --idref 1655196349

# compares with expected:
# poetry run pytest -q -s --suite example02-single --id 1655195952
def test_suite_result(suite, suite_id, suite_idref="$expected"):
    if suite_id == "last":
        suite_id = util.get_last_suite_id(suite)
    results_dir = util.get_results_dir()
    d1 = os.path.join(results_dir, util.get_folder(suite=suite, suite_id=suite_id))
    d2 = os.path.join(results_dir, util.get_folder(suite=suite, suite_id=suite_idref))


    suite_idref = r"{}".format(suite_idref.replace("$", r"\$")) # r"\$expected"
    path_pattern = r"\/.*\/demo_project" # we need to ignore the path to the demo project because it is different between euler and aws (+ on euler person dependent)
    job_finished_order= r"^exp_job_ids_finished: \[.*\]$" # on euler jobs can finish in different order
    aws_ec2_host_ids = r" ip-[0-9a-z.-]*internal " # ip can change


    print(f"Comparing folders:\n   {d1}\nwith:\n   {d2}")
    is_same = dircomp.compare_dir(d1, d2, ignore_infiles=[suite_id, suite_idref, path_pattern, job_finished_order, aws_ec2_host_ids], ignore_files=["stdout.log"])
    assert is_same


# configuration of pytest arguments
@fixture(scope="session")
def suite(request):
    return request.config.getoption("--suite")

@fixture(scope="session")
def suite_id(request):
    return request.config.getoption("--id")

@fixture(scope="session")
def suite_idref(request):
    return request.config.getoption("--idref")