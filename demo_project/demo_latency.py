import argparse
import time
import json
import random
import csv


random.seed(1234)


def main():

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--opt", choices=["True", "False"], required=True)
    parser.add_argument("--out", default="json", choices=["json", "csv"])

    args = parser.parse_args()

    if args.opt == "True":
        a = 1.4
    else:
        a = 2.7

    print("Measuring Latency...")
    data = {}
    noise = 0.9329
    #noise = random.uniform(-1, 1)
    data["latency"] = a * args.size + noise # latency depends linear on size + some noise for reps


    time.sleep(10)  # wait 15 seconds

    if args.out == "json":
        write_json_output([data])
    else:
        write_csv_output([data])

    print("Demo Latency Done!")


def write_json_output(data):
    with open("results/demo_latency_out.json", "w+") as f:
        json.dump(data, f)


def write_csv_output(data):

    header = list(data[0].keys())

    with open("results/demo_latency_out.csv", "w+") as f:
        csv_writer = csv.DictWriter(f, header)
        csv_writer.writeheader()
        csv_writer.writerows(data)


if __name__ == "__main__":
    main()
