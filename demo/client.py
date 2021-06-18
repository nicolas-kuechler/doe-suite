import os, sys, time

print(f"cwd = {os.getcwd()}")

import numpy as np

print("Client Starting...")
time.sleep(30) # wait 30 seconds

print("Client Writing Output...")
with open("results/client_out.txt", 'w+') as f:
    f.write("Client Output - args:")
    f.write(str(sys.argv[1:]))

print("Client Done!")
