#!/usr/bin/env python3
"""
Test script for the protocol implementation
Can be used to verify packet encoding/decoding and checksum calculations
"""

from protocol import (
    Packet, PacketBuilder, PacketParser,
    FunctionCode, ErrorCode, RegisterMap,
    fletcher16, encode_word, decode_word
)


def test_fletcher16():
    """Test Fletcher-16 checksum calculation"""
    print("Testing Fletcher-16 checksum...")
    
    # Test with known data
    test_data = bytes([0x7E, 0x01, 0x02, 0x03, 0x01, 0x00, 0x10])
    checksum = fletcher16(test_data)
    print(f"  Data: {' '.join(f'{b:02X}' for b in test_data)}")
    print(f"  Checksum: 0x{checksum:04X}")
    print()


def test_packet_encoding():
    """Test packet encoding"""
    print("Testing packet encoding...")
    
    # Test read single request
    packet = PacketBuilder.read_single_request(device_addr=1, msg_id=0x10, reg_addr=0x1234)
    packet_bytes = packet.to_bytes()
    print(f"  Read Single Request:")
    print(f"    Device: 1, MsgID: 0x10, RegAddr: 0x1234")
    print(f"    Encoded: {' '.join(f'{b:02X}' for b in packet_bytes)}")
    
    # Test write single request
    packet = PacketBuilder.write_single_request(device_addr=2, msg_id=0x11, reg_addr=0x5678, reg_value=0xABCD)
    packet_bytes = packet.to_bytes()
    print(f"  Write Single Request:")
    print(f"    Device: 2, MsgID: 0x11, RegAddr: 0x5678, Value: 0xABCD")
    print(f"    Encoded: {' '.join(f'{b:02X}' for b in packet_bytes)}")
    print()


def test_packet_decoding():
    """Test packet decoding"""
    print("Testing packet decoding...")
    
    # Create a packet
    original = PacketBuilder.read_single_request(device_addr=5, msg_id=0x20, reg_addr=0x0100)
    packet_bytes = original.to_bytes()
    
    # Decode it
    decoded = Packet.from_bytes(packet_bytes)
    if decoded:
        print(f"  Original packet: {' '.join(f'{b:02X}' for b in packet_bytes)}")
        print(f"  Decoded successfully:")
        print(f"    Device Address: {decoded.device_address}")
        print(f"    Message ID: 0x{decoded.message_id:02X}")
        print(f"    Function Code: 0x{decoded.function_code:02X}")
        print(f"    Data: {' '.join(f'{b:02X}' for b in decoded.data)}")
        
        # Parse the request
        parsed = PacketParser.parse_request(decoded)
        if parsed:
            print(f"  Parsed request:")
            print(f"    Register Address: 0x{parsed['register_address']:04X}")
    else:
        print("  Failed to decode packet!")
    print()


def test_register_map():
    """Test register map operations"""
    print("Testing register map...")
    
    reg_map = RegisterMap(size=16)
    
    # Test single write/read
    reg_map.write(0, 0x1234)
    reg_map.write(1, 0x5678)
    
    value = reg_map.read(0)
    print(f"  Register[0] = 0x{value:04X}")
    value = reg_map.read(1)
    print(f"  Register[1] = 0x{value:04X}")
    
    # Test multiple write/read
    values = [0xAAAA, 0xBBBB, 0xCCCC]
    reg_map.write_multiple(4, values)
    
    read_values = reg_map.read_multiple(4, 3)
    print(f"  Registers[4:7] = {', '.join(f'0x{v:04X}' for v in read_values)}")
    
    # Test bounds checking
    result = reg_map.write(100, 0x9999)
    print(f"  Write to address 100 (out of bounds): {'Failed' if not result else 'Success'}")
    print()


def test_error_responses():
    """Test error response generation"""
    print("Testing error responses...")
    
    # Generate various error responses
    errors = [
        (ErrorCode.INVALID_FUNCTION, "Invalid Function"),
        (ErrorCode.INVALID_ADDRESS, "Invalid Address"),
        (ErrorCode.INVALID_VALUE, "Invalid Value"),
        (ErrorCode.INTERNAL_ERROR, "Internal Error")
    ]
    
    for error_code, desc in errors:
        packet = PacketBuilder.error_response(
            device_addr=1, msg_id=0x30, function_code=FunctionCode.READ_SINGLE, error_code=error_code
        )
        packet_bytes = packet.to_bytes()
        print(f"  {desc} (0x{error_code:02X}):")
        print(f"    Packet: {' '.join(f'{b:02X}' for b in packet_bytes)}")
    print()


def test_full_communication():
    """Test a complete request-response cycle"""
    print("Testing full communication cycle...")
    
    # Simulate register map
    device_map = RegisterMap(size=256)
    device_map.write(0x10, 0x1234)
    device_map.write(0x11, 0x5678)
    
    # Create request
    request = PacketBuilder.read_single_request(device_addr=1, msg_id=0x40, reg_addr=0x10)
    request_bytes = request.to_bytes()
    print(f"  Host sends request: {' '.join(f'{b:02X}' for b in request_bytes)}")
    
    # Device receives and decodes
    received = Packet.from_bytes(request_bytes)
    if received:
        parsed = PacketParser.parse_request(received)
        if parsed:
            # Device reads register
            value = device_map.read(parsed['register_address'])
            
            # Device sends response
            response = PacketBuilder.read_single_response(
                device_addr=1, 
                msg_id=received.message_id,
                reg_addr=parsed['register_address'],
                reg_value=value
            )
            response_bytes = response.to_bytes()
            print(f"  Device sends response: {' '.join(f'{b:02X}' for b in response_bytes)}")
            
            # Host receives and decodes response
            received_resp = Packet.from_bytes(response_bytes)
            if received_resp:
                parsed_resp = PacketParser.parse_response(received_resp)
                if parsed_resp:
                    print(f"  Host decoded response:")
                    print(f"    Register 0x{parsed_resp['register_address']:04X} = 0x{parsed_resp['register_value']:04X}")
    print()


def main():
    """Run all tests"""
    print("=" * 60)
    print("Protocol Implementation Test Suite")
    print("=" * 60)
    print()
    
    test_fletcher16()
    test_packet_encoding()
    test_packet_decoding()
    test_register_map()
    test_error_responses()
    test_full_communication()
    
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()