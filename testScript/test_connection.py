#!/usr/bin/env python3
"""Test script to verify Modbus TCP connection stability"""

import socket
import time
import struct

def create_modbus_read_request(transaction_id=1, unit_id=1, start_addr=0, count=1):
    """Create a Modbus TCP read holding registers request"""
    # MBAP Header
    mbap = struct.pack('>HHHB', 
                      transaction_id,  # Transaction ID
                      0,               # Protocol ID (0 for Modbus)
                      6,               # Length (6 bytes following)
                      unit_id)         # Unit ID
    
    # Function code 0x03 (Read Holding Registers)
    pdu = struct.pack('>BHH', 
                     0x03,           # Function code
                     start_addr,     # Starting address
                     count)          # Number of registers
    
    return mbap + pdu

def test_connection_stability():
    """Test that the connection remains stable"""
    
    print("Testing Modbus TCP Connection Stability")
    print("=" * 50)
    
    try:
        # Connect to server
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5.0)
        
        server_ip = "127.0.0.1"  # Use localhost for testing
        server_port = 502
        
        print(f"Connecting to {server_ip}:{server_port}...")
        client.connect((server_ip, server_port))
        print("[SUCCESS] Connected")
        
        # Send multiple requests to test stability
        for i in range(5):
            print(f"\nTest {i+1}/5:")
            
            # Create and send request
            request = create_modbus_read_request(
                transaction_id=i+1,
                unit_id=1,
                start_addr=0,
                count=10
            )
            
            print(f"  Sending read request (TID={i+1})...")
            client.send(request)
            
            # Receive response
            try:
                response = client.recv(1024)
                if response:
                    # Parse transaction ID from response
                    tid = struct.unpack('>H', response[0:2])[0]
                    print(f"  [SUCCESS] Received response (TID={tid}, {len(response)} bytes)")
                else:
                    print("  [ERROR] No response received")
                    break
            except socket.timeout:
                print("  [ERROR] Response timeout")
                break
            
            # Small delay between requests
            time.sleep(0.5)
        
        print("\n" + "=" * 50)
        print("Connection test completed")
        
        # Keep connection open for a bit to test persistence
        print("Testing connection persistence (5 seconds)...")
        time.sleep(5)
        
        # Send one more request to verify connection still works
        print("Sending final test request...")
        request = create_modbus_read_request(transaction_id=99)
        client.send(request)
        
        response = client.recv(1024)
        if response:
            print("[SUCCESS] Connection still active after 5 seconds")
        else:
            print("[FAILED] Connection dropped")
        
        client.close()
        print("Connection closed")
        
    except ConnectionRefusedError:
        print("[ERROR] Connection refused - Is the Modbus TCP Slave running?")
        print("Please start the Slave server first:")
        print("1. Open the application")
        print("2. Go to Modbus TCP Slave tab")
        print("3. Select IP: 0.0.0.0 or 127.0.0.1")
        print("4. Click 'Start Server'")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    test_connection_stability()