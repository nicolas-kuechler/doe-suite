import os, sys, time, json, random

print(f"cwd = {os.getcwd()}")

import numpy as np

print("Client Starting...")
time.sleep(30) # wait 30 seconds

d = {}

for i, a in enumerate(sys.argv[1:]):
    d[f"a{i}"] = a

d["tp"] = random.randint(1, 21)

print("Client Writing Output...")
with open("results/client_out.json", 'w+') as f:
    json.dump(d, f)

print("Client Done!")
