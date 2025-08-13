"""
Test script for reading channel registers from Modbus TCP Slave
This script helps verify that the channel registers are properly populated
"""

import socket
import struct
import time

def create_modbus_read_request(transaction_id, unit_id, start_addr, count):
    """Create a Modbus TCP Read Holding Registers request"""
    # Function code 0x03 - Read Holding Registers
    function_code = 0x03
    
    # Build the Modbus PDU (Protocol Data Unit)
    pdu = struct.pack('>BHH', function_code, start_addr, count)
    
    # Build the MBAP header (Modbus Application Protocol)
    protocol_id = 0x0000  # Always 0 for Modbus TCP
    length = len(pdu) + 1  # PDU length + unit ID
    mbap = struct.pack('>HHHB', transaction_id, protocol_id, length, unit_id)
    
    return mbap + pdu

def parse_modbus_response(data):
    """Parse a Modbus TCP response"""
    if len(data) < 9:
        return None
    
    # Parse MBAP header
    transaction_id, protocol_id, length, unit_id = struct.unpack('>HHHB', data[:7])
    
    # Parse PDU
    function_code = data[7]
    
    if function_code == 0x03:  # Read Holding Registers response
        byte_count = data[8]
        values = []
        for i in range(9, 9 + byte_count, 2):
            if i + 1 < len(data):
                value = struct.unpack('>H', data[i:i+2])[0]
                values.append(value)
        return values
    elif function_code == 0x83:  # Exception response
        exception_code = data[8] if len(data) > 8 else 0
        return f"Exception: {exception_code}"
    
    return None

def test_channel_registers(ip='127.0.0.1', port=502):
    """Test reading channel registers from the Modbus slave"""
    print(f"\nConnecting to Modbus TCP Slave at {ip}:{port}")
    print("=" * 80)
    
    try:
        # Create socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((ip, port))
        print(f"✓ Connected to {ip}:{port}\n")
        
        # Test 1: Read all 10 channels (30 registers from 0x001A)
        print("TEST 1: Reading all 10 channels (30 registers from 0x001A)")
        print("-" * 60)
        
        request = create_modbus_read_request(1, 1, 0x001A, 30)
        s.send(request)
        response = s.recv(1024)
        values = parse_modbus_response(response)
        
        if isinstance(values, list):
            print(f"Received {len(values)} register values\n")
            
            # Parse and display channel data
            for ch in range(10):
                base_idx = ch * 3
                if base_idx + 2 < len(values):
                    current_ma = values[base_idx]
                    voltage_mv = values[base_idx + 1]
                    state = values[base_idx + 2]
                    state_name = ["OFF", "ON", "FAULT", "OVERCURRENT"][state] if state < 4 else "UNKNOWN"
                    
                    print(f"Channel {ch+1:2d}: Current={current_ma:5d}mA ({current_ma/1000:.2f}A), "
                          f"Voltage={voltage_mv:5d}mV ({voltage_mv/1000:.2f}V), "
                          f"State={state} ({state_name})")
        else:
            print(f"Error: {values}")
        
        print()
        
        # Test 2: Read specific channel (Channel 5 - 3 registers from 0x0026)
        print("TEST 2: Reading Channel 5 only (3 registers from 0x0026)")
        print("-" * 60)
        
        request = create_modbus_read_request(2, 1, 0x0026, 3)
        s.send(request)
        response = s.recv(1024)
        values = parse_modbus_response(response)
        
        if isinstance(values, list) and len(values) >= 3:
            current_ma = values[0]
            voltage_mv = values[1]
            state = values[2]
            state_name = ["OFF", "ON", "FAULT", "OVERCURRENT"][state] if state < 4 else "UNKNOWN"
            
            print(f"Channel 5: Current={current_ma}mA ({current_ma/1000:.2f}A)")
            print(f"          Voltage={voltage_mv}mV ({voltage_mv/1000:.2f}V)")
            print(f"          State={state} ({state_name})")
        else:
            print(f"Error: {values}")
        
        print()
        
        # Test 3: Read first register only to check if any data exists
        print("TEST 3: Reading first channel current register (0x001A)")
        print("-" * 60)
        
        request = create_modbus_read_request(3, 1, 0x001A, 1)
        s.send(request)
        response = s.recv(1024)
        values = parse_modbus_response(response)
        
        if isinstance(values, list) and len(values) >= 1:
            print(f"Register 0x001A value: {values[0]} (Channel 1 current in mA)")
            if values[0] == 0:
                print("\n⚠️ WARNING: Register is 0. Possible issues:")
                print("  1. Test pattern not loaded - Click 'Test Pattern' button")
                print("  2. Registers cleared - Reload test pattern")
                print("  3. Server just started - Enable 'Auto-load test pattern' checkbox")
        else:
            print(f"Error: {values}")
        
        s.close()
        print("\n✓ Test completed successfully")
        
    except socket.timeout:
        print("❌ Connection timeout - Is the server running?")
    except ConnectionRefusedError:
        print("❌ Connection refused - Is the server running on the correct port?")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # You can modify these values to match your server settings
    SERVER_IP = "127.0.0.1"  # or "0.0.0.0" or your actual IP
    SERVER_PORT = 502
    
    print("\nModbus TCP Channel Register Test")
    print("Make sure the Modbus TCP Slave is running with test pattern loaded!")
    
    test_channel_registers(SERVER_IP, SERVER_PORT)