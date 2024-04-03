import numpy as np


def generate_fake_data(n_measurements, system, system_config, workload):

    fake_data_s = {
        "system1": {"workload1": [20,5,10], "workload2": [25,7,12]},
        "system2": {"workload1": [22,6,11], "workload2": [18,4,9]},
        "system3": {"workload1": [23,6,11], "workload2": [20,5,10]}
    }

    fake_data_mb = {
      "system1": {"workload1": [800,200], "workload2": [750,250]},
      "system2": {"workload1": [780,220], "workload2": [820,180]},
      "system3": {"workload1": [770,230], "workload2": [800,200]}
    }


    system_config_factor = {
        "v1": 1,
        "v2": 1.6,
    }

    scales = {
      "system1": {"workload1": 10, "workload2": 13},
      "system2": {"workload1": 5, "workload2": 9},
      "system3": {"workload1": 15, "workload2": 20}
    }

    np.random.seed(12345)

    xs = fake_data_s[system][workload]
    xmb = fake_data_mb[system][workload]

    res = {"base_s": xs[0], "overhead1_s": xs[1], "overhead2_s": xs[2], "base_mb": xmb[0], "overhead_mb": xmb[1]}

    results = []

    for i in range(n_measurements):

        for k, v in res.items():
            v = v * system_config_factor[system_config]
            scale = v * scales[system][workload] / 100
            res[k] = round(np.random.normal(loc=v, scale=scale), 1)

        res_str = ", ".join(f"{k}: {v}" for k, v in res.items())

        res_str = "{" + res_str + "}"
        results.append(res_str)

    res_str = "[" + ", ".join(results) + "]"

    return res_str




class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            'generate_fake_data': generate_fake_data
        }