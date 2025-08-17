"""
Test the improved debug messages in Modbus TCP Slave
"""

import socket
import struct
import time

def create_read_request(transaction_id, unit_id, start_addr, count):
    """Create a Read Holding Registers request"""
    function_code = 0x03
    pdu = struct.pack('>BHH', function_code, start_addr, count)
    protocol_id = 0x0000
    length = len(pdu) + 1
    mbap = struct.pack('>HHHB', transaction_id, protocol_id, length, unit_id)
    return mbap + pdu

def create_write_request(transaction_id, unit_id, start_addr, values):
    """Create a Write Multiple Registers request"""
    function_code = 0x10
    count = len(values)
    byte_count = count * 2
    
    # Pack register values
    values_bytes = b''.join(struct.pack('>H', v) for v in values)
    
    pdu = struct.pack('>BHHB', function_code, start_addr, count, byte_count) + values_bytes
    protocol_id = 0x0000
    length = len(pdu) + 1
    mbap = struct.pack('>HHHB', transaction_id, protocol_id, length, unit_id)
    return mbap + pdu

def test_debug_messages(ip='127.0.0.1', port=502):
    """Test to see the new debug message format"""
    print("\nTesting Improved Debug Messages")
    print("=" * 60)
    print("Watch the Modbus TCP Slave Communication Log for:")
    print("  - OLD: [DEBUG] Sent response #1 (11 bytes)")
    print("  - NEW: [DEBUG] Response #1: Read Response - 3 registers: [0x03E8, 0x2EE0, 0x0001]")
    print("=" * 60)
    
    try:
        # Connect to server
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((ip, port))
        print(f"\n✓ Connected to {ip}:{port}")
        
        # Test 1: Read request (small)
        print("\n1. Sending Read Request for 3 registers from 0x001A")
        request = create_read_request(1, 1, 0x001A, 3)
        s.send(request)
        response = s.recv(1024)
        print("   Response received - Check slave debug log!")
        time.sleep(0.5)
        
        # Test 2: Read request (large)
        print("\n2. Sending Read Request for 10 registers from 0x0000")
        request = create_read_request(2, 1, 0x0000, 10)
        s.send(request)
        response = s.recv(1024)
        print("   Response received - Check slave debug log!")
        time.sleep(0.5)
        
        # Test 3: Write request
        print("\n3. Sending Write Request for 5 registers to 0x0042")
        values = [0x1111, 0x2222, 0x3333, 0x4444, 0x5555]
        request = create_write_request(3, 1, 0x0042, values)
        s.send(request)
        response = s.recv(1024)
        print("   Response received - Check slave debug log!")
        
        s.close()
        print("\n✓ Tests completed - Check the slave's Communication Log")
        print("\nExpected debug messages:")
        print("  Response #1: Read Response - 3 registers: [0x03E8, 0x2EE0, 0x0001]")
        print("  Response #2: Read Response - 10 registers: [0x0001, 0x0002, 0x0003... (10 total)]")
        print("  Response #3: Write Response - Wrote 5 registers from 0x0042")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure the Modbus TCP Slave is running!")

if __name__ == "__main__":
    test_debug_messages()