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
    print(f"Comparing folders:\n   {d1}\nwith:\n   {d2}")
    is_same = dircomp.compare_dir(d1, d2, ignore_infiles=[suite_id, suite_idref])
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