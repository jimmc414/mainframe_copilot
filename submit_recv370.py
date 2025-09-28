#!/usr/bin/env python3
"""
Submit RECV370 job to process KICKS XMIT file
"""

import time
from py3270 import Emulator

# Connect to MVS
em = Emulator(visible=False)
em.connect('localhost:3270')
time.sleep(3)

# Wait for initial screen
time.sleep(1)

# Send clear key to unlock keyboard
em.exec_command(b'Clear')
time.sleep(1)

# Logon to TSO with HERC02
em.send_string("LOGON HERC02")
em.send_enter()
time.sleep(2)

# Enter password
em.send_string("CUL8TR")
em.send_enter()
time.sleep(3)

# Wait for READY
for _ in range(10):
    screen = em.string_get(1, 1, 1920)  # Get 24x80 screen
    if "READY" in screen:
        break
    time.sleep(1)

print("Logged on to TSO, submitting RECV370 job...")

# Submit the JCL from the dataset
em.send_string("SUBMIT 'HERC02.JCL(RECVKICK)'")
em.send_enter()
time.sleep(3)

# Check for submission
screen = em.string_get(1, 1, 1920)
if "JOB" in screen and "SUBMITTED" in screen:
    print("RECV370 job submitted successfully")
    # Extract job number if possible
    lines = screen.split('\n')
    for line in lines:
        if "JOB" in line and "SUBMITTED" in line:
            print(f"Job info: {line.strip()}")
            break
else:
    print("Could not verify job submission")
    print(f"Screen content:\n{screen}")

# Wait a bit for job to complete
print("Waiting for job to complete...")
time.sleep(10)

# Check job status with STATUS command
em.send_string("STATUS")
em.send_enter()
time.sleep(2)

status_screen = em.string_get(1, 1, 1920)
print(f"Status output:\n{status_screen}")

# Logoff
em.send_string("LOGOFF")
em.send_enter()
time.sleep(2)

em.disconnect()
print("Disconnected from TSO")