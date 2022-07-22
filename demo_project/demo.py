import os
import sys
import time
import json
import random
import csv

random.seed(1234)


def main():
    print(f"cwd={os.getcwd()}")

    # read the config file in the working directory
    config_path = sys.argv[2]
    with open(config_path, "r") as c:
        config = json.load(c)
    print(f"config={config}\n\n")

    print("Demo Starting...")
    time.sleep(15)  # wait 15 seconds

    print("Demo Writing Output...")

    if "out" in config and config["out"] == "json":
        write_json_output(sys.argv[1:])
    else:
        write_csv_output(sys.argv[1:])

    print("Demo Done!")


def write_json_output(args):
    d = {}
    for i, a in enumerate(args):
        d[f"a{i}"] = a

    d["tp"] = random.randint(1, 21)

    with open("results/demo_out.json", "w+") as f:
        json.dump(d, f)


def write_csv_output(args):
    header = []
    row = []
    for i, a in enumerate(args):
        header.append(f"a{i}")
        row.append(a)

    header.append("tp")
    row.append(random.randint(1, 21))

    with open("results/demo_out.csv", "w+") as f:
        writer = csv.writer(f)

        writer.writerow(header)
        writer.writerow(row)


if __name__ == "__main__":
    main()
