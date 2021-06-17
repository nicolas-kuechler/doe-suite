import sys, time

print("Client Starting...")
time.sleep(30) # wait 30 seconds

print("Client Writing Output...")
with open("results/client_out.txt") as f:
    f.write("Client Output - args:")
    f.write(sys.argv[1:])

print("Client Done!")
