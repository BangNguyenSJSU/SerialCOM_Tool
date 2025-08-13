"""
Test the improved debug messages for both Master and Slave
This script demonstrates the enhanced logging with full register displays
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

def main():
    ip = '127.0.0.1'
    port = 502
    
    print("=" * 80)
    print("TESTING IMPROVED DEBUG MESSAGES - MASTER & SLAVE")
    print("=" * 80)
    
    print("\nSUMMARY OF IMPROVEMENTS:")
    print("\n[SLAVE TAB - Write Response Fixed]:")
    print("  * OLD: Write Response - Successfully wrote 5 registers starting at 0x0042")
    print("  * NEW: Write Response - Wrote 5 registers from 0x0042 to 0x0046")
    
    print("\n[MASTER TAB - Complete Overhaul]:")
    print("  * Enhanced TX Request decoding with indexed register values")
    print("  * Enhanced RX Response decoding with all register values")
    print("  * Multi-line format for large requests/responses (>8 registers)")
    print("  * Better exception response decoding with names")
    print("  * Response timing information")
    
    print("\n[BOTH TABS - Visual Improvements]:")
    print("  * Orange debug messages (#FF6600) on light yellow background (#FFF8E0)")
    print("  * Consolas monospace font for better alignment")
    print("  * Bold formatting for important messages")
    print("  * Improved color scheme for better visibility")
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((ip, port))
        print(f"\n[OK] Connected to {ip}:{port}")
        
        # Test 1: Small read
        print("\n1. SMALL READ TEST (5 registers)")
        request = create_read_request(1, 1, 0x001A, 5)
        s.send(request)
        response = s.recv(1024)
        print("   [OK] Check both Master TX and Slave Response logs")
        time.sleep(0.3)
        
        # Test 2: Large read
        print("\n2. LARGE READ TEST (20 registers)")
        request = create_read_request(2, 1, 0x0000, 20)
        s.send(request)
        response = s.recv(1024)
        print("   [OK] Should show multi-line format")
        time.sleep(0.3)
        
        # Test 3: Small write
        print("\n3. SMALL WRITE TEST (3 registers)")
        values = [0x1111, 0x2222, 0x3333]
        request = create_write_request(3, 1, 0x0042, values)
        s.send(request)
        response = s.recv(1024)
        print("   [OK] Check improved Write Response format")
        time.sleep(0.3)
        
        # Test 4: Large write
        print("\n4. LARGE WRITE TEST (15 registers)")
        values = [0x1000 + i for i in range(15)]
        request = create_write_request(4, 1, 0x0050, values)
        s.send(request)
        response = s.recv(1024)
        print("   [OK] Should show multi-line request format")
        
        s.close()
        print("\n" + "=" * 80)
        print("TESTS COMPLETED - CHECK BOTH MASTER AND SLAVE LOGS")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("Make sure the Modbus TCP Slave is running!")

if __name__ == "__main__":
    main()