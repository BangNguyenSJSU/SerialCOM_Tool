#!/usr/bin/env python3
"""
Modbus TCP Master Tab - Acts as a Modbus TCP client
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import struct
import threading
import datetime
from typing import Optional, List, Dict, Any
from modbus_tcp_protocol import (
    ModbusTCPFrame, ModbusTCPBuilder, ModbusTCPParser,
    ModbusFunctionCode, ModbusException
)
from ui_styles import (
    FONTS, SPACING, COLORS, configure_text_widget
)


class ModbusTCPMasterTab:
    """Modbus TCP Master implementation.
    
    This tab acts as a Modbus TCP client, connecting to a server
    and sending register read/write requests with comprehensive logging.
    """
    
    # Using shared styling system from ui_styles module
    
    def _init_style(self):
        """Initialize ttk styles for professional appearance"""
        # Use the shared init_style from ui_styles module instead of duplicating
        from ui_styles import init_style
        init_style()
    
    def __init__(self, parent_frame: ttk.Frame):
        """Initialize Modbus TCP Master Tab."""
        self.frame = parent_frame
        
        # Client state
        self.client_socket: Optional[socket.socket] = None
        self.is_connected = False
        self.connection_lock = threading.Lock()
        self.receive_thread: Optional[threading.Thread] = None
        
        # Modbus state
        self.transaction_id = 1
        self.unit_id = 1
        self.pending_requests: Dict[int, Dict[str, Any]] = {}
        self.response_timeout = 3000  # milliseconds
        
        # Statistics
        self.request_count = 0
        self.response_count = 0
        self.timeout_count = 0
        self.error_count = 0
        
        # UI state
        self.auto_scroll = tk.BooleanVar(value=True)
        
        # Build UI
        self.create_widgets()
        
        # Initialize
        self.update_statistics()
        self.update_preview()
    
    def create_widgets(self):
        """Create Modbus TCP Master tab UI elements"""
        self._init_style()
        
        # Main container with reduced padding
        main_frame = tk.Frame(self.frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Compact connection configuration
        config_frame = ttk.LabelFrame(main_frame, text="Connection Configuration",
                                     style="Section.TLabelframe")
        config_frame.pack(fill=tk.X, pady=(0, 8), padx=6)
        
        # Compact connection settings
        conn_frame = ttk.Frame(config_frame)
        conn_frame.pack(fill=tk.X, pady=(2, 4), padx=6)
        
        # Server IP
        ttk.Label(conn_frame, text="Server IP:").grid(row=0, column=0, sticky=tk.E, padx=(0, 6), pady=2)
        self.server_ip_var = tk.StringVar(value="127.0.0.1")
        self.server_ip_entry = ttk.Entry(conn_frame, textvariable=self.server_ip_var, width=14)
        self.server_ip_entry.grid(row=0, column=1, padx=(0, 18), pady=2, sticky=tk.W)
        
        # Server Port  
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, sticky=tk.E, padx=(0, 6), pady=2)
        self.server_port_var = tk.IntVar(value=502)
        self.server_port_spin = ttk.Spinbox(conn_frame, from_=1, to=65535, 
                                           textvariable=self.server_port_var, width=8)
        self.server_port_spin.grid(row=0, column=3, padx=(0, 18), pady=2, sticky=tk.W)
        
        # Unit ID
        ttk.Label(conn_frame, text="Unit ID:").grid(row=0, column=4, sticky=tk.E, padx=(0, 6), pady=2)
        self.unit_id_var = tk.IntVar(value=self.unit_id)
        self.unit_id_spin = ttk.Spinbox(conn_frame, from_=1, to=247, textvariable=self.unit_id_var,
                                       width=6, command=self.update_unit_id)
        self.unit_id_spin.grid(row=0, column=5, padx=(0, 18), pady=2, sticky=tk.W)
        
        # Timeout on same row
        ttk.Label(conn_frame, text="Timeout (ms):").grid(row=0, column=6, sticky=tk.E, padx=(0, 6), pady=2)
        self.timeout_var = tk.IntVar(value=self.response_timeout)
        ttk.Spinbox(conn_frame, from_=100, to=10000, textvariable=self.timeout_var,
                   width=6, increment=100, command=self.update_timeout).grid(row=0, column=7, pady=2, sticky=tk.W)
        
        # Compact connection controls and status on second row
        conn_control_frame = ttk.Frame(config_frame)
        conn_control_frame.pack(fill=tk.X, pady=(4, 2))
        
        # Buttons on left with keyboard mnemonics
        self.connect_btn = ttk.Button(conn_control_frame, text="Connect", underline=0,
                                     command=self.connect_to_server, width=10, style="Accent.TButton")
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.disconnect_btn = ttk.Button(conn_control_frame, text="Disconnect", underline=0,
                                        command=self.disconnect_from_server,
                                        state=tk.DISABLED, width=10)
        self.disconnect_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        # Status pill (single element for cleaner state display)
        self.status_pill = tk.Label(conn_control_frame, text="Disconnected",
                                   bd=0, padx=10, pady=3, fg="#991B1B",
                                   font=FONTS["ui_bold"])
        self.status_pill.pack(side=tk.LEFT, padx=(6, 0))
        
        # Add separator between header and content
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=(4, 8), padx=6)
        
        # Two-column layout: Request config + Stats | Preview + Log
        content_frame = tk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.columnconfigure(0, weight=1)  # Request config + Stats
        content_frame.columnconfigure(1, weight=2)  # Preview + Log
        
        # Left column: Request Configuration + Statistics
        left_column = tk.Frame(content_frame)
        left_column.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        # Right column: Preview + Communication Log
        right_column = tk.Frame(content_frame)
        right_column.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        
        # === LEFT COLUMN ===
        
        # Request Configuration with compact styling
        request_frame = ttk.LabelFrame(left_column, text="Request Configuration", padding="6")
        request_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Compact operation selection
        op_frame = ttk.Frame(request_frame)
        op_frame.pack(fill=tk.X, pady=(0, 4))
        
        ttk.Label(op_frame, text="Operation", font=FONTS["ui_bold"]).pack(anchor=tk.W)
        rb_container = ttk.Frame(op_frame)
        rb_container.pack(anchor=tk.W, pady=(2, 0))
        
        self.operation_var = tk.StringVar(value="read")
        ttk.Radiobutton(rb_container, text="Read (0x03)", variable=self.operation_var,
                       value="read", command=self.update_preview).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(rb_container, text="Write (0x10)", variable=self.operation_var,
                       value="write", command=self.update_preview).pack(side=tk.LEFT)
        
        # Compact parameters layout
        params_frame = ttk.Frame(request_frame)
        params_frame.pack(fill=tk.X, pady=(0, 6))
        
        # Start Address
        ttk.Label(params_frame, text="Start Address:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.start_addr_var = tk.StringVar(value="0000")
        self.start_addr_entry = ttk.Entry(params_frame, textvariable=self.start_addr_var, width=8)
        self.start_addr_entry.grid(row=0, column=1, padx=(5, 2), pady=2, sticky=tk.W)
        self.start_addr_var.trace('w', lambda *args: self.update_preview())
        
        ttk.Label(params_frame, text="(hex)", font=FONTS['ui_small'], foreground="#6B7280").grid(row=0, column=2, sticky=tk.W, pady=2)
        
        # Count (for read)
        self.count_label = ttk.Label(params_frame, text="Count:")
        self.count_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.count_var = tk.IntVar(value=1)
        self.count_spin = ttk.Spinbox(params_frame, from_=1, to=125, textvariable=self.count_var, width=8)
        self.count_spin.grid(row=1, column=1, padx=(5, 0), pady=2, sticky=tk.W)
        self.count_var.trace('w', lambda *args: self.update_preview())
        
        # Values for write operation
        self.values_label = ttk.Label(params_frame, text="Values (hex):")
        self.values_var = tk.StringVar(value="0000,0001,0002")
        self.values_entry = ttk.Entry(params_frame, textvariable=self.values_var, width=25)
        self.values_var.trace('w', lambda *args: self.update_preview())
        
        # Compact send button
        send_frame = ttk.Frame(request_frame)
        send_frame.pack(fill=tk.X, pady=(6, 0))
        
        self.send_btn = ttk.Button(send_frame, text="Send Request", underline=0,
                                  command=self.send_request, state=tk.DISABLED, width=12,
                                  style="Accent.TButton")
        self.send_btn.pack(side=tk.LEFT)
        
        # Statistics section in left column
        stats_frame = ttk.LabelFrame(left_column, text="Statistics", padding="4")
        stats_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Vertical compact layout with professional statistics styling
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.X)
        
        ttk.Label(stats_grid, text="Requests", style="StatLabel.TLabel").grid(row=0, column=0, sticky=tk.W)
        self.requests_label = ttk.Label(stats_grid, text="0", style="StatValue.TLabel")
        self.requests_label.grid(row=0, column=1, sticky=tk.E, padx=(5, 0))
        
        ttk.Label(stats_grid, text="Responses", style="StatLabel.TLabel").grid(row=1, column=0, sticky=tk.W)
        self.responses_label = ttk.Label(stats_grid, text="0", style="StatValue.TLabel")
        self.responses_label.grid(row=1, column=1, sticky=tk.E, padx=(5, 0))
        
        ttk.Label(stats_grid, text="Timeouts", style="StatLabel.TLabel").grid(row=2, column=0, sticky=tk.W)
        self.timeouts_label = ttk.Label(stats_grid, text="0", style="StatValue.TLabel", foreground="#F59E0B")
        self.timeouts_label.grid(row=2, column=1, sticky=tk.E, padx=(5, 0))
        
        ttk.Label(stats_grid, text="Errors", style="StatLabel.TLabel").grid(row=3, column=0, sticky=tk.W)
        self.errors_label = ttk.Label(stats_grid, text="0", style="StatValue.TLabel", foreground="#DC2626")
        self.errors_label.grid(row=3, column=1, sticky=tk.E, padx=(5, 0))
        
        ttk.Button(stats_frame, text="Reset", command=self.reset_statistics, width=8).pack(pady=(4, 0))
        
        # === RIGHT COLUMN ===
        
        # Create horizontal layout for Preview and Log side by side
        preview_log_frame = tk.Frame(right_column)
        preview_log_frame.pack(fill=tk.BOTH, expand=True)
        preview_log_frame.columnconfigure(0, weight=1)  # Preview column
        preview_log_frame.columnconfigure(1, weight=1)  # Log column
        
        # Request Preview (left half of right column)
        preview_frame = ttk.LabelFrame(preview_log_frame, text="Preview", padding="4")
        preview_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 3))
        
        self.preview_text = scrolledtext.ScrolledText(preview_frame, wrap=tk.WORD, height=25)
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        configure_text_widget(self.preview_text, "preview")
        
        # Configure tags with high contrast and clean appearance
        self.preview_text.tag_config("header", font=FONTS["mono"], foreground="#1F4B99")
        self.preview_text.tag_config("field", font=FONTS["mono"], foreground="#2E2E2E")
        self.preview_text.tag_config("value", font=FONTS["mono"], foreground="#065F46")
        self.preview_text.tag_config("hex", font=FONTS["mono"], foreground="#6B21A8")
        self.preview_text.tag_config("address", font=FONTS["mono"], foreground="#B45309")
        
        # Add vertical separator between Preview and Log
        sep = ttk.Separator(preview_log_frame, orient="vertical")
        sep.grid(row=0, column=1, sticky="ns", padx=4)
        
        # Communication Log (right half of right column)  
        log_frame = ttk.LabelFrame(preview_log_frame, text="Log", padding="4")
        log_frame.grid(row=0, column=2, sticky='nsew', padx=(3, 0))
        
        # Update column configuration
        preview_log_frame.columnconfigure(0, weight=1)  # Preview column
        preview_log_frame.columnconfigure(2, weight=1)  # Log column
        
        # Compact log toolbar
        log_toolbar = ttk.Frame(log_frame)
        log_toolbar.pack(fill=tk.X, pady=(0, 2))
        
        ttk.Checkbutton(log_toolbar, text="Auto-scroll", variable=self.auto_scroll).pack(side=tk.LEFT)
        ttk.Button(log_toolbar, text="Clear", command=self.clear_log, width=6).pack(side=tk.RIGHT)
        
        # Compact log display
        self.log_display = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=25)
        self.log_display.pack(fill=tk.BOTH, expand=True)
        configure_text_widget(self.log_display, "log")
        
        # Configure log tags with high contrast colors
        self.log_display.tag_config("info", foreground="#0066CC", font=FONTS["mono"])
        self.log_display.tag_config("request", foreground="#00AA00", font=FONTS["mono"])
        self.log_display.tag_config("response", foreground="#AA00AA", font=FONTS["mono"])
        self.log_display.tag_config("error", foreground="#CC0000", font=FONTS["mono"])
        self.log_display.tag_config("timeout", foreground="#FF8800", font=FONTS["mono"])
        self.log_display.tag_config("system", foreground="#666666", font=FONTS["mono"])
        self.log_display.tag_config("debug", foreground="#FF6600", font=FONTS["mono"])
        
        # Initialize UI state
        self.update_operation_ui()
        
        # Set initial focus for keyboard accessibility
        self.server_ip_entry.focus_set()
    
    def update_operation_ui(self):
        """Update UI based on selected operation"""
        operation = self.operation_var.get()
        
        if operation == "read":
            # Show count, hide values
            self.count_label.grid(row=1, column=0, sticky=tk.W, pady=2)
            self.count_spin.grid(row=1, column=1, padx=(5, 0), pady=2, sticky=tk.W)
            self.values_label.grid_remove()
            self.values_entry.grid_remove()
        else:  # write
            # Hide count, show values
            self.count_label.grid_remove()
            self.count_spin.grid_remove()
            self.values_label.grid(row=2, column=0, sticky=tk.W, pady=2)
            self.values_entry.grid(row=2, column=1, columnspan=2, sticky=tk.EW, pady=2, padx=(5, 0))
    
    def update_unit_id(self):
        """Update unit ID"""
        self.unit_id = self.unit_id_var.get()
    
    def decode_request_for_debug(self, request_data: bytes, operation_desc: str) -> str:
        """Decode Modbus request for debug display"""
        if len(request_data) < 8:
            return f"Invalid request ({len(request_data)} bytes)"
        
        try:
            # Parse MBAP header
            transaction_id, protocol_id, length, unit_id = struct.unpack('>HHHB', request_data[:7])
            function_code = request_data[7]
            
            if function_code == 0x03:  # Read Holding Registers
                start_addr = struct.unpack('>H', request_data[8:10])[0] if len(request_data) >= 10 else 0
                count = struct.unpack('>H', request_data[10:12])[0] if len(request_data) >= 12 else 0
                return f"Read Request - {count} registers from 0x{start_addr:04X} to 0x{start_addr + count - 1:04X}"
            
            elif function_code == 0x10:  # Write Multiple Registers
                start_addr = struct.unpack('>H', request_data[8:10])[0] if len(request_data) >= 10 else 0
                count = struct.unpack('>H', request_data[10:12])[0] if len(request_data) >= 12 else 0
                byte_count = request_data[12] if len(request_data) > 12 else 0
                
                # Extract register values
                values = []
                reg_index = 0
                for i in range(13, 13 + byte_count, 2):
                    if i + 1 < len(request_data):
                        value = struct.unpack('>H', request_data[i:i+2])[0]
                        values.append(f"[{reg_index}]=0x{value:04X}")
                        reg_index += 1
                
                if count <= 8:
                    values_str = " ".join(values)
                    return f"Write Request - {count} registers from 0x{start_addr:04X}: {values_str}"
                else:
                    lines = []
                    for i in range(0, len(values), 8):
                        group = " ".join(values[i:i+8])
                        lines.append(f"    {group}")
                    values_str = "\n".join(lines)
                    return f"Write Request - {count} registers from 0x{start_addr:04X}:\n{values_str}"
            
            else:
                return f"Function 0x{function_code:02X} Request ({len(request_data)} bytes)"
                
        except Exception as e:
            return f"Decode error: {str(e)}"
    
    def decode_response_for_debug(self, response_data: bytes) -> str:
        """Decode Modbus response for debug display"""
        if len(response_data) < 8:
            return f"Invalid response ({len(response_data)} bytes)"
        
        try:
            # Parse MBAP header
            transaction_id, protocol_id, length, unit_id = struct.unpack('>HHHB', response_data[:7])
            function_code = response_data[7]
            
            # Check if it's an exception response
            if function_code & 0x80:
                exception_code = response_data[8] if len(response_data) > 8 else 0
                exception_names = {
                    0x01: "ILLEGAL_FUNCTION",
                    0x02: "ILLEGAL_DATA_ADDRESS", 
                    0x03: "ILLEGAL_DATA_VALUE",
                    0x04: "SLAVE_DEVICE_FAILURE"
                }
                exception_name = exception_names.get(exception_code, f"UNKNOWN_0x{exception_code:02X}")
                return f"Exception Response - {exception_name} (0x{exception_code:02X})"
            
            # Decode based on function code
            if function_code == 0x03:  # Read Holding Registers Response
                byte_count = response_data[8] if len(response_data) > 8 else 0
                num_registers = byte_count // 2
                
                # Extract ALL register values with indices
                values = []
                reg_index = 0
                for i in range(9, 9 + byte_count, 2):
                    if i + 1 < len(response_data):
                        value = struct.unpack('>H', response_data[i:i+2])[0]
                        values.append(f"[{reg_index}]=0x{value:04X}")
                        reg_index += 1
                
                # Format output based on number of registers
                if num_registers <= 8:
                    values_str = " ".join(values)
                    return f"Read Response ({num_registers} regs): {values_str}"
                else:
                    lines = []
                    for i in range(0, len(values), 8):
                        group = " ".join(values[i:i+8])
                        lines.append(f"    {group}")
                    values_str = "\n".join(lines)
                    return f"Read Response ({num_registers} registers):\n{values_str}"
            
            elif function_code == 0x10:  # Write Multiple Registers Response
                start_addr = struct.unpack('>H', response_data[8:10])[0] if len(response_data) >= 10 else 0
                quantity = struct.unpack('>H', response_data[10:12])[0] if len(response_data) >= 12 else 0
                return f"Write Response - Wrote {quantity} registers from 0x{start_addr:04X} to 0x{start_addr + quantity - 1:04X}"
            
            else:
                return f"Function 0x{function_code:02X} Response ({len(response_data)} bytes)"
                
        except Exception as e:
            return f"Decode error: {str(e)}"
        self.update_preview()
    
    def update_timeout(self):
        """Update response timeout"""
        self.response_timeout = self.timeout_var.get()
    
    def update_preview(self):
        """Update request preview"""
        try:
            self.update_operation_ui()
            
            operation = self.operation_var.get()
            start_addr = int(self.start_addr_var.get(), 16)
            
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)
            
            if operation == "read":
                count = self.count_var.get()
                
                # Build preview frame
                frame = ModbusTCPBuilder.read_holding_registers_request(
                    self.transaction_id, self.unit_id, start_addr, count)
                
                self.preview_text.insert(tk.END, "Multi Read Request:\n", "header")
                self.preview_text.insert(tk.END, "  Transaction ID: ", "field")
                self.preview_text.insert(tk.END, f"0x{frame.transaction_id:04X}\n", "value")
                self.preview_text.insert(tk.END, "  Unit ID: ", "field")
                self.preview_text.insert(tk.END, f"{frame.unit_id}\n", "value")
                self.preview_text.insert(tk.END, "  Function: ", "field")
                self.preview_text.insert(tk.END, "Read Holding Registers (0x03)\n", "value")
                self.preview_text.insert(tk.END, "  Start Address: ", "field")
                self.preview_text.insert(tk.END, f"0x{start_addr:04X}", "address")
                self.preview_text.insert(tk.END, f" ({start_addr})\n", "value")
                self.preview_text.insert(tk.END, "  Count: ", "field")
                self.preview_text.insert(tk.END, f"{count}\n\n", "value")
                
                frame_bytes = frame.to_bytes()
                hex_str = " ".join(f"{b:02X}" for b in frame_bytes)
                self.preview_text.insert(tk.END, f"Raw bytes ({len(frame_bytes)}):\n", "header")
                self.preview_text.insert(tk.END, hex_str, "hex")
                
            else:  # write
                try:
                    values_str = self.values_var.get().strip()
                    if not values_str:
                        raise ValueError("No values specified")
                    
                    values = []
                    for v in values_str.split(','):
                        values.append(int(v.strip(), 16))
                    
                    if not values:
                        raise ValueError("No valid values")
                    
                    # Build preview frame
                    frame = ModbusTCPBuilder.write_multiple_registers_request(
                        self.transaction_id, self.unit_id, start_addr, values)
                    
                    self.preview_text.insert(tk.END, "Multi Write Request:\n", "header")
                    self.preview_text.insert(tk.END, "  Transaction ID: ", "field")
                    self.preview_text.insert(tk.END, f"0x{frame.transaction_id:04X}\n", "value")
                    self.preview_text.insert(tk.END, "  Unit ID: ", "field")
                    self.preview_text.insert(tk.END, f"{frame.unit_id}\n", "value")
                    self.preview_text.insert(tk.END, "  Function: ", "field")
                    self.preview_text.insert(tk.END, "Write Multiple Registers (0x10)\n", "value")
                    self.preview_text.insert(tk.END, "  Start Address: ", "field")
                    self.preview_text.insert(tk.END, f"0x{start_addr:04X}", "address")
                    self.preview_text.insert(tk.END, f" ({start_addr})\n", "value")
                    self.preview_text.insert(tk.END, "  Count: ", "field")
                    self.preview_text.insert(tk.END, f"{len(values)}\n", "value")
                    
                    values_str = ", ".join(f"0x{v:04X}" for v in values[:8])
                    if len(values) > 8:
                        values_str += f"... ({len(values)} total)"
                    self.preview_text.insert(tk.END, "  Values: [", "field")
                    self.preview_text.insert(tk.END, values_str, "hex")
                    self.preview_text.insert(tk.END, "]\n\n", "field")
                    
                    frame_bytes = frame.to_bytes()
                    hex_str = " ".join(f"{b:02X}" for b in frame_bytes)
                    self.preview_text.insert(tk.END, f"Raw bytes ({len(frame_bytes)}):\n", "header")
                    self.preview_text.insert(tk.END, hex_str, "hex")
                    
                except ValueError as e:
                    self.preview_text.insert(tk.END, "Invalid values: ", "field")
                    self.preview_text.insert(tk.END, str(e), "hex")
            
            self.preview_text.config(state=tk.DISABLED)
            
        except ValueError:
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, "Invalid parameters", "hex")
            self.preview_text.config(state=tk.DISABLED)
    
    def connect_to_server(self):
        """Connect to Modbus TCP server"""
        if self.is_connected:
            return
        
        server_ip = self.server_ip_var.get().strip()
        server_port = self.server_port_var.get()
        
        if not server_ip:
            messagebox.showerror("Error", "Please enter a server IP address")
            return
        
        try:
            # Create socket and connect
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5.0)  # Connection timeout
            self.client_socket.connect((server_ip, server_port))
            
            self.is_connected = True
            
            # Update UI state with enhanced styling
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            self.send_btn.config(state=tk.NORMAL)
            self.server_ip_entry.config(state=tk.DISABLED)
            self.server_port_spin.config(state=tk.DISABLED)
            self.status_pill.config(text="Connected", fg="#065F46")
            
            self.add_log(f"[CONNECTED] Connected to {server_ip}:{server_port}", "info")
            
            # Start persistent receive thread
            self.receive_thread = threading.Thread(target=self.receive_worker, daemon=True)
            self.receive_thread.start()
                
        except Exception as e:
            self.is_connected = False
            if self.client_socket:
                try:
                    self.client_socket.close()
                except:
                    pass
                self.client_socket = None
            
            error_msg = f"Failed to connect to {server_ip}:{server_port}: {str(e)}"
            messagebox.showerror("Connection Error", error_msg)
            self.add_log(f"[ERROR] {error_msg}", "error")
    
    def disconnect_from_server(self):
        """Disconnect from server"""
        self.is_connected = False
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        
        # Clear pending requests
        self.pending_requests.clear()
        
        # Update UI state with enhanced styling
        self.connect_btn.config(state=tk.NORMAL)
        self.disconnect_btn.config(state=tk.DISABLED)
        self.send_btn.config(state=tk.DISABLED)
        self.server_ip_entry.config(state=tk.NORMAL)
        self.server_port_spin.config(state=tk.NORMAL)
        self.status_pill.config(text="Disconnected", fg="#991B1B")
        
        self.add_log("[DISCONNECTED] Disconnected from server", "info")
    
    def send_request(self):
        """Send Modbus request"""
        if not self.is_connected or not self.client_socket:
            messagebox.showerror("Error", "Not connected to server")
            return
        
        try:
            operation = self.operation_var.get()
            start_addr = int(self.start_addr_var.get(), 16)
            
            if operation == "read":
                count = self.count_var.get()
                frame = ModbusTCPBuilder.read_holding_registers_request(
                    self.transaction_id, self.unit_id, start_addr, count)
                operation_desc = f"Read {count} registers from 0x{start_addr:04X}"
            else:  # write
                values_str = self.values_var.get().strip()
                values = []
                for v in values_str.split(','):
                    values.append(int(v.strip(), 16))
                
                if not values:
                    raise ValueError("No valid values specified")
                
                frame = ModbusTCPBuilder.write_multiple_registers_request(
                    self.transaction_id, self.unit_id, start_addr, values)
                values_preview = ", ".join(f"0x{v:04X}" for v in values[:4])
                if len(values) > 4:
                    values_preview += f"... ({len(values)} total)"
                operation_desc = f"Write {len(values)} registers from 0x{start_addr:04X}: [{values_preview}]"
            
            # Send request
            request_bytes = frame.to_bytes()
            self.client_socket.send(request_bytes)
            
            self.request_count += 1
            self.update_statistics()
            
            # Log request with detailed decoding
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            decoded_request = self.decode_request_for_debug(request_bytes, operation_desc)
            self.add_log(f"[{timestamp}] TX Request (TID: {self.transaction_id:04X}):", "request")
            self.add_log(f"  {decoded_request}", "debug")
            
            # Store pending request for timeout handling
            self.pending_requests[self.transaction_id] = {
                'timestamp': datetime.datetime.now(),
                'operation': operation,
                'frame': frame
            }
            
            # Schedule timeout check
            self.frame.after(self.response_timeout, 
                           lambda tid=self.transaction_id: self.check_timeout(tid))
            
            # Increment transaction ID
            self.transaction_id = (self.transaction_id % 65535) + 1
            self.update_preview()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid parameters: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send request: {str(e)}")
            self.disconnect_from_server()
    
    def receive_worker(self):
        """Persistent receive worker thread"""
        self.frame.after(0, lambda: self.add_log("[DEBUG] Receive worker started", "system"))
        
        while self.is_connected and self.client_socket:
            try:
                # Set short timeout for receiving to allow checking is_connected
                self.client_socket.settimeout(1.0)
                
                # Receive response (minimum 8 bytes for MBAP header + function)
                data = self.client_socket.recv(1024)
                if not data:
                    # Connection closed by server
                    if self.is_connected:
                        self.frame.after(0, lambda: self.add_log("Connection closed by server", "error"))
                        self.frame.after(0, self.disconnect_from_server)
                    break
                
                # Parse response
                response = ModbusTCPFrame.from_bytes(data)
                if response:
                    self.handle_response(response)
                
            except socket.timeout:
                # Normal timeout, continue loop
                continue
            except ConnectionResetError as e:
                if self.is_connected:
                    self.frame.after(0, lambda: self.add_log(f"Connection reset by server", "error"))
                    self.frame.after(0, self.disconnect_from_server)
                break
            except Exception as e:
                if self.is_connected:
                    self.frame.after(0, lambda: self.add_log(f"Receive error: {str(e)} (type: {type(e).__name__})", "error"))
                    self.frame.after(0, self.disconnect_from_server)
                break
        
        self.frame.after(0, lambda: self.add_log("[DEBUG] Receive worker stopped", "system"))
    
    def handle_response(self, response: ModbusTCPFrame):
        """Handle received response (thread-safe)"""
        def process_response():
            # Check if this matches a pending request
            if response.transaction_id not in self.pending_requests:
                self.add_log(f"Unexpected response TID: {response.transaction_id:04X}", "error")
                return
            
            request_info = self.pending_requests.pop(response.transaction_id)
            elapsed = (datetime.datetime.now() - request_info['timestamp']).total_seconds() * 1000
            
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.add_log(f"[{timestamp}] RX Response (TID: {response.transaction_id:04X}, Time: {elapsed:.1f}ms):", "response")
            
            self.response_count += 1
            self.update_statistics()
            
            # Use improved response decoding
            response_bytes = response.to_bytes()
            decoded_response = self.decode_response_for_debug(response_bytes)
            
            # Check for exception response
            if response.function_code & 0x80:
                self.error_count += 1
                self.update_statistics()
                self.add_log(f"  {decoded_response}", "error")
            else:
                self.add_log(f"  {decoded_response}", "debug")
        
        # Execute on main thread
        self.frame.after(0, process_response)
    
    def check_timeout(self, transaction_id: int):
        """Check if request has timed out"""
        if transaction_id in self.pending_requests:
            request_info = self.pending_requests.pop(transaction_id)
            self.timeout_count += 1
            self.update_statistics()
            
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.add_log(f"[{timestamp}] Timeout for TID: {transaction_id:04X}", "timeout")
            self.add_log(f"  No response received within {self.response_timeout}ms", "timeout")
    
    def add_log(self, message: str, tag: str = "system"):
        """Add message to log display"""
        self.log_display.insert(tk.END, message + "\n", tag)
        if self.auto_scroll.get():
            self.log_display.see(tk.END)
    
    def clear_log(self):
        """Clear the log display"""
        self.log_display.delete(1.0, tk.END)
    
    def reset_statistics(self):
        """Reset all statistics"""
        self.request_count = 0
        self.response_count = 0
        self.timeout_count = 0
        self.error_count = 0
        self.update_statistics()
    
    def update_statistics(self):
        """Update statistics display"""
        self.requests_label.config(text=str(self.request_count))
        self.responses_label.config(text=str(self.response_count))
        self.timeouts_label.config(text=str(self.timeout_count))
        self.errors_label.config(text=str(self.error_count))