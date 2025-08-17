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
from ui_styles import FONTS, SPACING, COLORS
from serial_connection import SerialConnection
from register_grid_window import RegisterGridWindow


class HostTab:
    """Host (Master) mode implementation for protocol testing.
    
    This tab acts as a protocol master, sending register read/write requests
    to devices and handling their responses. It provides a UI for configuring
    requests, tracks pending requests for timeout handling, and logs all
    communication.
    """
    
    # Using shared color scheme from ui_styles
    
    def __init__(self, parent_frame: ttk.Frame):
        """
        Initialize Host Tab.
        
        Args:
            parent_frame: Parent Tkinter frame
        """
        self.frame = parent_frame
        
        # Create independent serial connection for Host tab
        self.serial_connection = SerialConnection(parent_frame, self.on_data_received)
        
        # Create internal data queue for protocol responses
        self.data_queue = queue.Queue()
        
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
    
    def setup_styles(self):
        """Configure ttk styles with shared design system"""
        style = ttk.Style()
        return style
    
    def create_widgets(self):
        """Create Host tab UI elements"""
        # Configure shared styles
        self.setup_styles()
        
        # Main container with background
        main_frame = tk.Frame(self.frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING['padx'], pady=SPACING['pady'])
        
        # Top section (full width) - Device Address and Register Operation
        top_section = tk.Frame(main_frame)
        top_section.pack(fill=tk.X, pady=(0, 10))
        
        # Device Address Section - using shared styling
        addr_frame = ttk.LabelFrame(top_section, text="Device Address", 
                                   style="Section.TLabelframe")
        addr_frame.pack(fill=tk.X, pady=(0, 10), padx=SPACING['padx'])
        
        # Create inner frame for grid layout with consistent padding
        addr_content = ttk.Frame(addr_frame)
        addr_content.pack(fill=tk.X, padx=10, pady=8)
        
        # Address field - aligned to grid
        ttk.Label(addr_content, text="Address (0-247):").grid(row=0, column=0, sticky='e', padx=(0, 6), pady=2)
        self.device_addr_var = tk.IntVar(value=1)
        self.device_addr_spin = ttk.Spinbox(addr_content, from_=0, to=247, 
                                           textvariable=self.device_addr_var, width=12)
        self.device_addr_spin.grid(row=0, column=1, padx=(0, 10), sticky='w')
        self.device_addr_var.trace('w', lambda *args: self.update_preview())
        ttk.Label(addr_content, text="(0 = Broadcast)", font=FONTS["default"], foreground="#6B7280").grid(row=0, column=2, padx=(2, 20), sticky='w')
        
        # Message ID field - aligned to same grid
        ttk.Label(addr_content, text="Message ID:").grid(row=0, column=3, sticky='e', padx=(0, 6), pady=2)
        self.msg_id_var = tk.StringVar(value=f"{self.message_id:02X}")
        self.msg_id_entry = ttk.Entry(addr_content, textvariable=self.msg_id_var, width=12, font=FONTS["mono"])
        self.msg_id_entry.grid(row=0, column=4, padx=(0, 10), sticky='w')
        self.msg_id_var.trace('w', self.on_message_id_change)
        ttk.Label(addr_content, text="(00-FF hex)", font=FONTS["default"], foreground="#6B7280").grid(row=0, column=5, sticky='w', padx=(2, 0), pady=2)
        
        # Operation Selection - using shared styling
        op_frame = ttk.LabelFrame(top_section, text="Register Operation", 
                                 style="Section.TLabelframe")
        op_frame.pack(fill=tk.X, pady=(0, 10), padx=SPACING['padx'])
        
        # Operation type radio buttons with even spacing using grid
        self.operation_var = tk.StringVar(value="read_single")
        operations = [
            ("Read Single (0x01)", "read_single"),
            ("Write Single (0x02)", "write_single"),
            ("Read Multiple (0x03)", "read_multiple"),
            ("Write Multiple (0x04)", "write_multiple")
        ]
        
        op_content = ttk.Frame(op_frame)
        op_content.pack(fill=tk.X, padx=SPACING['padx'], pady=SPACING['pady'])
        
        # Configure equal column weights for even spacing
        for i in range(4):
            op_content.columnconfigure(i, weight=1)
        
        for i, (text, value) in enumerate(operations):
            radio = ttk.Radiobutton(
                op_content, text=text, variable=self.operation_var, value=value,
                command=self.on_operation_change
            )
            radio.grid(row=0, column=i, padx=5, sticky='w')
        
        # Two-column layout section
        columns_frame = tk.Frame(main_frame)
        columns_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure column weights: left 60%, right 40%
        columns_frame.columnconfigure(0, weight=60)
        columns_frame.columnconfigure(1, weight=40)
        
        # LEFT COLUMN (60% width)
        left_column = tk.Frame(columns_frame)
        left_column.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        
        # RIGHT COLUMN (40% width)
        right_column = tk.Frame(columns_frame)
        right_column.grid(row=0, column=1, sticky='nsew')
        
        # === LEFT COLUMN CONTENT ===
        
        # Parameters Frame with green background - using grid for alignment
        params_frame = ttk.LabelFrame(left_column, text="Parameters", padding="8")
        params_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        # Create grid container for parameter fields
        params_content = tk.Frame(params_frame)
        params_content.pack(fill=tk.X, padx=10, pady=8)
        
        # Configure column widths for consistent alignment
        params_content.columnconfigure(1, weight=1)
        
        # Register Address - row 0
        ttk.Label(params_content, text="Register Address (hex):",
                width=25, anchor='e').grid(row=0, column=0, padx=(0, 10), pady=3, sticky='e')
        self.reg_addr_var = tk.StringVar(value="0000")
        self.reg_addr_entry = ttk.Entry(params_content, textvariable=self.reg_addr_var, width=15)
        self.reg_addr_entry.grid(row=0, column=1, pady=3, sticky='w')
        self.reg_addr_var.trace('w', lambda *args: self.update_preview())
        
        # Register Value (for write operations) - row 1
        self.value_label = ttk.Label(params_content, text="Register Value (hex):",
                width=25, anchor='e')
        self.value_label.grid(row=1, column=0, padx=(0, 10), pady=3, sticky='e')
        self.reg_value_var = tk.StringVar(value="0000")
        self.reg_value_entry = ttk.Entry(params_content, textvariable=self.reg_value_var, width=15)
        self.reg_value_entry.grid(row=1, column=1, pady=3, sticky='w')
        self.reg_value_var.trace('w', lambda *args: self.update_preview())
        
        # Count (for multiple operations) - row 2
        self.count_label = ttk.Label(params_content, text="Count (1-255):",
                width=25, anchor='e')
        self.count_label.grid(row=2, column=0, padx=(0, 10), pady=3, sticky='e')
        self.count_var = tk.IntVar(value=1)
        self.count_spin = ttk.Spinbox(params_content, from_=1, to=255, textvariable=self.count_var, width=15)
        self.count_spin.grid(row=2, column=1, pady=3, sticky='w')
        self.count_var.trace('w', lambda *args: self.update_preview())
        
        # Multiple values (for write multiple) - row 3
        self.values_label = ttk.Label(params_content, text="Values (comma-separated):",
                width=30, anchor='e')
        self.values_label.grid(row=3, column=0, padx=(0, 10), pady=3, sticky='e')
        self.values_var = tk.StringVar(value="0000,0001,0002")
        self.values_entry = ttk.Entry(params_content, textvariable=self.values_var, width=50)
        self.values_entry.grid(row=3, column=1, pady=3, sticky='w')
        self.values_var.trace('w', lambda *args: self.update_preview())
        
        # Control Buttons with timeout indicator - using grid for better alignment
        control_frame = ttk.Frame(left_column)
        control_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        # Create inner container with consistent padding
        control_content = ttk.Frame(control_frame)
        control_content.pack(fill=tk.X, padx=10, pady=5)
        
        # Standardized button width and height
        button_width = 12
        
        self.send_btn = ttk.Button(control_content, text="Send Request", command=self.send_request, 
                                  style='Send.TButton', width=button_width)
        self.send_btn.grid(row=0, column=0, padx=(0, 10), sticky='w')
        
        clear_btn = ttk.Button(control_content, text="Clear Log", command=self.clear_log, 
                              style='Clear.TButton', width=button_width)
        clear_btn.grid(row=0, column=1, padx=(0, 10), sticky='w')
        
        # Register Grid button
        register_grid_btn = ttk.Button(control_content, text="📊 Register Grid", 
                                      command=self.open_register_grid, 
                                      width=button_width)
        register_grid_btn.grid(row=0, column=2, padx=(0, 20), sticky='w')
        
        # Timeout setting - aligned with buttons
        ttk.Label(control_content, text="Timeout (ms):",
                anchor='e', width=12).grid(row=0, column=3, padx=(0, 10), sticky='e')
        self.timeout_var = tk.IntVar(value=self.response_timeout)
        timeout_spin = ttk.Spinbox(control_content, from_=100, to=5000, textvariable=self.timeout_var, 
                                   width=8, increment=100)
        timeout_spin.grid(row=0, column=4, padx=(0, 10), sticky='w')
        self.timeout_var.trace('w', lambda *args: setattr(self, 'response_timeout', self.timeout_var.get()))
        
        # Timeout indicator (shows countdown when waiting for response)
        self.timeout_indicator = ttk.Label(control_content, text="",
                                         foreground='orange', font=FONTS['default'], width=15)
        self.timeout_indicator.grid(row=0, column=5, padx=10, sticky='w')
        
        # Packet Preview with amber background and parsed fields
        preview_frame = ttk.LabelFrame(left_column, text="Packet Preview & Inspection", padding="8")
        preview_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        # Split preview into hex and parsed sections with proper alignment
        preview_container = ttk.Frame(preview_frame)
        preview_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        
        # Configure grid weights for proper stretching
        preview_container.columnconfigure(1, weight=1)
        
        # Hex preview section - aligned labels
        ttk.Label(preview_container, text="Hex Bytes:",
                font=FONTS['default'], width=12, anchor='e').grid(row=0, column=0, 
                padx=(0, 10), pady=3, sticky='e')
        self.preview_text = tk.Text(preview_container, height=6, width=50, font=FONTS['mono'],
                                   relief=tk.SUNKEN, bd=1)
        self.preview_text.grid(row=0, column=1, pady=3, sticky='ew')
        
        # Configure color tags for preview_text
        self.preview_text.configure(font=FONTS["mono"], borderwidth=0, highlightthickness=0)
        self.preview_text.tag_config("header", font=FONTS["mono"], foreground="#1F4B99")
        self.preview_text.tag_config("field", font=FONTS["mono"], foreground="#2E2E2E")
        self.preview_text.tag_config("value", font=FONTS["mono"], foreground="#065F46")
        self.preview_text.tag_config("hex", font=FONTS["mono"], foreground="#6B21A8")
        self.preview_text.tag_config("address", font=FONTS["mono"], foreground="#B45309")
        self.preview_text.tag_config("hex_data", foreground="#0066CC", font=FONTS['mono'])
        self.preview_text.tag_config("label", foreground="#666666", font=FONTS['mono'])
        self.preview_text.tag_config("error", foreground="#CC0000", font=FONTS['mono'])
        
        # Parsed fields section - aligned with hex section
        ttk.Label(preview_container, text="Parsed:",
                font=FONTS['default'], width=12, anchor='e').grid(row=1, column=0, 
                padx=(0, 10), pady=3, sticky='e')
        self.parsed_text = tk.Text(preview_container, height=8, width=50, font=FONTS['mono'],
                                  relief=tk.SUNKEN, bd=1)
        self.parsed_text.grid(row=1, column=1, pady=3, sticky='ew')
        
        # Configure color tags for parsed_text
        self.parsed_text.tag_config("field_label", foreground="#666666", font=FONTS['mono'])
        self.parsed_text.tag_config("field_value", foreground="#0066CC", font=FONTS['mono'])
        self.parsed_text.tag_config("func_code", foreground="#9900CC", font=FONTS['mono'])
        self.parsed_text.tag_config("address", foreground="#FF6600", font=FONTS['mono'])
        self.parsed_text.tag_config("separator", foreground="#999999", font=FONTS['mono'])
        self.parsed_text.tag_config("error", foreground="#CC0000", font=FONTS['mono'])
        
        # Checksum status - aligned with parsed text start
        self.checksum_label = ttk.Label(preview_container, text="Checksum: Not calculated",
                                      font=FONTS['default'],
                                      anchor='w')
        self.checksum_label.grid(row=2, column=1, pady=5, sticky='w')
        
        # === RIGHT COLUMN CONTENT ===
        
        # Communication Log with white background - now in right column, full height
        log_frame = ttk.LabelFrame(right_column, text="Communication Log", padding="8")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5)
        
        # Create log with consistent padding, larger for right column
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        
        # Larger log display to take advantage of right column space
        self.log_display = scrolledtext.ScrolledText(log_container, wrap=tk.WORD, height=20, 
                                                    width=40, font=FONTS['mono'], 
                                                    relief=tk.SUNKEN, bd=1)
        self.log_display.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for coloring
        self.log_display.tag_config("request", foreground="blue")
        self.log_display.tag_config("response", foreground="green")
        self.log_display.tag_config("error", foreground="red")
        self.log_display.tag_config("timeout", foreground="orange")
        self.log_display.tag_config("system", foreground="gray")
        
        # Initially hide unused fields and update preview
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
        
        # Show/hide relevant fields based on operation
        if operation == "write_single":
            # Show only register value field
            self.value_label.grid(row=1, column=0, padx=(0, 10), pady=3, sticky='e')
            self.reg_value_entry.grid(row=1, column=1, pady=3, sticky='w')
            # Hide count and values fields
            self.count_label.grid_remove()
            self.count_spin.grid_remove()
            self.values_label.grid_remove()
            self.values_entry.grid_remove()
        elif operation == "read_multiple":
            # Show only count field
            self.count_label.grid(row=2, column=0, padx=(0, 10), pady=3, sticky='e')
            self.count_spin.grid(row=2, column=1, pady=3, sticky='w')
            # Hide value and values fields
            self.value_label.grid_remove()
            self.reg_value_entry.grid_remove()
            self.values_label.grid_remove()
            self.values_entry.grid_remove()
        elif operation == "write_multiple":
            # Show count and values fields
            self.count_label.grid(row=2, column=0, padx=(0, 10), pady=3, sticky='e')
            self.count_spin.grid(row=2, column=1, pady=3, sticky='w')
            self.values_label.grid(row=3, column=0, padx=(0, 10), pady=3, sticky='e')
            self.values_entry.grid(row=3, column=1, pady=3, sticky='w')
            # Hide single value field
            self.value_label.grid_remove()
            self.reg_value_entry.grid_remove()
        else:  # read_single
            # Hide all optional fields
            self.value_label.grid_remove()
            self.reg_value_entry.grid_remove()
            self.count_label.grid_remove()
            self.count_spin.grid_remove()
            self.values_label.grid_remove()
            self.values_entry.grid_remove()
        
        # Update preview
        self.update_preview()
    
    def update_preview(self):
        """Update packet preview with hex bytes and parsed fields"""
        try:
            packet = self.build_packet(show_errors=False)
            if packet:
                packet_bytes = packet.to_bytes()
                
                # Format hex bytes with spacing
                hex_str = " ".join(f"{b:02X}" for b in packet_bytes)
                
                # Update hex preview with color coding
                self.preview_text.delete(1.0, tk.END)
                self.preview_text.insert(tk.END, hex_str, "hex_data")
                self.preview_text.insert(tk.END, "\n")
                self.preview_text.insert(tk.END, "Length: ", "label")
                self.preview_text.insert(tk.END, f"{len(packet_bytes)} bytes", "value")
                
                # Parse and display fields with color coding
                self.parse_packet_fields_with_colors(packet, packet_bytes)
                
                # Update checksum status
                checksum = (packet_bytes[-2] << 8) | packet_bytes[-1] if len(packet_bytes) >= 2 else 0
                self.checksum_label.config(text=f"Checksum: 0x{checksum:04X} (Fletcher-16)",
                                         foreground='green')
            else:
                # Show informative message when packet can't be built
                self.preview_text.delete(1.0, tk.END)
                operation = self.operation_var.get()
                if operation == "write_multiple":
                    count = self.count_var.get()
                    values_str = self.values_var.get().strip()
                    num_values = len(values_str.split(',')) if values_str else 0
                    if num_values != count:
                        self.preview_text.insert(tk.END, "Count mismatch: ", "error")
                        self.preview_text.insert(tk.END, f"Count={count}, Values={num_values}", "label")
                    else:
                        self.preview_text.insert(tk.END, "Invalid input format", "error")
                else:
                    self.preview_text.insert(tk.END, "Invalid input format", "error")
                self.parsed_text.delete(1.0, tk.END)
                self.parsed_text.insert(tk.END, "Waiting for valid input...", "label")
                self.checksum_label.config(text="Checksum: N/A", foreground='gray')
        except Exception as e:
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, "Error: ", "error")
            self.preview_text.insert(tk.END, str(e), "error")
            self.parsed_text.delete(1.0, tk.END)
            self.checksum_label.config(text="Checksum: Error", foreground='red')
    
    def parse_packet_fields(self, packet, packet_bytes):
        """Parse packet into human-readable fields"""
        if len(packet_bytes) < 6:
            return "Invalid packet (too short)"
        
        try:
            start_flag = f"0x{packet_bytes[0]:02X}"
            device_addr = packet_bytes[1]
            message_id = f"0x{packet_bytes[2]:02X}"
            length = packet_bytes[3]
            func_code = f"0x{packet_bytes[4]:02X}"
            
            # Decode function
            func_names = {
                0x01: "Read Single",
                0x02: "Write Single", 
                0x03: "Read Multiple",
                0x04: "Write Multiple"
            }
            func_name = func_names.get(packet_bytes[4], "Unknown")
            
            parsed = f"Start: {start_flag} | Addr: {device_addr} | ID: {message_id}\n"
            parsed += f"Len: {length} | Func: {func_code} ({func_name})"
            
            # Add data field info if space allows
            if length > 1 and len(packet_bytes) > 7:
                data_bytes = packet_bytes[5:-2]  # Exclude checksum
                if len(data_bytes) >= 2:
                    reg_addr = (data_bytes[0] << 8) | data_bytes[1]
                    parsed += f" | Reg: 0x{reg_addr:04X}"
            
            return parsed
        except:
            return "Parse error"
    
    def parse_packet_fields_with_colors(self, packet, packet_bytes):
        """Parse packet and display with color-coded fields"""
        self.parsed_text.delete(1.0, tk.END)
        
        if len(packet_bytes) < 6:
            self.parsed_text.insert(tk.END, "Invalid packet (too short)", "error")
            return
        
        try:
            start_flag = f"0x{packet_bytes[0]:02X}"
            device_addr = packet_bytes[1]
            message_id = f"0x{packet_bytes[2]:02X}"
            length = packet_bytes[3]
            func_code = f"0x{packet_bytes[4]:02X}"
            
            # Decode function
            func_names = {
                0x01: "Read Single",
                0x02: "Write Single", 
                0x03: "Read Multiple",
                0x04: "Write Multiple"
            }
            func_name = func_names.get(packet_bytes[4], "Unknown")
            
            # First line with colored fields
            self.parsed_text.insert(tk.END, "Start: ", "field_label")
            self.parsed_text.insert(tk.END, start_flag, "field_value")
            self.parsed_text.insert(tk.END, " | ", "separator")
            self.parsed_text.insert(tk.END, "Addr: ", "field_label")
            self.parsed_text.insert(tk.END, str(device_addr), "address")
            self.parsed_text.insert(tk.END, " | ", "separator")
            self.parsed_text.insert(tk.END, "ID: ", "field_label")
            self.parsed_text.insert(tk.END, message_id, "field_value")
            self.parsed_text.insert(tk.END, "\n")
            
            # Second line with function details
            self.parsed_text.insert(tk.END, "Len: ", "field_label")
            self.parsed_text.insert(tk.END, str(length), "field_value")
            self.parsed_text.insert(tk.END, " | ", "separator")
            self.parsed_text.insert(tk.END, "Func: ", "field_label")
            self.parsed_text.insert(tk.END, func_code, "func_code")
            self.parsed_text.insert(tk.END, " (", "separator")
            self.parsed_text.insert(tk.END, func_name, "func_code")
            self.parsed_text.insert(tk.END, ")", "separator")
            
            # Add data field info if space allows
            if length > 1 and len(packet_bytes) > 7:
                data_bytes = packet_bytes[5:-2]  # Exclude checksum
                if len(data_bytes) >= 2:
                    reg_addr = (data_bytes[0] << 8) | data_bytes[1]
                    self.parsed_text.insert(tk.END, " | ", "separator")
                    self.parsed_text.insert(tk.END, "Reg: ", "field_label")
                    self.parsed_text.insert(tk.END, f"0x{reg_addr:04X}", "address")
            
        except Exception as e:
            self.parsed_text.delete(1.0, tk.END)
            self.parsed_text.insert(tk.END, "Parse error: ", "error")
            self.parsed_text.insert(tk.END, str(e), "error")
    
    def build_packet(self, show_errors=True) -> Optional[Packet]:
        """Build packet based on current UI settings.
        
        Reads the current UI configuration and creates the appropriate
        packet for the selected operation type.
        
        Args:
            show_errors: If True, show error dialogs. If False, return None silently.
        
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
                    if show_errors:
                        messagebox.showerror("Error", f"Count ({count}) doesn't match number of values ({len(values)})")
                    return None
                
                return PacketBuilder.write_multiple_request(device_addr, self.message_id, reg_addr, values)
                
        except ValueError as e:
            if show_errors:
                messagebox.showerror("Error", f"Invalid input: {str(e)}")
            return None
        except Exception as e:
            if show_errors:
                messagebox.showerror("Error", f"Failed to build packet: {str(e)}")
            return None
    
    def send_request(self):
        """Send the request packet.
        
        Builds and transmits the configured request packet, logs the
        transaction, stores it for timeout tracking, and auto-increments
        the message ID for the next request.
        """
        if not self.serial_connection.is_connected:
            messagebox.showerror("Error", "Serial port not connected")
            return
        
        packet = self.build_packet()
        if not packet:
            return
        
        try:
            # Send packet
            packet_bytes = packet.to_bytes()
            success = self.serial_connection.send_data(packet_bytes)
            if not success:
                messagebox.showerror("Error", "Failed to send packet")
                return
            
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
    
    def on_data_received(self, msg_type: str, data, timestamp: str):
        """Callback for serial connection data."""
        if msg_type == 'rx':
            # Add received data to our internal queue for processing
            self.data_queue.put(data)
        elif msg_type == 'error':
            # Log error message
            self.log_display.insert(tk.END, f"Serial Error: {data}\n", "error")
            self.log_display.see(tk.END)
    
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
            
            # Handle response event for register grid integration
            if 'request_event' in request and 'response_data' in request:
                # Parse response for the register grid
                parsed = PacketParser.parse_response(packet)
                if parsed:
                    if parsed.get('is_error'):
                        request['response_data']['success'] = False
                        request['response_data']['data'] = parsed['error_description']
                    else:
                        func = packet.function_code
                        if func == FunctionCode.READ_SINGLE_RESP:
                            request['response_data']['success'] = True
                            request['response_data']['data'] = {
                                'value': parsed['register_value']
                            }
                        elif func == FunctionCode.READ_MULTIPLE_RESP:
                            request['response_data']['success'] = True
                            request['response_data']['data'] = {
                                'values': parsed.get('values', [])
                            }
                        elif func in [FunctionCode.WRITE_SINGLE_RESP, FunctionCode.WRITE_MULTIPLE_RESP]:
                            request['response_data']['success'] = True
                            request['response_data']['data'] = {
                                'address': parsed['register_address'],
                                'count': parsed.get('count', 1)
                            }
                else:
                    request['response_data']['success'] = False
                    request['response_data']['data'] = "Failed to parse response"
                
                # Signal the waiting thread
                request['request_event'].set()
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
    
    def open_register_grid(self):
        """Open register grid window"""
        RegisterGridWindow(self.frame, host_tab=self)
    
    def send_protocol_request(self, function_code, start_addr, count=1, values=None):
        """Send protocol request programmatically (for register grid integration).
        
        This method allows the register grid to send read/write requests through
        the host tab's communication system.
        
        Args:
            function_code: Protocol function code (0x01-0x04)
            start_addr: Starting register address
            count: Number of registers (for multiple operations)
            values: List of values (for write operations)
            
        Returns:
            Tuple of (success: bool, response_data: dict or error_message: str)
        """
        if not self.serial_connection.is_connected:
            return False, "Not connected to device"
        
        try:
            # Map function codes to operations
            operation_map = {
                0x01: "read_single",
                0x02: "write_single", 
                0x03: "read_multiple",
                0x04: "write_multiple"
            }
            
            operation = operation_map.get(function_code)
            if not operation:
                return False, f"Invalid function code: 0x{function_code:02X}"
            
            # Save current UI state
            saved_operation = self.operation_var.get()
            saved_addr = self.reg_addr_var.get()
            saved_value = self.reg_value_var.get()
            saved_count = self.count_var.get()
            saved_values = self.values_var.get()
            
            # Set up for the requested operation
            self.operation_var.set(operation)
            self.reg_addr_var.set(f"{start_addr:04X}")
            
            if operation == "write_single" and values:
                self.reg_value_var.set(f"{values[0]:04X}")
            elif operation in ["read_multiple", "write_multiple"]:
                self.count_var.set(count)
                if operation == "write_multiple" and values:
                    values_str = ",".join(f"{v:04X}" for v in values)
                    self.values_var.set(values_str)
            
            # Build packet
            packet = self.build_packet()
            if not packet:
                return False, "Failed to build packet"
            
            # Send request
            packet_bytes = packet.to_bytes()
            
            # Store pending request info for response matching
            request_event = threading.Event()
            response_data = {"success": False, "data": None}
            
            self.pending_requests[packet.message_id] = {
                'timestamp': datetime.datetime.now(),
                'timeout_after': None,
                'request_event': request_event,
                'response_data': response_data,
                'operation': operation,
                'start_addr': start_addr,
                'count': count
            }
            
            # Send the packet
            self.serial_connection.send_data(packet_bytes)
            
            # Wait for response with timeout
            timeout_ms = self.response_timeout
            if request_event.wait(timeout_ms / 1000.0):
                # Response received
                result = response_data.get("success", False)
                data = response_data.get("data", "No data received")
                
                # Restore UI state
                self.operation_var.set(saved_operation)
                self.reg_addr_var.set(saved_addr)
                self.reg_value_var.set(saved_value)
                self.count_var.set(saved_count)
                self.values_var.set(saved_values)
                
                return result, data
            else:
                # Timeout
                if packet.message_id in self.pending_requests:
                    del self.pending_requests[packet.message_id]
                
                # Restore UI state
                self.operation_var.set(saved_operation)
                self.reg_addr_var.set(saved_addr)
                self.reg_value_var.set(saved_value)
                self.count_var.set(saved_count)
                self.values_var.set(saved_values)
                
                return False, "Request timeout"
                
        except Exception as e:
            return False, f"Error: {str(e)}"