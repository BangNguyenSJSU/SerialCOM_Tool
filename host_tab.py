#!/usr/bin/env python3
"""
Host Tab - Acts as master for register read/write operations
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


class HostTab:
    """Host (Master) mode implementation for protocol testing.
    
    This tab acts as a protocol master, sending register read/write requests
    to devices and handling their responses. It provides a UI for configuring
    requests, tracks pending requests for timeout handling, and logs all
    communication.
    """
    
    def __init__(self, parent_frame: ttk.Frame, serial_port_getter, data_queue: queue.Queue):
        """
        Initialize Host Tab.
        
        Args:
            parent_frame: Parent Tkinter frame
            serial_port_getter: Callable that returns current serial port
            data_queue: Shared queue for serial data
        """
        self.frame = parent_frame
        self.get_serial_port = serial_port_getter
        self.data_queue = data_queue
        
        # Protocol state management
        self.message_id = 0  # Current message ID (auto-increments)
        self.pending_requests: Dict[int, Dict[str, Any]] = {}  # Track requests awaiting responses
        self.response_timeout = 500  # Response timeout in milliseconds
        
        # Response handling
        self.response_buffer = bytearray()
        
        # Build UI
        self.create_widgets()
        
        # Start processing loop
        self.process_responses()
    
    def create_widgets(self):
        """Create Host tab UI elements"""
        # Main container with padding
        main_frame = ttk.Frame(self.frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Device Address Section
        addr_frame = ttk.LabelFrame(main_frame, text="Device Address", padding="5")
        addr_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(addr_frame, text="Address (0-247):").pack(side=tk.LEFT, padx=5)
        self.device_addr_var = tk.IntVar(value=1)
        self.device_addr_spin = ttk.Spinbox(
            addr_frame, from_=0, to=247, textvariable=self.device_addr_var, width=10
        )
        self.device_addr_spin.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(addr_frame, text="(0 = Broadcast)").pack(side=tk.LEFT, padx=5)
        
        # Message ID Input
        ttk.Label(addr_frame, text="Message ID:").pack(side=tk.LEFT, padx=(20, 5))
        self.msg_id_var = tk.StringVar(value=f"{self.message_id:02X}")
        self.msg_id_entry = ttk.Entry(addr_frame, textvariable=self.msg_id_var, width=4, font=("Courier", 14))
        self.msg_id_entry.pack(side=tk.LEFT, padx=5)
        self.msg_id_var.trace('w', self.on_message_id_change)
        
        ttk.Label(addr_frame, text="(00-FF hex)").pack(side=tk.LEFT, padx=5)
        
        # Operation Selection
        op_frame = ttk.LabelFrame(main_frame, text="Register Operation", padding="5")
        op_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Operation type radio buttons in a single row
        self.operation_var = tk.StringVar(value="read_single")
        operations = [
            ("Read Single (0x01)", "read_single"),
            ("Write Single (0x02)", "write_single"),
            ("Read Multiple (0x03)", "read_multiple"),
            ("Write Multiple (0x04)", "write_multiple")
        ]
        
        op_row = ttk.Frame(op_frame)
        op_row.pack(fill=tk.X, pady=2)
        
        for text, value in operations:
            ttk.Radiobutton(
                op_row, text=text, variable=self.operation_var, value=value,
                command=self.on_operation_change
            ).pack(side=tk.LEFT, padx=(0, 15))
        
        # Parameters Frame
        params_frame = ttk.LabelFrame(main_frame, text="Parameters", padding="5")
        params_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Register Address
        addr_row = ttk.Frame(params_frame)
        addr_row.pack(fill=tk.X, pady=2)
        ttk.Label(addr_row, text="Register Address (hex):").pack(side=tk.LEFT, padx=5)
        self.reg_addr_var = tk.StringVar(value="0000")
        self.reg_addr_entry = ttk.Entry(addr_row, textvariable=self.reg_addr_var, width=10)
        self.reg_addr_entry.pack(side=tk.LEFT, padx=5)
        
        # Register Value (for write operations)
        self.value_row = ttk.Frame(params_frame)
        self.value_row.pack(fill=tk.X, pady=2)
        ttk.Label(self.value_row, text="Register Value (hex):").pack(side=tk.LEFT, padx=5)
        self.reg_value_var = tk.StringVar(value="0000")
        self.reg_value_entry = ttk.Entry(self.value_row, textvariable=self.reg_value_var, width=10)
        self.reg_value_entry.pack(side=tk.LEFT, padx=5)
        
        # Count (for multiple operations)
        self.count_row = ttk.Frame(params_frame)
        self.count_row.pack(fill=tk.X, pady=2)
        ttk.Label(self.count_row, text="Count (1-255):").pack(side=tk.LEFT, padx=5)
        self.count_var = tk.IntVar(value=1)
        self.count_spin = ttk.Spinbox(self.count_row, from_=1, to=255, textvariable=self.count_var, width=10)
        self.count_spin.pack(side=tk.LEFT, padx=5)
        
        # Multiple values (for write multiple)
        self.values_row = ttk.Frame(params_frame)
        self.values_row.pack(fill=tk.X, pady=2)
        ttk.Label(self.values_row, text="Values (hex, comma-separated):").pack(side=tk.LEFT, padx=5)
        self.values_var = tk.StringVar(value="0000,0001,0002")
        self.values_entry = ttk.Entry(self.values_row, textvariable=self.values_var, width=30)
        self.values_entry.pack(side=tk.LEFT, padx=5)
        
        # Control Buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.send_btn = ttk.Button(control_frame, text="Send Request", command=self.send_request)
        self.send_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Clear Log", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        
        # Timeout setting
        ttk.Label(control_frame, text="Timeout (ms):").pack(side=tk.LEFT, padx=(20, 5))
        self.timeout_var = tk.IntVar(value=self.response_timeout)
        timeout_spin = ttk.Spinbox(control_frame, from_=100, to=5000, textvariable=self.timeout_var, 
                                   width=10, increment=100)
        timeout_spin.pack(side=tk.LEFT, padx=5)
        self.timeout_var.trace('w', lambda *args: setattr(self, 'response_timeout', self.timeout_var.get()))
        
        # Packet Preview
        preview_frame = ttk.LabelFrame(main_frame, text="Packet Preview", padding="5")
        preview_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.preview_text = tk.Text(preview_frame, height=3, width=80, font=("Courier", 14))
        self.preview_text.pack(fill=tk.X)
        
        # Communication Log
        log_frame = ttk.LabelFrame(main_frame, text="Communication Log", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create log with scrollbar
        self.log_display = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15, font=("Courier", 14))
        self.log_display.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for coloring
        self.log_display.tag_config("request", foreground="blue")
        self.log_display.tag_config("response", foreground="green")
        self.log_display.tag_config("error", foreground="red")
        self.log_display.tag_config("timeout", foreground="orange")
        self.log_display.tag_config("system", foreground="gray")
        
        # Initially hide unused fields
        self.on_operation_change()
    
    def on_message_id_change(self, *args):
        """Handle message ID field changes with validation"""
        try:
            # Get the current value
            value = self.msg_id_var.get().strip().upper()
            
            # Allow empty or partial input during editing
            if not value:
                return
            
            # Validate hex format and range
            if len(value) <= 2 and all(c in '0123456789ABCDEF' for c in value):
                msg_id = int(value, 16)
                if 0 <= msg_id <= 255:
                    self.message_id = msg_id
                    self.update_preview()
                    return
            
            # If invalid, revert to last valid value
            self.msg_id_var.set(f"{self.message_id:02X}")
        except ValueError:
            # Revert to last valid value on error
            self.msg_id_var.set(f"{self.message_id:02X}")
    
    def on_operation_change(self):
        """Handle operation type change"""
        operation = self.operation_var.get()
        
        # Hide all optional fields first
        self.value_row.pack_forget()
        self.count_row.pack_forget()
        self.values_row.pack_forget()
        
        # Show relevant fields
        if operation == "write_single":
            self.value_row.pack(fill=tk.X, pady=2, after=self.reg_addr_entry.master)
        elif operation == "read_multiple":
            self.count_row.pack(fill=tk.X, pady=2, after=self.reg_addr_entry.master)
        elif operation == "write_multiple":
            self.count_row.pack(fill=tk.X, pady=2, after=self.reg_addr_entry.master)
            self.values_row.pack(fill=tk.X, pady=2, after=self.count_row)
        
        # Update preview
        self.update_preview()
    
    def update_preview(self):
        """Update packet preview based on current settings"""
        try:
            packet = self.build_packet()
            if packet:
                packet_bytes = packet.to_bytes()
                
                # Format as hex
                hex_str = " ".join(f"{b:02X}" for b in packet_bytes)
                
                # Add ASCII representation
                ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in packet_bytes)
                
                # Update preview
                self.preview_text.delete(1.0, tk.END)
                self.preview_text.insert(tk.END, f"Hex: {hex_str}\n")
                self.preview_text.insert(tk.END, f"ASCII: {ascii_str}\n")
                self.preview_text.insert(tk.END, f"Length: {len(packet_bytes)} bytes")
        except Exception as e:
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, f"Error: {str(e)}")
    
    def build_packet(self) -> Optional[Packet]:
        """Build packet based on current UI settings.
        
        Reads the current UI configuration and creates the appropriate
        packet for the selected operation type.
        
        Returns:
            Configured packet ready for transmission, or None if invalid
        """
        try:
            device_addr = self.device_addr_var.get()
            operation = self.operation_var.get()
            
            # Parse register address
            reg_addr = int(self.reg_addr_var.get(), 16)
            
            if operation == "read_single":
                return PacketBuilder.read_single_request(device_addr, self.message_id, reg_addr)
                
            elif operation == "write_single":
                reg_value = int(self.reg_value_var.get(), 16)
                return PacketBuilder.write_single_request(device_addr, self.message_id, reg_addr, reg_value)
                
            elif operation == "read_multiple":
                count = self.count_var.get()
                return PacketBuilder.read_multiple_request(device_addr, self.message_id, reg_addr, count)
                
            elif operation == "write_multiple":
                count = self.count_var.get()
                # Parse values
                values_str = self.values_var.get().strip()
                values = []
                for v in values_str.split(','):
                    values.append(int(v.strip(), 16))
                
                # Check count matches
                if len(values) != count:
                    messagebox.showerror("Error", f"Count ({count}) doesn't match number of values ({len(values)})")
                    return None
                
                return PacketBuilder.write_multiple_request(device_addr, self.message_id, reg_addr, values)
                
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")
            return None
        except Exception as e:
            messagebox.showerror("Error", f"Failed to build packet: {str(e)}")
            return None
    
    def send_request(self):
        """Send the request packet.
        
        Builds and transmits the configured request packet, logs the
        transaction, stores it for timeout tracking, and auto-increments
        the message ID for the next request.
        """
        serial_port = self.get_serial_port()
        if not serial_port or not serial_port.is_open:
            messagebox.showerror("Error", "Serial port not connected")
            return
        
        packet = self.build_packet()
        if not packet:
            return
        
        try:
            # Send packet
            packet_bytes = packet.to_bytes()
            serial_port.write(packet_bytes)
            
            # Log the request
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.log_display.insert(tk.END, f"[{timestamp}] TX Request (ID: {self.message_id:02X}):\n", "system")
            
            # Format packet display
            hex_str = " ".join(f"{b:02X}" for b in packet_bytes)
            self.log_display.insert(tk.END, f"  Raw: {hex_str}\n", "request")
            
            # Parse and display
            operation = self.operation_var.get()
            self.log_display.insert(tk.END, f"  Operation: {operation.replace('_', ' ').title()}\n", "request")
            self.log_display.insert(tk.END, f"  Device Address: {packet.device_address}\n", "request")
            
            # Store pending request for timeout handling
            self.pending_requests[self.message_id] = {
                'timestamp': datetime.datetime.now(),
                'operation': operation,
                'packet': packet
            }
            
            # Schedule timeout check
            self.frame.after(self.response_timeout, lambda: self.check_timeout(self.message_id))
            
            # Increment message ID
            self.message_id = (self.message_id + 1) & 0xFF
            self.msg_id_var.set(f"{self.message_id:02X}")
            
            # Auto-scroll
            self.log_display.see(tk.END)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send packet: {str(e)}")
    
    def check_timeout(self, msg_id: int):
        """Check if a request has timed out.
        
        Called after the timeout period to check if a response was received.
        If the request is still pending, it's marked as timed out.
        
        Args:
            msg_id: Message ID to check for timeout
        """
        if msg_id in self.pending_requests:
            request = self.pending_requests.pop(msg_id)
            
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.log_display.insert(tk.END, f"[{timestamp}] Timeout for Message ID {msg_id:02X}\n", "timeout")
            self.log_display.insert(tk.END, f"  No response received within {self.response_timeout}ms\n\n", "timeout")
            self.log_display.see(tk.END)
    
    def handle_raw_data(self, data: bytes):
        """Handle raw serial data from main thread"""
        try:
            self.response_buffer.extend(data)
            self.process_response_buffer()
        except Exception as e:
            print(f"Error handling raw data in host tab: {e}")
    
    def process_response_buffer(self):
        """Process the response buffer for complete packets"""
        try:
            # Try to parse packets
            while len(self.response_buffer) > 0:
                # Look for start flag
                start_idx = self.response_buffer.find(0x7E)
                if start_idx == -1:
                    self.response_buffer.clear()
                    break
                
                # Remove data before start flag
                if start_idx > 0:
                    self.response_buffer = self.response_buffer[start_idx:]
                
                # Check if we have enough data for header
                if len(self.response_buffer) < 6:
                    break
                
                # Get message length
                msg_length = self.response_buffer[3]
                total_length = 6 + msg_length  # Header + data + checksum
                
                # Check if we have complete packet
                if len(self.response_buffer) < total_length:
                    break
                
                # Extract packet
                packet_data = bytes(self.response_buffer[:total_length])
                self.response_buffer = self.response_buffer[total_length:]
                
                # Parse packet
                packet = Packet.from_bytes(packet_data)
                if packet:
                    self.handle_response(packet, packet_data)
                
        except Exception as e:
            print(f"Error processing response buffer: {e}")
    
    def process_responses(self):
        """Legacy method - now just schedules next check"""
        # Schedule next check - reduced interval for better responsiveness
        self.frame.after(5, self.process_responses)
    
    def handle_response(self, packet: Packet, raw_data: bytes = None):
        """Handle received response packet.
        
        Processes response packets from devices, matches them to pending
        requests, calculates response time, and logs the details.
        
        Args:
            packet: Parsed response packet
            raw_data: Original raw bytes (for display)
        """
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Check if this matches a pending request
        if packet.message_id in self.pending_requests:
            request = self.pending_requests.pop(packet.message_id)
            elapsed = (datetime.datetime.now() - request['timestamp']).total_seconds() * 1000
            
            self.log_display.insert(tk.END, 
                f"[{timestamp}] RX Response (ID: {packet.message_id:02X}, Time: {elapsed:.1f}ms):\n", "system")
        else:
            self.log_display.insert(tk.END, 
                f"[{timestamp}] RX Unexpected Response (ID: {packet.message_id:02X}):\n", "system")
        
        # Display raw packet - use original raw data if available, otherwise reconstruct
        if raw_data is not None:
            packet_bytes = raw_data
        else:
            packet_bytes = packet.to_bytes()
        hex_str = " ".join(f"{b:02X}" for b in packet_bytes)
        self.log_display.insert(tk.END, f"  Raw: {hex_str}\n", "response")
        
        # Parse and display response
        parsed = PacketParser.parse_response(packet)
        if parsed:
            if parsed.get('is_error'):
                self.log_display.insert(tk.END, f"  ERROR: {parsed['error_description']}\n", "error")
                self.log_display.insert(tk.END, f"  Error Code: 0x{parsed['error_code']:02X}\n", "error")
            else:
                func = packet.function_code
                if func == FunctionCode.READ_SINGLE_RESP:
                    self.log_display.insert(tk.END, 
                        f"  Read Single Response:\n", "response")
                    self.log_display.insert(tk.END, 
                        f"    Address: 0x{parsed['register_address']:04X}\n", "response")
                    self.log_display.insert(tk.END, 
                        f"    Value: 0x{parsed['register_value']:04X} ({parsed['register_value']})\n", "response")
                        
                elif func == FunctionCode.WRITE_SINGLE_RESP:
                    self.log_display.insert(tk.END, 
                        f"  Write Single Response:\n", "response")
                    self.log_display.insert(tk.END, 
                        f"    Address: 0x{parsed['register_address']:04X}\n", "response")
                    self.log_display.insert(tk.END, 
                        f"    Value: 0x{parsed['register_value']:04X}\n", "response")
                        
                elif func == FunctionCode.READ_MULTIPLE_RESP:
                    self.log_display.insert(tk.END, 
                        f"  Read Multiple Response:\n", "response")
                    self.log_display.insert(tk.END, 
                        f"    Starting Address: 0x{parsed['register_address']:04X}\n", "response")
                    self.log_display.insert(tk.END, 
                        f"    Count: {parsed['count']}\n", "response")
                    values_str = ", ".join(f"0x{v:04X}" for v in parsed.get('values', []))
                    self.log_display.insert(tk.END, 
                        f"    Values: [{values_str}]\n", "response")
                        
                elif func == FunctionCode.WRITE_MULTIPLE_RESP:
                    self.log_display.insert(tk.END, 
                        f"  Write Multiple Response:\n", "response")
                    self.log_display.insert(tk.END, 
                        f"    Starting Address: 0x{parsed['register_address']:04X}\n", "response")
                    self.log_display.insert(tk.END, 
                        f"    Count Written: {parsed['count']}\n", "response")
        
        self.log_display.insert(tk.END, "\n")
        self.log_display.see(tk.END)
    
    def clear_log(self):
        """Clear the communication log"""
        self.log_display.delete(1.0, tk.END)