import os, sys, time

print(f"cwd = {os.getcwd()}")

import numpy as np

print("Server Starting...")
time.sleep(30) # wait 30 seconds

print("Server Writing Output...")
with open("results/server_out.txt", "w+") as f:
    f.write("Server Output - args:")
    f.write(sys.argv[1:])

print("Server Done!")
