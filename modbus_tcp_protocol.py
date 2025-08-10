#!/usr/bin/env python3
"""
Modbus TCP Protocol implementation for 16-bit register operations
Supports Multi Read (0x03) and Multi Write (0x10) function codes
"""

import struct
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import IntEnum


class ModbusFunctionCode(IntEnum):
    """Modbus function codes for 16-bit register operations"""
    READ_HOLDING_REGISTERS = 0x03    # Read multiple 16-bit registers
    WRITE_MULTIPLE_REGISTERS = 0x10  # Write multiple 16-bit registers


class ModbusException(IntEnum):
    """Modbus exception codes"""
    ILLEGAL_FUNCTION = 0x01
    ILLEGAL_DATA_ADDRESS = 0x02
    ILLEGAL_DATA_VALUE = 0x03
    SLAVE_DEVICE_FAILURE = 0x04


@dataclass
class ModbusTCPFrame:
    """Modbus TCP Application Data Unit (ADU)"""
    transaction_id: int    # 2 bytes - Transaction identifier
    protocol_id: int      # 2 bytes - Protocol identifier (0x0000 for Modbus)
    length: int           # 2 bytes - Length of remaining bytes
    unit_id: int          # 1 byte - Unit identifier (slave address)
    function_code: int    # 1 byte - Function code
    data: bytes          # Variable length data
    
    def to_bytes(self) -> bytes:
        """Convert frame to bytes for transmission"""
        # MBAP Header (7 bytes) + PDU data
        mbap_header = struct.pack('>HHHB', 
                                 self.transaction_id,
                                 self.protocol_id,
                                 self.length,
                                 self.unit_id)
        pdu = struct.pack('B', self.function_code) + self.data
        return mbap_header + pdu
    
    @classmethod
    def from_bytes(cls, data: bytes) -> Optional['ModbusTCPFrame']:
        """Parse frame from bytes"""
        if len(data) < 8:  # Minimum frame size (MBAP + function code)
            return None
        
        try:
            # Parse MBAP header
            transaction_id, protocol_id, length, unit_id = struct.unpack('>HHHB', data[:7])
            
            # Validate protocol ID
            if protocol_id != 0x0000:
                return None
                
            # Check if we have complete frame
            if len(data) < 6 + length:
                return None
            
            # Extract PDU
            function_code = data[7]
            pdu_data = data[8:6+length]
            
            return cls(
                transaction_id=transaction_id,
                protocol_id=protocol_id,
                length=length,
                unit_id=unit_id,
                function_code=function_code,
                data=pdu_data
            )
        except struct.error:
            return None


class ModbusRegisterMap:
    """16-bit register map for Modbus devices"""
    
    def __init__(self, size: int = 1000):
        """Initialize register map
        
        Args:
            size: Number of 16-bit registers (default 1000)
        """
        self.size = size
        self.registers = [0] * size  # Initialize all registers to 0
    
    def read_registers(self, start_address: int, count: int) -> Optional[List[int]]:
        """Read multiple 16-bit registers
        
        Args:
            start_address: Starting register address (0-based)
            count: Number of registers to read
            
        Returns:
            List of register values or None if invalid
        """
        if start_address < 0 or start_address >= self.size:
            return None
        if count < 1 or count > 125:  # Modbus limit
            return None
        if start_address + count > self.size:
            return None
            
        return self.registers[start_address:start_address + count]
    
    def write_registers(self, start_address: int, values: List[int]) -> bool:
        """Write multiple 16-bit registers
        
        Args:
            start_address: Starting register address (0-based)
            values: List of values to write
            
        Returns:
            True if successful, False if invalid
        """
        if start_address < 0 or start_address >= self.size:
            return False
        if len(values) < 1 or len(values) > 123:  # Modbus limit
            return False
        if start_address + len(values) > self.size:
            return False
            
        # Validate all values are 16-bit
        for value in values:
            if not (0 <= value <= 0xFFFF):
                return False
        
        # Write values
        for i, value in enumerate(values):
            self.registers[start_address + i] = value
            
        return True
    
    def get_register(self, address: int) -> int:
        """Get single register value
        
        Args:
            address: Register address (0-based)
            
        Returns:
            Register value (0-65535) or 0 if invalid address
        """
        if 0 <= address < self.size:
            return self.registers[address]
        return 0
    
    def set_register(self, address: int, value: int) -> bool:
        """Set single register value
        
        Args:
            address: Register address (0-based)
            value: Value to set (0-65535)
            
        Returns:
            True if successful, False if invalid
        """
        if 0 <= address < self.size and 0 <= value <= 0xFFFF:
            self.registers[address] = value
            return True
        return False
    
    def clear(self):
        """Clear all registers to zero"""
        self.registers = [0] * self.size
    
    def get_all(self) -> List[int]:
        """Get all register values"""
        return self.registers.copy()


class ModbusTCPBuilder:
    """Helper class to build Modbus TCP frames"""
    
    @staticmethod
    def read_holding_registers_request(transaction_id: int, unit_id: int, 
                                     start_address: int, count: int) -> ModbusTCPFrame:
        """Build read holding registers request"""
        data = struct.pack('>HH', start_address, count)
        return ModbusTCPFrame(
            transaction_id=transaction_id,
            protocol_id=0x0000,
            length=len(data) + 2,  # data + unit_id + function_code
            unit_id=unit_id,
            function_code=ModbusFunctionCode.READ_HOLDING_REGISTERS,
            data=data
        )
    
    @staticmethod
    def read_holding_registers_response(transaction_id: int, unit_id: int, 
                                      values: List[int]) -> ModbusTCPFrame:
        """Build read holding registers response"""
        byte_count = len(values) * 2
        data = struct.pack('B', byte_count)
        for value in values:
            data += struct.pack('>H', value)
        
        return ModbusTCPFrame(
            transaction_id=transaction_id,
            protocol_id=0x0000,
            length=len(data) + 2,  # data + unit_id + function_code
            unit_id=unit_id,
            function_code=ModbusFunctionCode.READ_HOLDING_REGISTERS,
            data=data
        )
    
    @staticmethod
    def write_multiple_registers_request(transaction_id: int, unit_id: int,
                                       start_address: int, values: List[int]) -> ModbusTCPFrame:
        """Build write multiple registers request"""
        count = len(values)
        byte_count = count * 2
        data = struct.pack('>HHB', start_address, count, byte_count)
        for value in values:
            data += struct.pack('>H', value)
        
        return ModbusTCPFrame(
            transaction_id=transaction_id,
            protocol_id=0x0000,
            length=len(data) + 2,  # data + unit_id + function_code
            unit_id=unit_id,
            function_code=ModbusFunctionCode.WRITE_MULTIPLE_REGISTERS,
            data=data
        )
    
    @staticmethod
    def write_multiple_registers_response(transaction_id: int, unit_id: int,
                                        start_address: int, count: int) -> ModbusTCPFrame:
        """Build write multiple registers response"""
        data = struct.pack('>HH', start_address, count)
        return ModbusTCPFrame(
            transaction_id=transaction_id,
            protocol_id=0x0000,
            length=len(data) + 2,  # data + unit_id + function_code
            unit_id=unit_id,
            function_code=ModbusFunctionCode.WRITE_MULTIPLE_REGISTERS,
            data=data
        )
    
    @staticmethod
    def exception_response(transaction_id: int, unit_id: int, 
                         function_code: int, exception_code: int) -> ModbusTCPFrame:
        """Build exception response"""
        error_function = 0x80 | function_code  # Set error bit
        data = struct.pack('B', exception_code)
        return ModbusTCPFrame(
            transaction_id=transaction_id,
            protocol_id=0x0000,
            length=len(data) + 2,  # data + unit_id + function_code
            unit_id=unit_id,
            function_code=error_function,
            data=data
        )


class ModbusTCPParser:
    """Helper class to parse Modbus TCP frames"""
    
    @staticmethod
    def parse_read_holding_registers_request(frame: ModbusTCPFrame) -> Optional[Dict[str, Any]]:
        """Parse read holding registers request"""
        if frame.function_code != ModbusFunctionCode.READ_HOLDING_REGISTERS:
            return None
        if len(frame.data) < 4:
            return None
            
        try:
            start_address, count = struct.unpack('>HH', frame.data[:4])
            return {
                'function': 'read_holding_registers',
                'start_address': start_address,
                'count': count
            }
        except struct.error:
            return None
    
    @staticmethod
    def parse_read_holding_registers_response(frame: ModbusTCPFrame) -> Optional[Dict[str, Any]]:
        """Parse read holding registers response"""
        if frame.function_code != ModbusFunctionCode.READ_HOLDING_REGISTERS:
            return None
        if len(frame.data) < 1:
            return None
            
        try:
            byte_count = frame.data[0]
            if len(frame.data) < 1 + byte_count:
                return None
            
            values = []
            for i in range(0, byte_count, 2):
                value = struct.unpack('>H', frame.data[1+i:3+i])[0]
                values.append(value)
            
            return {
                'function': 'read_holding_registers_response',
                'values': values
            }
        except struct.error:
            return None
    
    @staticmethod
    def parse_write_multiple_registers_request(frame: ModbusTCPFrame) -> Optional[Dict[str, Any]]:
        """Parse write multiple registers request"""
        if frame.function_code != ModbusFunctionCode.WRITE_MULTIPLE_REGISTERS:
            return None
        if len(frame.data) < 5:
            return None
            
        try:
            start_address, count, byte_count = struct.unpack('>HHB', frame.data[:5])
            if len(frame.data) < 5 + byte_count:
                return None
            
            values = []
            for i in range(0, byte_count, 2):
                value = struct.unpack('>H', frame.data[5+i:7+i])[0]
                values.append(value)
            
            return {
                'function': 'write_multiple_registers',
                'start_address': start_address,
                'count': count,
                'values': values
            }
        except struct.error:
            return None
    
    @staticmethod
    def parse_write_multiple_registers_response(frame: ModbusTCPFrame) -> Optional[Dict[str, Any]]:
        """Parse write multiple registers response"""
        if frame.function_code != ModbusFunctionCode.WRITE_MULTIPLE_REGISTERS:
            return None
        if len(frame.data) < 4:
            return None
            
        try:
            start_address, count = struct.unpack('>HH', frame.data[:4])
            return {
                'function': 'write_multiple_registers_response',
                'start_address': start_address,
                'count': count
            }
        except struct.error:
            return None
    
    @staticmethod
    def parse_exception_response(frame: ModbusTCPFrame) -> Optional[Dict[str, Any]]:
        """Parse exception response"""
        if not (frame.function_code & 0x80):  # Check error bit
            return None
        if len(frame.data) < 1:
            return None
            
        original_function = frame.function_code & 0x7F
        exception_code = frame.data[0]
        
        exception_names = {
            ModbusException.ILLEGAL_FUNCTION: "Illegal Function",
            ModbusException.ILLEGAL_DATA_ADDRESS: "Illegal Data Address",
            ModbusException.ILLEGAL_DATA_VALUE: "Illegal Data Value",
            ModbusException.SLAVE_DEVICE_FAILURE: "Slave Device Failure"
        }
        
        return {
            'function': 'exception_response',
            'original_function': original_function,
            'exception_code': exception_code,
            'exception_name': exception_names.get(exception_code, f"Unknown (0x{exception_code:02X})")
        }
    
    @staticmethod
    def get_function_name(function_code: int) -> str:
        """Get human-readable function name"""
        if function_code & 0x80:
            return f"Exception Response (0x{function_code:02X})"
        
        names = {
            ModbusFunctionCode.READ_HOLDING_REGISTERS: "Read Holding Registers (0x03)",
            ModbusFunctionCode.WRITE_MULTIPLE_REGISTERS: "Write Multiple Registers (0x10)"
        }
        return names.get(function_code, f"Unknown Function (0x{function_code:02X})")