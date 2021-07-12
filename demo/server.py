import os, sys, time, csv, random

print(f"cwd = {os.getcwd()}")

import numpy as np

print("Server Starting...")
time.sleep(30) # wait 30 seconds


header = []
row = []
for i, a in enumerate(sys.argv[1:]):
    header.append(f"a{i}")
    row.append(a)

header.append("tp")
row.append(random.randint(1, 21))

print("Server Writing Output...")
with open("results/server_out.csv", "w+") as f:
    writer = csv.writer(f)

    writer.writerow(header)
    writer.writerow(row)

print("Server Done!")
