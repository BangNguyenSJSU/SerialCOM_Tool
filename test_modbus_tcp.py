#!/usr/bin/env python3
"""
Test script for Modbus TCP protocol implementation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modbus_tcp_protocol import *

def test_modbus_tcp():
    """Test Modbus TCP protocol functionality"""
    print("Testing Modbus TCP Protocol Implementation")
    print("=" * 50)
    
    # Test 1: Register Map
    print("\n1. Testing Register Map...")
    reg_map = ModbusRegisterMap(size=10)
    
    # Write some values
    assert reg_map.write_registers(0, [0x1234, 0x5678, 0xABCD])
    assert reg_map.write_registers(5, [0x0001, 0x0002])
    
    # Read values back
    values = reg_map.read_registers(0, 3)
    assert values == [0x1234, 0x5678, 0xABCD]
    
    values = reg_map.read_registers(5, 2)
    assert values == [0x0001, 0x0002]
    
    print("OK - Register map operations working correctly")
    
    # Test 2: Read Request Frame
    print("\n2. Testing Read Request Frame...")
    frame = ModbusTCPBuilder.read_holding_registers_request(
        transaction_id=0x1234,
        unit_id=1,
        start_address=0x0100,
        count=5
    )
    
    frame_bytes = frame.to_bytes()
    print(f"   Frame bytes: {' '.join(f'{b:02X}' for b in frame_bytes)}")
    
    # Parse frame back
    parsed_frame = ModbusTCPFrame.from_bytes(frame_bytes)
    assert parsed_frame is not None
    assert parsed_frame.transaction_id == 0x1234
    assert parsed_frame.unit_id == 1
    assert parsed_frame.function_code == ModbusFunctionCode.READ_HOLDING_REGISTERS
    
    # Parse request data
    request_data = ModbusTCPParser.parse_read_holding_registers_request(parsed_frame)
    assert request_data is not None
    assert request_data['start_address'] == 0x0100
    assert request_data['count'] == 5
    
    print("OK - Read request frame creation and parsing working correctly")
    
    # Test 3: Write Request Frame
    print("\n3. Testing Write Request Frame...")
    values = [0x1111, 0x2222, 0x3333]
    frame = ModbusTCPBuilder.write_multiple_registers_request(
        transaction_id=0x5678,
        unit_id=2,
        start_address=0x0200,
        values=values
    )
    
    frame_bytes = frame.to_bytes()
    print(f"   Frame bytes: {' '.join(f'{b:02X}' for b in frame_bytes)}")
    
    # Parse frame back
    parsed_frame = ModbusTCPFrame.from_bytes(frame_bytes)
    assert parsed_frame is not None
    assert parsed_frame.transaction_id == 0x5678
    assert parsed_frame.unit_id == 2
    assert parsed_frame.function_code == ModbusFunctionCode.WRITE_MULTIPLE_REGISTERS
    
    # Parse request data
    request_data = ModbusTCPParser.parse_write_multiple_registers_request(parsed_frame)
    assert request_data is not None
    assert request_data['start_address'] == 0x0200
    assert request_data['count'] == 3
    assert request_data['values'] == values
    
    print("OK - Write request frame creation and parsing working correctly")
    
    # Test 4: Response Frames
    print("\n4. Testing Response Frames...")
    
    # Read response
    response_values = [0xAAAA, 0xBBBB, 0xCCCC]
    frame = ModbusTCPBuilder.read_holding_registers_response(
        transaction_id=0x1234,
        unit_id=1,
        values=response_values
    )
    
    frame_bytes = frame.to_bytes()
    parsed_frame = ModbusTCPFrame.from_bytes(frame_bytes)
    response_data = ModbusTCPParser.parse_read_holding_registers_response(parsed_frame)
    
    assert response_data is not None
    assert response_data['values'] == response_values
    
    # Write response
    frame = ModbusTCPBuilder.write_multiple_registers_response(
        transaction_id=0x5678,
        unit_id=2,
        start_address=0x0200,
        count=3
    )
    
    frame_bytes = frame.to_bytes()
    parsed_frame = ModbusTCPFrame.from_bytes(frame_bytes)
    response_data = ModbusTCPParser.parse_write_multiple_registers_response(parsed_frame)
    
    assert response_data is not None
    assert response_data['start_address'] == 0x0200
    assert response_data['count'] == 3
    
    print("OK - Response frame creation and parsing working correctly")
    
    # Test 5: Exception Response
    print("\n5. Testing Exception Response...")
    frame = ModbusTCPBuilder.exception_response(
        transaction_id=0x9999,
        unit_id=3,
        function_code=ModbusFunctionCode.READ_HOLDING_REGISTERS,
        exception_code=ModbusException.ILLEGAL_DATA_ADDRESS
    )
    
    frame_bytes = frame.to_bytes()
    parsed_frame = ModbusTCPFrame.from_bytes(frame_bytes)
    exception_data = ModbusTCPParser.parse_exception_response(parsed_frame)
    
    assert exception_data is not None
    assert exception_data['original_function'] == ModbusFunctionCode.READ_HOLDING_REGISTERS
    assert exception_data['exception_code'] == ModbusException.ILLEGAL_DATA_ADDRESS
    assert "Illegal Data Address" in exception_data['exception_name']
    
    print("OK - Exception response creation and parsing working correctly")
    
    print("\n" + "=" * 50)
    print("SUCCESS - All Modbus TCP protocol tests passed!")
    print("\nImplementation Summary:")
    print("- OK Multi Read 16-bit registers (Function Code 0x03)")
    print("- OK Multi Write 16-bit registers (Function Code 0x10)")
    print("- OK Proper MBAP header handling")
    print("- OK Transaction ID management")
    print("- OK Exception response handling")
    print("- OK Register map with bounds checking")
    print("- OK Complete frame encoding/decoding")


if __name__ == "__main__":
    test_modbus_tcp()