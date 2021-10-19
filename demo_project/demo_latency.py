import argparse, time, json, random, csv, random


def main():

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--opt", type=bool, required=True)
    parser.add_argument("--out", default="json", choices=['json', 'csv'])

    args = parser.parse_args()

    if args.opt:
        a = 1.4
    else:
        a = 3.9


    print("Measuring Latency...")
    data = {}
    data["latency"] = a * args.size + random.uniform(-1, 1) # latency depends linear on size + some noise for reps

    time.sleep(10) # wait 15 seconds

    if args.out == "json":
        write_json_output([data])
    else:
        write_csv_output([data])

    print("Demo Latency Done!")


def write_json_output(data):
    with open("results/demo_latency_out.json", 'w+') as f:
        json.dump(data, f)


def write_csv_output(data):

    header = list(data[0].keys())

    with open("results/demo_latency_out.csv", "w+") as f:
        csv_writer = csv.DictWriter(f, header)
        csv_writer.writeheader()
        csv_writer.writerows(data)


if __name__ == "__main__":
    main()