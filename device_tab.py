#!/usr/bin/env python3
"""
Device Tab - Simulates a slave device with register map
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import datetime
from typing import Optional, List, Dict, Any
from protocol import (
    Packet, PacketBuilder, PacketParser,
    FunctionCode, ErrorCode, RegisterMap
)


class DeviceTab:
    """Device (Slave) mode implementation for protocol testing.
    
    This tab simulates an embedded device with a register map that responds
    to protocol requests from a host. It processes incoming packets, manages
    a configurable register map, and sends appropriate responses.
    """
    
    def __init__(self, parent_frame: ttk.Frame, serial_port_getter, data_queue: queue.Queue):
        """
        Initialize Device Tab.
        
        Args:
            parent_frame: Parent Tkinter frame
            serial_port_getter: Callable that returns current serial port
            data_queue: Shared queue for serial data
        """
        self.frame = parent_frame
        self.get_serial_port = serial_port_getter
        self.data_queue = data_queue
        
        # Device state management
        self.device_address = 1  # This device's address (1-247)
        self.register_map = RegisterMap(size=256)  # Simulated register memory
        self.request_buffer = bytearray()  # Buffer for assembling incoming packets
        
        # Error simulation
        self.simulate_errors = tk.BooleanVar(value=False)
        self.error_type = tk.StringVar(value="none")
        
        # Statistics
        self.request_count = 0
        self.response_count = 0
        self.error_count = 0
        
        # Build UI
        self.create_widgets()
        
        # Start processing loop
        self.process_requests()
    
    def create_widgets(self):
        """Create Device tab UI elements"""
        # Main container
        main_frame = ttk.Frame(self.frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top controls frame
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Device Configuration (more compact layout)
        config_frame = ttk.LabelFrame(top_frame, text="Device Configuration", padding="5")
        config_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        
        # Device address and register size in single row
        addr_size_row = ttk.Frame(config_frame)
        addr_size_row.pack(fill=tk.X, pady=2)
        ttk.Label(addr_size_row, text="Addr:").pack(side=tk.LEFT)
        self.addr_var = tk.IntVar(value=self.device_address)
        addr_spin = ttk.Spinbox(addr_size_row, from_=1, to=247, textvariable=self.addr_var, width=5,
                                command=self.update_device_address)
        addr_spin.pack(side=tk.LEFT, padx=(2, 5))
        
        ttk.Label(addr_size_row, text="Size:").pack(side=tk.LEFT)
        self.map_size_var = tk.IntVar(value=256)
        size_spin = ttk.Spinbox(addr_size_row, from_=16, to=1024, textvariable=self.map_size_var, 
                                width=5, increment=16)
        size_spin.pack(side=tk.LEFT, padx=2)
        
        # Control buttons in two rows
        button_row1 = ttk.Frame(config_frame)
        button_row1.pack(fill=tk.X, pady=2)
        ttk.Button(button_row1, text="Resize", command=self.resize_register_map, width=8).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_row1, text="Clear", command=self.clear_registers, width=8).pack(side=tk.LEFT, padx=1)
        
        button_row2 = ttk.Frame(config_frame)
        button_row2.pack(fill=tk.X, pady=2)
        ttk.Button(button_row2, text="Test Pattern", command=self.load_test_pattern, width=17).pack()
        
        # Error Simulation (compact)
        error_frame = ttk.LabelFrame(top_frame, text="Error Simulation", padding="5")
        error_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        ttk.Checkbutton(error_frame, text="Enable Errors", 
                       variable=self.simulate_errors).pack(anchor=tk.W, pady=1)
        
        error_types = [
            ("No Error", "none"),
            ("Invalid Func", "invalid_function"),
            ("Invalid Addr", "invalid_address"),
            ("Invalid Val", "invalid_value"),
            ("Internal", "internal_error")
        ]
        
        for text, value in error_types:
            ttk.Radiobutton(error_frame, text=text, variable=self.error_type, 
                          value=value).pack(anchor=tk.W)
        
        # Statistics (compact)
        stats_frame = ttk.LabelFrame(top_frame, text="Statistics", padding="5")
        stats_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        self.stats_labels = {}
        for stat in ["Requests", "Responses", "Errors"]:
            row = ttk.Frame(stats_frame)
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=f"{stat}:", width=8).pack(side=tk.LEFT)
            label = ttk.Label(row, text="0", font=("Courier", 12), width=4)
            label.pack(side=tk.LEFT)
            self.stats_labels[stat] = label
        
        ttk.Button(stats_frame, text="Reset", command=self.reset_statistics, width=8).pack(pady=2)
        
        # Incoming Requests (expanded)
        incoming_frame = ttk.LabelFrame(top_frame, text="Incoming Requests", padding="5")
        incoming_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.incoming_request_log = scrolledtext.ScrolledText(incoming_frame, wrap=tk.WORD, height=8, width=45, font=("Courier", 14))
        self.incoming_request_log.pack(fill=tk.BOTH, expand=True)
        
        ttk.Button(incoming_frame, text="Clear", 
                  command=lambda: self.incoming_request_log.delete(1.0, tk.END)).pack(pady=2)
        
        # Outgoing Responses (expanded)
        outgoing_frame = ttk.LabelFrame(top_frame, text="Outgoing Responses", padding="5")
        outgoing_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.outgoing_response_log = scrolledtext.ScrolledText(outgoing_frame, wrap=tk.WORD, height=8, width=45, font=("Courier", 14))
        self.outgoing_response_log.pack(fill=tk.BOTH, expand=True)
        
        ttk.Button(outgoing_frame, text="Clear", 
                  command=lambda: self.outgoing_response_log.delete(1.0, tk.END)).pack(pady=2)
        
        # Middle section - Register Map Display
        middle_frame = ttk.Frame(main_frame)
        middle_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Register Map Display (now takes full width)
        reg_frame = ttk.LabelFrame(middle_frame, text="Register Map", padding="5")
        reg_frame.pack(fill=tk.BOTH, expand=True)
        
        # Register controls
        reg_control = ttk.Frame(reg_frame)
        reg_control.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(reg_control, text="Address (hex):").pack(side=tk.LEFT, padx=5)
        self.reg_edit_addr = tk.StringVar(value="0000")
        addr_entry = ttk.Entry(reg_control, textvariable=self.reg_edit_addr, width=8)
        addr_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(reg_control, text="Value (hex):").pack(side=tk.LEFT, padx=5)
        self.reg_edit_value = tk.StringVar(value="0000")
        value_entry = ttk.Entry(reg_control, textvariable=self.reg_edit_value, width=8)
        value_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(reg_control, text="Set", command=self.set_register).pack(side=tk.LEFT, padx=5)
        ttk.Button(reg_control, text="Refresh View", command=self.refresh_register_view).pack(side=tk.LEFT, padx=5)
        
        # Register display (scrolled text)
        self.register_display = scrolledtext.ScrolledText(reg_frame, wrap=tk.NONE, height=15, width=40,
                                                         font=("Courier", 14))
        self.register_display.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for the new log widgets
        self.incoming_request_log.tag_config("header", foreground="blue", font=("Courier", 15, "bold"))
        self.incoming_request_log.tag_config("data", foreground="black")
        self.incoming_request_log.tag_config("error", foreground="red")
        
        self.outgoing_response_log.tag_config("header", foreground="green", font=("Courier", 15, "bold"))
        self.outgoing_response_log.tag_config("data", foreground="black")
        self.outgoing_response_log.tag_config("error", foreground="red")
        
        # Initialize register view
        self.refresh_register_view()
    
    def update_device_address(self):
        """Update device address from UI"""
        self.device_address = self.addr_var.get()
    
    def resize_register_map(self):
        """Resize the register map"""
        new_size = self.map_size_var.get()
        if new_size != self.register_map.size:
            # Save existing values
            old_values = self.register_map.get_all()
            
            # Create new map
            self.register_map = RegisterMap(size=new_size)
            
            # Restore values that fit
            for i, value in enumerate(old_values[:new_size]):
                self.register_map.write(i, value)
            
            self.refresh_register_view()
            messagebox.showinfo("Success", f"Register map resized to {new_size} registers")
    
    def clear_registers(self):
        """Clear all registers to zero"""
        self.register_map.clear()
        self.refresh_register_view()
    
    def load_test_pattern(self):
        """Load a test pattern into registers"""
        for i in range(min(16, self.register_map.size)):
            # Create a pattern: address in high byte, counter in low byte
            value = ((i & 0xFF) << 8) | ((i * 0x11) & 0xFF)
            self.register_map.write(i, value)
        
        # Some specific test values
        if self.register_map.size > 16:
            self.register_map.write(0x10, 0x1234)
            self.register_map.write(0x11, 0xABCD)
            self.register_map.write(0x12, 0x5555)
            self.register_map.write(0x13, 0xAAAA)
        
        self.refresh_register_view()
    
    def set_register(self):
        """Set a single register value from UI"""
        try:
            addr = int(self.reg_edit_addr.get(), 16)
            value = int(self.reg_edit_value.get(), 16)
            
            if self.register_map.write(addr, value):
                self.refresh_register_view()
                # Highlight the changed register
                self.highlight_register(addr)
            else:
                messagebox.showerror("Error", f"Invalid address or value")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")
    
    def highlight_register(self, address: int):
        """Highlight a register in the display"""
        # Find the line with this address
        content = self.register_display.get(1.0, tk.END)
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith(f"{address:04X}:"):
                # Highlight this line
                line_start = f"{i+1}.0"
                line_end = f"{i+1}.end"
                self.register_display.tag_add("highlight", line_start, line_end)
                self.register_display.tag_config("highlight", background="yellow")
                self.register_display.see(line_start)
                # Remove highlight after 1 second
                self.frame.after(1000, lambda: self.register_display.tag_remove("highlight", "1.0", tk.END))
                break
    
    def refresh_register_view(self):
        """Refresh the register map display"""
        self.register_display.config(state=tk.NORMAL)
        self.register_display.delete(1.0, tk.END)
        
        # Display registers in rows of 8
        self.register_display.insert(tk.END, "Addr: Value  (Decimal)\n")
        self.register_display.insert(tk.END, "-" * 30 + "\n")
        
        for i in range(0, self.register_map.size, 8):
            for j in range(8):
                if i + j < self.register_map.size:
                    addr = i + j
                    value = self.register_map.read(addr)
                    self.register_display.insert(tk.END, f"{addr:04X}: {value:04X}  ({value:5d})\n")
        
        self.register_display.config(state=tk.DISABLED)
    
    def reset_statistics(self):
        """Reset statistics counters"""
        self.request_count = 0
        self.response_count = 0
        self.error_count = 0
        self.update_statistics()
    
    def update_statistics(self):
        """Update statistics display"""
        self.stats_labels["Requests"].config(text=str(self.request_count))
        self.stats_labels["Responses"].config(text=str(self.response_count))
        self.stats_labels["Errors"].config(text=str(self.error_count))
    
    def handle_raw_data(self, data: bytes):
        """Handle raw serial data from main thread.
        
        Called by the main serial reading thread when data is received.
        Adds data to buffer and attempts to extract complete packets.
        
        Args:
            data: Raw bytes received from serial port
        """
        try:
            # Debug: Show raw incoming data
            if len(data) > 0:
                timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                hex_str = " ".join(f"{b:02X}" for b in data)
                self.incoming_request_log.insert(tk.END, f"[{timestamp}] Raw Data: {hex_str}\n", "data")
                self.incoming_request_log.see(tk.END)
            
            self.request_buffer.extend(data)
            self.process_buffer()
        except Exception as e:
            print(f"Error handling raw data: {e}")
    
    def process_buffer(self):
        """Process the request buffer for complete packets.
        
        Scans the buffer for packet start flags (0x7E) and attempts to
        extract complete packets. Successfully parsed packets are passed
        to handle_request() for processing.
        """
        try:
            # Try to parse packets
            while len(self.request_buffer) > 0:
                # Look for start flag
                start_idx = self.request_buffer.find(0x7E)
                if start_idx == -1:
                    self.request_buffer.clear()
                    break
                
                # Remove data before start flag
                if start_idx > 0:
                    self.request_buffer = self.request_buffer[start_idx:]
                
                # Check if we have enough data for header
                if len(self.request_buffer) < 6:
                    break
                
                # Get message length
                msg_length = self.request_buffer[3]
                total_length = 6 + msg_length  # Header + data + checksum
                
                # Check if we have complete packet
                if len(self.request_buffer) < total_length:
                    break
                
                # Extract packet
                packet_data = bytes(self.request_buffer[:total_length])
                self.request_buffer = self.request_buffer[total_length:]
                
                # Parse packet
                packet = Packet.from_bytes(packet_data)
                if packet:
                    self.handle_request(packet)
                
        except Exception as e:
            print(f"Error processing buffer: {e}")
    
    def process_requests(self):
        """Legacy method - now just schedules next check"""
        # Schedule next check - reduced interval for better responsiveness
        self.frame.after(5, self.process_requests)
    
    def handle_request(self, packet: Packet):
        """Handle received request packet.
        
        Processes the request based on device address matching:
        - If address matches this device: process and respond
        - If broadcast (address 0): process but don't respond
        - If different address: log but ignore
        
        Args:
            packet: Parsed request packet from host
        """
        self.request_count += 1
        self.update_statistics()
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Log the request - ALWAYS show incoming messages
        self.incoming_request_log.insert(tk.END, f"[{timestamp}] Request (ID: {packet.message_id:02X}):\n", "header")
        
        # Display raw packet
        packet_bytes = packet.to_bytes()
        hex_str = " ".join(f"{b:02X}" for b in packet_bytes)
        self.incoming_request_log.insert(tk.END, f"  Raw: {hex_str}\n", "data")
        
        # Show device address info - but don't return early
        if packet.device_address != self.device_address and packet.device_address != 0:
            self.incoming_request_log.insert(tk.END, f"  Device Address: {packet.device_address} (not for this device: {self.device_address})\n", "data")
        elif packet.device_address == 0:
            self.incoming_request_log.insert(tk.END, f"  Device Address: {packet.device_address} (broadcast)\n", "data")
        else:
            self.incoming_request_log.insert(tk.END, f"  Device Address: {packet.device_address} (matches this device)\n", "data")
        
        # Parse request - always show what we received
        parsed = PacketParser.parse_request(packet)
        if not parsed:
            self.incoming_request_log.insert(tk.END, f"  Invalid request format\n\n", "error")
            self.incoming_request_log.see(tk.END)
            return
        
        # Display parsed request - ALWAYS show the content
        func = packet.function_code
        if func == FunctionCode.READ_SINGLE:
            self.incoming_request_log.insert(tk.END, 
                f"  Read Single: Address=0x{parsed['register_address']:04X}\n", "data")
        elif func == FunctionCode.WRITE_SINGLE:
            self.incoming_request_log.insert(tk.END, 
                f"  Write Single: Address=0x{parsed['register_address']:04X}, Value=0x{parsed['register_value']:04X}\n", "data")
        elif func == FunctionCode.READ_MULTIPLE:
            self.incoming_request_log.insert(tk.END, 
                f"  Read Multiple: Address=0x{parsed['register_address']:04X}, Count={parsed['count']}\n", "data")
        elif func == FunctionCode.WRITE_MULTIPLE:
            values_str = ", ".join(f"0x{v:04X}" for v in parsed.get('values', []))
            self.incoming_request_log.insert(tk.END, 
                f"  Write Multiple: Address=0x{parsed['register_address']:04X}, Count={parsed['count']}, Values=[{values_str}]\n", "data")
        
        # Now check if we should process and respond (only process for our address or broadcast)
        should_process = (packet.device_address == self.device_address or packet.device_address == 0)
        
        if should_process:
            self.incoming_request_log.insert(tk.END, f"  → Processing request\n", "data")
            
            # Process request and send response (if not broadcast)
            if packet.device_address != 0:
                response = self.process_request(packet, parsed)
                if response:
                    self.send_response(response)
            else:
                # For broadcast, just process without responding
                self.process_request(packet, parsed)
                self.incoming_request_log.insert(tk.END, "  → Broadcast - no response sent\n", "data")
        else:
            self.incoming_request_log.insert(tk.END, f"  → Not processing (wrong device address)\n", "data")
        
        self.incoming_request_log.insert(tk.END, "\n")
        self.incoming_request_log.see(tk.END)
    
    def process_request(self, packet: Packet, parsed: Dict[str, Any]) -> Optional[Packet]:
        """Process request and generate response.
        
        Executes the requested operation on the register map and creates
        an appropriate response packet. Handles error simulation if enabled.
        
        Args:
            packet: Original request packet
            parsed: Parsed request data from PacketParser
            
        Returns:
            Response packet to send back, or None for broadcast
        """
        # Check for error simulation
        if self.simulate_errors.get():
            error_type = self.error_type.get()
            if error_type != "none":
                self.error_count += 1
                self.update_statistics()
                
                error_map = {
                    "invalid_function": ErrorCode.INVALID_FUNCTION,
                    "invalid_address": ErrorCode.INVALID_ADDRESS,
                    "invalid_value": ErrorCode.INVALID_VALUE,
                    "internal_error": ErrorCode.INTERNAL_ERROR
                }
                error_code = error_map.get(error_type, ErrorCode.INTERNAL_ERROR)
                return PacketBuilder.error_response(
                    self.device_address, packet.message_id, packet.function_code, error_code
                )
        
        # Process based on function code
        func = packet.function_code
        
        if func == FunctionCode.READ_SINGLE:
            addr = parsed['register_address']
            value = self.register_map.read(addr)
            if value is not None:
                return PacketBuilder.read_single_response(
                    self.device_address, packet.message_id, addr, value
                )
            else:
                self.error_count += 1
                self.update_statistics()
                return PacketBuilder.error_response(
                    self.device_address, packet.message_id, func, ErrorCode.INVALID_ADDRESS
                )
        
        elif func == FunctionCode.WRITE_SINGLE:
            addr = parsed['register_address']
            value = parsed['register_value']
            if self.register_map.write(addr, value):
                self.refresh_register_view()
                self.highlight_register(addr)
                return PacketBuilder.write_single_response(
                    self.device_address, packet.message_id, addr, value
                )
            else:
                self.error_count += 1
                self.update_statistics()
                return PacketBuilder.error_response(
                    self.device_address, packet.message_id, func, ErrorCode.INVALID_ADDRESS
                )
        
        elif func == FunctionCode.READ_MULTIPLE:
            addr = parsed['register_address']
            count = parsed['count']
            values = self.register_map.read_multiple(addr, count)
            if values is not None:
                return PacketBuilder.read_multiple_response(
                    self.device_address, packet.message_id, addr, values
                )
            else:
                self.error_count += 1
                self.update_statistics()
                return PacketBuilder.error_response(
                    self.device_address, packet.message_id, func, ErrorCode.INVALID_ADDRESS
                )
        
        elif func == FunctionCode.WRITE_MULTIPLE:
            addr = parsed['register_address']
            values = parsed.get('values', [])
            if self.register_map.write_multiple(addr, values):
                self.refresh_register_view()
                for i in range(len(values)):
                    self.highlight_register(addr + i)
                return PacketBuilder.write_multiple_response(
                    self.device_address, packet.message_id, addr, len(values)
                )
            else:
                self.error_count += 1
                self.update_statistics()
                return PacketBuilder.error_response(
                    self.device_address, packet.message_id, func, ErrorCode.INVALID_ADDRESS
                )
        
        else:
            # Unsupported function
            self.error_count += 1
            self.update_statistics()
            return PacketBuilder.error_response(
                self.device_address, packet.message_id, func, ErrorCode.INVALID_FUNCTION
            )
    
    def send_response(self, response: Packet):
        """Send response packet back to host.
        
        Transmits the response packet via serial port and logs the
        transaction in the outgoing response display.
        
        Args:
            response: Response packet to transmit
        """
        serial_port = self.get_serial_port()
        if not serial_port or not serial_port.is_open:
            return
        
        try:
            response_bytes = response.to_bytes()
            serial_port.write(response_bytes)
            
            self.response_count += 1
            self.update_statistics()
            
            # Log the response
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.outgoing_response_log.insert(tk.END, f"[{timestamp}] Response (ID: {response.message_id:02X}):\n", "header")
            
            # Display raw packet
            hex_str = " ".join(f"{b:02X}" for b in response_bytes)
            self.outgoing_response_log.insert(tk.END, f"  Raw: {hex_str}\n", "data")
            
            # Display parsed response
            if response.function_code & 0x80:
                # Error response
                error_code = response.data[0] if response.data else 0
                desc = PacketParser.get_error_description(error_code)
                self.outgoing_response_log.insert(tk.END, f"  Error Response: {desc}\n", "error")
            else:
                # Normal response
                func_names = {
                    FunctionCode.READ_SINGLE_RESP: "Read Single Response",
                    FunctionCode.WRITE_SINGLE_RESP: "Write Single Response",
                    FunctionCode.READ_MULTIPLE_RESP: "Read Multiple Response",
                    FunctionCode.WRITE_MULTIPLE_RESP: "Write Multiple Response"
                }
                func_name = func_names.get(response.function_code, "Unknown")
                self.outgoing_response_log.insert(tk.END, f"  {func_name}\n", "data")
            
            self.outgoing_response_log.insert(tk.END, "\n")
            self.outgoing_response_log.see(tk.END)
            
        except Exception as e:
            self.outgoing_response_log.insert(tk.END, f"  Send error: {str(e)}\n\n", "error")
            self.outgoing_response_log.see(tk.END)