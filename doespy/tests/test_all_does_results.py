import os

from doespy import util
from doespy.comp import dircomp
import pytest

def generate_test_cases():
    test_cases = [(x["suite"], x["suite_id"]) for x in util.get_all_suite_results_dir() if not x["suite_id"].startswith("$")]

    return test_cases


@pytest.mark.parametrize("suite, suite_id", generate_test_cases())
def test_suite_result(suite, suite_id, suite_idref="$expected"):

    results_dir = util.get_results_dir()
    d1 = os.path.join(results_dir, util.get_folder(suite=suite, suite_id=suite_id))
    d2 = os.path.join(results_dir, util.get_folder(suite=suite, suite_id=suite_idref))

    suite_idref = r"{}".format(suite_idref.replace("$", r"\$")) # r"\$expected"
    path_pattern = r"\/.*\/demo_project" # we need to ignore the path to the demo project because it is different between euler and aws (+ on euler person dependent)
    code_path_pattern = r" \/.*\/code"
    job_finished_order= r"^exp_job_ids_finished: \[.*\]$" # on euler jobs can finish in different order
    netcat_internal_hostname = r"netcat -q 1 [0-9a-z.-]* 2807"
    aws_ec2_host_ids = r"ip-[0-9a-z.-]*internal" # ip can change. This needs to come after netcat_internal_hostname, else the replacement will not work

    print(f"Comparing folders:\n   {d1}\nwith:\n   {d2}")
    is_same = dircomp.compare_dir(d1, d2, ignore_infiles=[suite_id, suite_idref, path_pattern, code_path_pattern, job_finished_order, netcat_internal_hostname, aws_ec2_host_ids],
                                          ignore_files=["stdout.log", "manual.yml", "aws_ec2.yml", "docker.yml"])
    assert is_same
