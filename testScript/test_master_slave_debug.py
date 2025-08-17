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

def test_master_slave_debug(ip='127.0.0.1', port=502):
    """Test both Master and Slave debug improvements"""
    print("=" * 80)
    print("TESTING IMPROVED DEBUG MESSAGES - MASTER & SLAVE")
    print("=" * 80)
    
    print("\nWhat to expect:")
    print("\nMASTER TAB (Client) will show:")
    print("  [timestamp] TX Request (TID: 0001):")
    print("    Read Request - 10 registers from 0x001A to 0x0023")
    print("  [timestamp] RX Response (TID: 0001, Time: 5.2ms):")
    print("    Read Response (10 regs): [0]=0x03E8 [1]=0x2EE0 [2]=0x0001 ...")
    
    print("\nSLAVE TAB (Server) will show:")
    print("  [timestamp] Read 10 registers from 0x001A")
    print("  [DEBUG] Response #1: Read Response (10 regs): [0]=0x03E8 [1]=0x2EE0 ...")
    
    print("\\n" + "-" * 80)
    
    try:
        # Connect to server
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((ip, port))
        print(f"\\n[OK] Connected to {ip}:{port}")
        
        # Test 1: Small read request
        print("\\n1. SMALL READ TEST (5 registers from 0x001A)")
        print("   Check both Master TX log and Slave RX/Response logs")
        request = create_read_request(1, 1, 0x001A, 5)
        s.send(request)
        response = s.recv(1024)
        print("   [OK] Request sent and response received")
        time.sleep(0.5)
        
        # Test 2: Large read request  
        print("\\n2. LARGE READ TEST (25 registers from 0x0000)")
        print("   Should show multi-line format in both Master and Slave")
        request = create_read_request(2, 1, 0x0000, 25)
        s.send(request)
        response = s.recv(1024)
        print("   [OK] Request sent and response received")
        time.sleep(0.5)
        
        # Test 3: Write request (small)
        print("\\n3. SMALL WRITE TEST (3 registers to 0x0042)")
        print("   Check Write Request and Write Response formatting")
        values = [0x1111, 0x2222, 0x3333]
        request = create_write_request(3, 1, 0x0042, values)
        s.send(request)
        response = s.recv(1024)
        print("   [OK] Request sent and response received")
        time.sleep(0.5)
        
        # Test 4: Large write request
        print("\\n4. LARGE WRITE TEST (12 registers to 0x0050)")
        print("   Should show multi-line format for large write requests")
        values = [0x1000 + i for i in range(12)]  # 0x1000, 0x1001, 0x1002, ...
        request = create_write_request(4, 1, 0x0050, values)
        s.send(request)
        response = s.recv(1024)
        print("   [OK] Request sent and response received")
        time.sleep(0.5)
        
        # Test 5: Channel data read (practical example)
        print("\\n5. CHANNEL DATA READ (30 registers from 0x001A)")
        print("   Reading all 10 channels (3 registers each)")
        request = create_read_request(5, 1, 0x001A, 30)
        s.send(request)
        response = s.recv(1024)
        print("   [OK] Request sent and response received")
        
        s.close()
        
        print("\\n" + "=" * 80)
        print("TESTS COMPLETED - CHECK BOTH MASTER AND SLAVE LOGS")
        print("=" * 80)
        
        print("\\nIMPROVEMENTS IMPLEMENTED:")
        print("\\n[MASTER TAB]")
        print("  * Enhanced colors: Orange debug messages on yellow background")
        print("  * Detailed TX Request decoding with indexed register values")
        print("  * Detailed RX Response decoding with all register values")
        print("  * Multi-line format for large requests/responses (>8 registers)")
        print("  * Response timing information")
        print("  * Better exception response decoding")
        
        print("\\n[SLAVE TAB]")
        print("  * Enhanced debug response messages with indexed values")
        print("  * Write Response shows address range (from 0x0042 to 0x0044)")
        print("  * All register values displayed (no truncation)")
        print("  * Better visual formatting with colors and fonts")
        
        print("\\nCOLOR SCHEME:")
        print("  * Requests: Bright Green (#00AA00) Bold")
        print("  * Responses: Bright Purple (#AA00AA) Bold") 
        print("  * Debug: Orange (#FF6600) on Light Yellow Background")
        print("  * Errors: Bright Red (#CC0000) Bold")
        print("  * Info: Nice Blue (#0066CC)")
        print("  * System: Gray (#666666)")
        print("  * Font: Consolas monospace for better alignment")
        
    except Exception as e:
        print(f"\\n[ERROR] {e}")
        print("Make sure the Modbus TCP Slave is running with test pattern loaded!")

if __name__ == "__main__":
    test_master_slave_debug()