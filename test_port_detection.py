#!/usr/bin/env python3
"""
Test script to see what serial ports are detected
"""

import serial.tools.list_ports

print("=" * 50)
print("SERIAL PORT DETECTION TEST")
print("=" * 50)

# Get all ports using pyserial's detection
ports = serial.tools.list_ports.comports()
print(f"Found {len(ports)} ports using pyserial:")
for port in ports:
    print(f"  {port.device} - {port.description}")

print("\n" + "=" * 50)
print("MANUAL TTY DETECTION")
print("=" * 50)

# Check specific virtual ports
import os
virtual_ports = ['/dev/ttys006', '/dev/ttys007', '/dev/ttys005', '/dev/ttys008']

print("Checking virtual TTY ports manually:")
for port in virtual_ports:
    if os.path.exists(port):
        try:
            # Try to open the port to see if it's usable
            with serial.Serial(port, timeout=0, write_timeout=0) as ser:
                print(f"  ✅ {port} - Available and working")
        except Exception as e:
            print(f"  ❌ {port} - Exists but error: {str(e)}")
    else:
        print(f"  ❓ {port} - Does not exist")

print("\n" + "=" * 50)
print("ALL /dev/tty* PORTS")
print("=" * 50)

# List all tty devices
import glob
all_ttys = glob.glob('/dev/tty*')
print("All TTY devices found:")
for tty in sorted(all_ttys):
    if 'ttys' in tty:
        print(f"  {tty}")

print("\nTest completed!")