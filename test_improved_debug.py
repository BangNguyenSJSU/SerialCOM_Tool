"""
Test the improved debug messages with full register display and better colors
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

def test_improved_debug(ip='127.0.0.1', port=502):
    """Test to see the improved debug message format with all registers"""
    print("\n" + "="*80)
    print("TESTING IMPROVED DEBUG MESSAGES WITH FULL REGISTER DISPLAY")
    print("="*80)
    print("\nFeatures:")
    print("  ✅ ALL register values displayed (not truncated)")
    print("  ✅ Index numbers for each register [0]=0x1234")
    print("  ✅ Better colors: Orange debug messages on light yellow background")
    print("  ✅ Multi-line format for large responses (>8 registers)")
    print("  ✅ Monospace font (Consolas) for better alignment")
    print("\n" + "-"*80)
    
    try:
        # Connect to server
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((ip, port))
        print(f"\n✓ Connected to {ip}:{port}")
        
        # Test 1: Small read (5 registers) - single line display
        print("\n1. SMALL READ TEST (5 registers from 0x001A)")
        print("   Expected: Single line with all values")
        request = create_read_request(1, 1, 0x001A, 5)
        s.send(request)
        response = s.recv(1024)
        print("   ✓ Response received - Check slave debug log!")
        print("   Should see: Read Response (5 regs): [0]=0x03E8 [1]=0x2EE0 [2]=0x0001 [3]=0x044C [4]=0x2F44")
        time.sleep(0.5)
        
        # Test 2: Medium read (10 registers) - multi-line display
        print("\n2. MEDIUM READ TEST (10 registers from 0x0000)")
        print("   Expected: Multi-line format with 8 registers per line")
        request = create_read_request(2, 1, 0x0000, 10)
        s.send(request)
        response = s.recv(1024)
        print("   ✓ Response received - Check slave debug log!")
        print("   Should see multiple lines with indexed values")
        time.sleep(0.5)
        
        # Test 3: Large read (43 registers) - multi-line display
        print("\n3. LARGE READ TEST (43 registers from 0x0000)")
        print("   Expected: Multi-line format showing ALL 43 values with indices")
        request = create_read_request(3, 1, 0x0000, 43)
        s.send(request)
        response = s.recv(1024)
        print("   ✓ Response received - Check slave debug log!")
        print("   Should see 6 lines (5 lines of 8 registers + 1 line of 3 registers)")
        time.sleep(0.5)
        
        # Test 4: Channel data read (30 registers - all 10 channels)
        print("\n4. CHANNEL DATA TEST (30 registers from 0x001A)")
        print("   Expected: 4 lines showing all channel data")
        request = create_read_request(4, 1, 0x001A, 30)
        s.send(request)
        response = s.recv(1024)
        print("   ✓ Response received - Check slave debug log!")
        print("   Each group of 3 registers = 1 channel (current, voltage, state)")
        
        s.close()
        print("\n" + "="*80)
        print("✓ TESTS COMPLETED")
        print("="*80)
        print("\nCHECK THE SLAVE'S COMMUNICATION LOG FOR:")
        print("  • Orange debug messages with light yellow background")
        print("  • Full register displays with [index]=value format")
        print("  • Multi-line formatting for large responses")
        print("  • Bold monospace font for better readability")
        print("\nEXAMPLE OUTPUT:")
        print("[DEBUG] Response #3: Read Response (43 registers):")
        print("    [0]=0x0001 [1]=0x0002 [2]=0x0003 [3]=0x0004 [4]=0x0005 [5]=0x0006 [6]=0x0007 [7]=0x0008")
        print("    [8]=0x0009 [9]=0x000A [10]=0x000B [11]=0x000C [12]=0x000D [13]=0x000E [14]=0x000F [15]=0x0010")
        print("    ... (continues for all 43 registers)")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure the Modbus TCP Slave is running with test pattern loaded!")

if __name__ == "__main__":
    test_improved_debug()