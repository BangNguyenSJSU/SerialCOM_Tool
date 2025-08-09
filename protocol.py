#!/usr/bin/env python3
"""
Protocol implementation for register-based communication
Implements packet encoding/decoding and Fletcher-16 checksum
"""

from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from enum import IntEnum


class FunctionCode(IntEnum):
    """Function codes for protocol operations.
    
    These codes identify the type of operation being requested or responded to.
    Request codes are 0x01-0x04, response codes are 0x41-0x44, error codes are 0x81-0x84.
    """
    # Host requests (sent by master to slave)
    READ_SINGLE = 0x01      # Read one 16-bit register
    WRITE_SINGLE = 0x02     # Write one 16-bit register
    READ_MULTIPLE = 0x03    # Read up to 255 consecutive registers
    WRITE_MULTIPLE = 0x04   # Write up to 255 consecutive registers
    
    # Device responses
    READ_SINGLE_RESP = 0x41
    WRITE_SINGLE_RESP = 0x42
    READ_MULTIPLE_RESP = 0x43
    WRITE_MULTIPLE_RESP = 0x44
    
    # Error responses
    READ_SINGLE_ERROR = 0x81
    WRITE_SINGLE_ERROR = 0x82
    READ_MULTIPLE_ERROR = 0x83
    WRITE_MULTIPLE_ERROR = 0x84


class ErrorCode(IntEnum):
    """Error codes for protocol errors"""
    INVALID_FUNCTION = 0x01
    INVALID_ADDRESS = 0x02
    INVALID_VALUE = 0x03
    INTERNAL_ERROR = 0xFF


@dataclass
class Packet:
    """Represents a protocol packet for register-based communication.
    
    Attributes:
        device_address: Target device address (0-247, 0=broadcast)
        message_id: Unique message identifier for request/response matching (0-255)
        function_code: Operation type from FunctionCode enum
        data: Payload bytes containing parameters or values
        checksum: Fletcher-16 checksum for data integrity (calculated if None)
    """
    device_address: int      # 0-247, where 0 is broadcast
    message_id: int          # 0-255, for matching responses to requests
    function_code: int       # Operation type from FunctionCode enum
    data: bytes             # Payload data (parameters/values)
    checksum: Optional[int] = None  # Fletcher-16 checksum
    
    def to_bytes(self) -> bytes:
        """Convert packet to bytes with checksum.
        
        Builds the complete packet structure:
        [0x7E][DevAddr][MsgID][Length][FuncCode][Data...][Checksum_H][Checksum_L]
        
        Returns:
            bytes: Complete packet ready for transmission
        """
        # Build packet without checksum
        packet = bytearray()
        packet.append(0x7E)  # Start flag (packet delimiter)
        packet.append(self.device_address)  # Target device
        packet.append(self.message_id)      # Message identifier
        packet.append(len(self.data) + 1)   # Length includes function code
        packet.append(self.function_code)   # Operation type
        packet.extend(self.data)            # Payload data
        
        # Calculate and append checksum
        checksum = fletcher16(packet)
        packet.append((checksum >> 8) & 0xFF)  # High byte
        packet.append(checksum & 0xFF)  # Low byte
        
        return bytes(packet)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> Optional['Packet']:
        """Parse packet from bytes.
        
        Validates packet structure and checksum before creating Packet instance.
        
        Args:
            data: Raw bytes containing the packet
            
        Returns:
            Packet instance if valid, None if invalid or corrupted
        """
        if len(data) < 7:  # Minimum packet size
            return None
        
        if data[0] != 0x7E:  # Check start flag
            return None
        
        device_address = data[1]
        message_id = data[2]
        length = data[3]
        
        if len(data) < 6 + length:  # Check if we have full packet
            return None
        
        function_code = data[4]
        payload = data[5:4+length]
        
        # Verify checksum
        received_checksum = (data[4+length] << 8) | data[5+length]
        calculated_checksum = fletcher16(data[:4+length])
        
        if received_checksum != calculated_checksum:
            return None
        
        return cls(
            device_address=device_address,
            message_id=message_id,
            function_code=function_code,
            data=payload,
            checksum=received_checksum
        )


def fletcher16(data: bytes) -> int:
    """Calculate Fletcher-16 checksum for data integrity.
    
    Fletcher-16 is a position-dependent checksum algorithm that
    detects both single-bit errors and byte transpositions.
    
    Args:
        data: Bytes to calculate checksum for
        
    Returns:
        16-bit checksum value (sum2 in high byte, sum1 in low byte)
    """
    sum1 = 0  # Sum of all bytes
    sum2 = 0  # Sum of running sum1 values
    for b in data:
        sum1 = (sum1 + b) & 0xFF      # Add byte and wrap at 255
        sum2 = (sum2 + sum1) & 0xFF   # Add to running sum and wrap
    return (sum2 << 8) | sum1  # Combine into 16-bit value


def encode_word(value: int) -> bytes:
    """Encode 16-bit value as big-endian bytes"""
    return value.to_bytes(2, byteorder='big')


def decode_word(data: bytes, offset: int = 0) -> int:
    """Decode 16-bit value from big-endian bytes"""
    return int.from_bytes(data[offset:offset+2], byteorder='big')


class PacketBuilder:
    """Helper class to build protocol packets.
    
    Provides static methods to create properly formatted packets
    for each protocol operation. Handles encoding of multi-byte
    values in big-endian format.
    """
    
    @staticmethod
    def read_single_request(device_addr: int, msg_id: int, reg_addr: int) -> Packet:
        """Build read single register request.
        
        Args:
            device_addr: Target device address (0-247)
            msg_id: Message ID for response matching
            reg_addr: Register address to read (0-65535)
            
        Returns:
            Packet ready for transmission
        """
        data = encode_word(reg_addr)
        return Packet(device_addr, msg_id, FunctionCode.READ_SINGLE, data)
    
    @staticmethod
    def read_single_response(device_addr: int, msg_id: int, reg_addr: int, reg_value: int) -> Packet:
        """Build read single register response"""
        data = encode_word(reg_addr) + encode_word(reg_value)
        return Packet(device_addr, msg_id, FunctionCode.READ_SINGLE_RESP, data)
    
    @staticmethod
    def write_single_request(device_addr: int, msg_id: int, reg_addr: int, reg_value: int) -> Packet:
        """Build write single register request"""
        data = encode_word(reg_addr) + encode_word(reg_value)
        return Packet(device_addr, msg_id, FunctionCode.WRITE_SINGLE, data)
    
    @staticmethod
    def write_single_response(device_addr: int, msg_id: int, reg_addr: int, reg_value: int) -> Packet:
        """Build write single register response"""
        data = encode_word(reg_addr) + encode_word(reg_value)
        return Packet(device_addr, msg_id, FunctionCode.WRITE_SINGLE_RESP, data)
    
    @staticmethod
    def read_multiple_request(device_addr: int, msg_id: int, reg_addr: int, count: int) -> Packet:
        """Build read multiple registers request"""
        data = encode_word(reg_addr) + bytes([count])
        return Packet(device_addr, msg_id, FunctionCode.READ_MULTIPLE, data)
    
    @staticmethod
    def read_multiple_response(device_addr: int, msg_id: int, reg_addr: int, values: List[int]) -> Packet:
        """Build read multiple registers response"""
        data = encode_word(reg_addr) + bytes([len(values)])
        for value in values:
            data += encode_word(value)
        return Packet(device_addr, msg_id, FunctionCode.READ_MULTIPLE_RESP, data)
    
    @staticmethod
    def write_multiple_request(device_addr: int, msg_id: int, reg_addr: int, values: List[int]) -> Packet:
        """Build write multiple registers request"""
        data = encode_word(reg_addr) + bytes([len(values)])
        for value in values:
            data += encode_word(value)
        return Packet(device_addr, msg_id, FunctionCode.WRITE_MULTIPLE, data)
    
    @staticmethod
    def write_multiple_response(device_addr: int, msg_id: int, reg_addr: int, count: int) -> Packet:
        """Build write multiple registers response"""
        data = encode_word(reg_addr) + bytes([count])
        return Packet(device_addr, msg_id, FunctionCode.WRITE_MULTIPLE_RESP, data)
    
    @staticmethod
    def error_response(device_addr: int, msg_id: int, function_code: int, error_code: ErrorCode) -> Packet:
        """Build error response"""
        error_func = 0x80 | function_code
        data = bytes([error_code])
        return Packet(device_addr, msg_id, error_func, data)


class PacketParser:
    """Helper class to parse protocol packets"""
    
    @staticmethod
    def parse_request(packet: Packet) -> Optional[Dict[str, Any]]:
        """Parse request packet into structured data"""
        result = {
            'device_address': packet.device_address,
            'message_id': packet.message_id,
            'function_code': packet.function_code
        }
        
        if packet.function_code == FunctionCode.READ_SINGLE:
            if len(packet.data) >= 2:
                result['register_address'] = decode_word(packet.data)
                return result
                
        elif packet.function_code == FunctionCode.WRITE_SINGLE:
            if len(packet.data) >= 4:
                result['register_address'] = decode_word(packet.data, 0)
                result['register_value'] = decode_word(packet.data, 2)
                return result
                
        elif packet.function_code == FunctionCode.READ_MULTIPLE:
            if len(packet.data) >= 3:
                result['register_address'] = decode_word(packet.data, 0)
                result['count'] = packet.data[2]
                return result
                
        elif packet.function_code == FunctionCode.WRITE_MULTIPLE:
            if len(packet.data) >= 3:
                result['register_address'] = decode_word(packet.data, 0)
                result['count'] = packet.data[2]
                values = []
                for i in range(result['count']):
                    offset = 3 + (i * 2)
                    if offset + 1 < len(packet.data):
                        values.append(decode_word(packet.data, offset))
                result['values'] = values
                return result
        
        return None
    
    @staticmethod
    def parse_response(packet: Packet) -> Optional[Dict[str, Any]]:
        """Parse response packet into structured data"""
        result = {
            'device_address': packet.device_address,
            'message_id': packet.message_id,
            'function_code': packet.function_code
        }
        
        # Check for error response
        if packet.function_code & 0x80:
            result['is_error'] = True
            result['error_code'] = packet.data[0] if packet.data else 0
            result['error_description'] = PacketParser.get_error_description(result['error_code'])
            return result
        
        result['is_error'] = False
        
        if packet.function_code == FunctionCode.READ_SINGLE_RESP:
            if len(packet.data) >= 4:
                result['register_address'] = decode_word(packet.data, 0)
                result['register_value'] = decode_word(packet.data, 2)
                return result
                
        elif packet.function_code == FunctionCode.WRITE_SINGLE_RESP:
            if len(packet.data) >= 4:
                result['register_address'] = decode_word(packet.data, 0)
                result['register_value'] = decode_word(packet.data, 2)
                return result
                
        elif packet.function_code == FunctionCode.READ_MULTIPLE_RESP:
            if len(packet.data) >= 3:
                result['register_address'] = decode_word(packet.data, 0)
                result['count'] = packet.data[2]
                values = []
                for i in range(result['count']):
                    offset = 3 + (i * 2)
                    if offset + 1 < len(packet.data):
                        values.append(decode_word(packet.data, offset))
                result['values'] = values
                return result
                
        elif packet.function_code == FunctionCode.WRITE_MULTIPLE_RESP:
            if len(packet.data) >= 3:
                result['register_address'] = decode_word(packet.data, 0)
                result['count'] = packet.data[2]
                return result
        
        return None
    
    @staticmethod
    def get_error_description(error_code: int) -> str:
        """Get human-readable error description"""
        descriptions = {
            ErrorCode.INVALID_FUNCTION: "Invalid or unsupported function",
            ErrorCode.INVALID_ADDRESS: "Invalid register address",
            ErrorCode.INVALID_VALUE: "Invalid register value",
            ErrorCode.INTERNAL_ERROR: "Internal/unspecified error"
        }
        return descriptions.get(error_code, f"Unknown error (0x{error_code:02X})")


class RegisterMap:
    """Simulated register map for device mode.
    
    Represents a device's register memory space. Each register is
    16-bit (0-65535) and addressed by index. Used in Device tab
    to simulate an embedded device's register-based interface.
    """
    
    def __init__(self, size: int = 256):
        """Initialize register map with specified size.
        
        Args:
            size: Number of 16-bit registers (default 256)
        """
        self.size = size
        self.registers = [0] * size  # Initialize all registers to 0
    
    def read(self, address: int) -> Optional[int]:
        """Read single register"""
        if 0 <= address < self.size:
            return self.registers[address]
        return None
    
    def write(self, address: int, value: int) -> bool:
        """Write single register"""
        if 0 <= address < self.size and 0 <= value <= 0xFFFF:
            self.registers[address] = value
            return True
        return False
    
    def read_multiple(self, address: int, count: int) -> Optional[List[int]]:
        """Read multiple registers"""
        if 0 <= address < self.size and address + count <= self.size:
            return self.registers[address:address + count]
        return None
    
    def write_multiple(self, address: int, values: List[int]) -> bool:
        """Write multiple registers"""
        if 0 <= address < self.size and address + len(values) <= self.size:
            for i, value in enumerate(values):
                if not (0 <= value <= 0xFFFF):
                    return False
            for i, value in enumerate(values):
                self.registers[address + i] = value
            return True
        return False
    
    def clear(self):
        """Clear all registers to zero"""
        self.registers = [0] * self.size
    
    def get_all(self) -> List[int]:
        """Get all register values"""
        return self.registers.copy()