# Modbus TCP Implementation for SerialCOM Tool

## Overview

The SerialCOM Tool has been enhanced with two new tabs for Modbus TCP communication:

- **🌐 Modbus TCP Slave** - Acts as a TCP server accepting connections from clients
- **🔌 Modbus TCP Master** - Acts as a TCP client connecting to servers

Both tabs support **Multi Read 16-bit registers (0x03)** and **Multi Write 16-bit registers (0x10)** function codes only, as requested.

## Features

### Modbus TCP Slave (Server)
- **Socket Server**: Opens a socket server on configurable IP address and port (default: 127.0.0.1:502)
- **Register Map**: Maintains up to 1000 16-bit registers (configurable)
- **Function Codes Supported**:
  - 0x03: Read Holding Registers (Multi Read 16-bit)
  - 0x10: Write Multiple Registers (Multi Write 16-bit)
- **Error Simulation**: Can simulate various Modbus exceptions for testing
- **Statistics**: Tracks connections, requests, responses, and errors
- **Register Management**: Set individual registers, clear all, load test patterns, export to CSV
- **Comprehensive Logging**: All requests and responses with timestamps

### Modbus TCP Master (Client)
- **TCP Client**: Connects to any Modbus TCP server
- **Function Codes Supported**:
  - 0x03: Read Holding Registers (Multi Read 16-bit)
  - 0x10: Write Multiple Registers (Multi Write 16-bit)
- **Request Builder**: Visual request configuration with real-time preview
- **Transaction Management**: Automatic transaction ID handling
- **Timeout Handling**: Configurable response timeout with timeout detection
- **Statistics**: Tracks requests, responses, timeouts, and errors
- **Response Logging**: Detailed logging of all communication

## Usage Instructions

### Setting up a Modbus TCP Slave

1. **Launch the SerialCOM Tool** and click on the **"🌐 Modbus TCP Slave"** tab
2. **Configure Server Settings**:
   - IP Address: 127.0.0.1 (localhost) or your network IP
   - Port: 502 (standard Modbus TCP port) or any available port
   - Unit ID: 1-247 (device identifier)
3. **Start the Server**: Click "Start Server"
4. **Register Management**:
   - Set individual registers using Address/Value fields
   - Load test patterns for demonstration
   - Clear all registers to zero
   - Export register values to CSV

### Setting up a Modbus TCP Master

1. **Launch the SerialCOM Tool** and click on the **"🔌 Modbus TCP Master"** tab
2. **Configure Connection**:
   - Server IP: IP address of the Modbus TCP slave (e.g., 127.0.0.1)
   - Server Port: Port of the Modbus TCP slave (e.g., 502)
   - Unit ID: Target device ID (1-247)
3. **Connect**: Click "Connect" to establish connection
4. **Send Requests**:
   - **Multi Read**: Select address and count of registers to read
   - **Multi Write**: Specify address and comma-separated hex values (e.g., 0000,1111,2222)
5. **Monitor**: View real-time request preview and response logging

### Testing Communication

1. **Start a Slave**: Configure and start the Modbus TCP Slave on port 502
2. **Connect a Master**: Configure the Master to connect to 127.0.0.1:502
3. **Load Test Data**: In the Slave, click "Load Test Pattern" to populate registers
4. **Read Registers**: In the Master, set address to 0000, count to 10, and send a read request
5. **Write Registers**: In the Master, set address to 0010, values to "AAAA,BBBB,CCCC" and send a write request
6. **Monitor Logs**: Both tabs show detailed communication logs with timestamps

## Protocol Details

### Modbus TCP Frame Format
```
[Transaction ID][Protocol ID][Length][Unit ID][Function Code][Data...]
     2 bytes      2 bytes    2 bytes  1 byte     1 byte      Variable
```

### Supported Function Codes
- **0x03**: Read Holding Registers (Multi Read 16-bit)
  - Request: Start Address (2 bytes) + Count (2 bytes)
  - Response: Byte Count (1 byte) + Register Values (2 bytes each)
  
- **0x10**: Write Multiple Registers (Multi Write 16-bit)  
  - Request: Start Address (2 bytes) + Count (2 bytes) + Byte Count (1 byte) + Values (2 bytes each)
  - Response: Start Address (2 bytes) + Count (2 bytes)

### Error Handling
- Proper Modbus exception responses (0x81, 0x83, 0x90)
- Exception codes: Illegal Function, Illegal Address, Illegal Value, Device Failure
- Network error handling and automatic disconnection
- Timeout detection with configurable timeouts

## Technical Implementation

### Files Added
- `modbus_tcp_protocol.py` - Core Modbus TCP protocol implementation
- `modbus_tcp_slave_tab.py` - Slave (Server) GUI and functionality  
- `modbus_tcp_master_tab.py` - Master (Client) GUI and functionality
- `test_modbus_tcp.py` - Comprehensive test suite

### Key Classes
- `ModbusTCPFrame` - Frame encoding/decoding
- `ModbusTCPBuilder` - Request/response frame construction
- `ModbusTCPParser` - Frame parsing and validation
- `ModbusRegisterMap` - 16-bit register storage and management
- `ModbusTCPSlaveTab` - Server GUI and socket handling
- `ModbusTCPMasterTab` - Client GUI and communication

### Threading
- Slave uses separate threads for server socket and client handling
- Master uses separate threads for response reception
- All GUI updates are thread-safe using proper synchronization

## Testing

Run the test suite to verify functionality:
```bash
python test_modbus_tcp.py
```

The test suite validates:
- Register map operations
- Frame encoding/decoding
- Request/response parsing
- Exception handling
- Protocol compliance

## Network Configuration

- **Default Port**: 502 (standard Modbus TCP port)
- **Local Testing**: Use 127.0.0.1 for same-machine communication
- **Network Testing**: Use actual IP addresses for network communication
- **Firewall**: Ensure the chosen port is not blocked by firewall
- **Multiple Clients**: Slave supports one client connection at a time

## Limitations

- **Function Codes**: Only supports 0x03 (Multi Read) and 0x10 (Multi Write) as requested
- **Data Types**: Only 16-bit registers (no coils, discrete inputs, or input registers)
- **Concurrent Clients**: Slave accepts one client connection at a time
- **Register Addressing**: 0-based addressing (register 0 = address 0x0000)

## Integration

The Modbus TCP implementation seamlessly integrates with the existing SerialCOM Tool:
- Follows the same UI design patterns as existing protocol tabs
- Uses consistent color schemes and layouts
- Integrates with the font size controls
- Maintains the same logging and error handling patterns