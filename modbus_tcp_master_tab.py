#!/usr/bin/env python3
"""
Modbus TCP Master Tab - Acts as a Modbus TCP client
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import threading
import datetime
from typing import Optional, List, Dict, Any
from modbus_tcp_protocol import (
    ModbusTCPFrame, ModbusTCPBuilder, ModbusTCPParser,
    ModbusFunctionCode, ModbusException
)


class ModbusTCPMasterTab:
    """Modbus TCP Master implementation.
    
    This tab acts as a Modbus TCP client, connecting to a server
    and sending register read/write requests with comprehensive logging.
    """
    
    # Color scheme matching original tabs
    COLORS = {
        'bg_main': '#f0f0f0',           # Light gray main background
        'bg_connection': '#e3f2fd',     # Light blue for connection config
        'bg_request': '#f3e5f5',        # Light purple for request config
        'bg_preview': '#fff3e0',        # Light amber for preview
        'bg_stats': '#e8f5e9',          # Light green for statistics
        'bg_log': '#ffffff',            # White for log display
        'fg_connected': '#4caf50',      # Green for connected
        'fg_disconnected': '#f44336',   # Red for disconnected
        'border_dark': '#9e9e9e',       # Dark gray for borders
    }
    
    def __init__(self, parent_frame: ttk.Frame):
        """Initialize Modbus TCP Master Tab."""
        self.frame = parent_frame
        
        # Client state
        self.client_socket: Optional[socket.socket] = None
        self.is_connected = False
        self.connection_lock = threading.Lock()
        
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
        # Main container with reduced padding
        main_frame = tk.Frame(self.frame, bg=self.COLORS['bg_main'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Compact connection configuration
        config_frame = tk.LabelFrame(main_frame, text="Connection Configuration",
                                    bg=self.COLORS['bg_connection'],
                                    fg='#01579b',
                                    font=('Arial', 9, 'bold'),
                                    relief=tk.RAISED, bd=1)
        config_frame.pack(fill=tk.X, pady=(0, 5), padx=2)
        
        # Compact connection settings
        conn_frame = ttk.Frame(config_frame)
        conn_frame.pack(fill=tk.X, pady=(2, 4))
        
        # Server IP
        ttk.Label(conn_frame, text="Server IP:", font=('Arial', 9)).grid(row=0, column=0, sticky=tk.E, padx=(0, 5), pady=2)
        self.server_ip_var = tk.StringVar(value="127.0.0.1")
        self.server_ip_entry = ttk.Entry(conn_frame, textvariable=self.server_ip_var, width=12, font=('Arial', 9))
        self.server_ip_entry.grid(row=0, column=1, padx=(0, 10), pady=2, sticky=tk.W)
        
        # Server Port  
        ttk.Label(conn_frame, text="Port:", font=('Arial', 9)).grid(row=0, column=2, sticky=tk.E, padx=(0, 5), pady=2)
        self.server_port_var = tk.IntVar(value=502)
        self.server_port_spin = ttk.Spinbox(conn_frame, from_=1, to=65535, 
                                           textvariable=self.server_port_var, width=8, font=('Arial', 9))
        self.server_port_spin.grid(row=0, column=3, padx=(0, 10), pady=2, sticky=tk.W)
        
        # Unit ID
        ttk.Label(conn_frame, text="Unit ID:", font=('Arial', 9)).grid(row=0, column=4, sticky=tk.E, padx=(0, 5), pady=2)
        self.unit_id_var = tk.IntVar(value=self.unit_id)
        self.unit_id_spin = ttk.Spinbox(conn_frame, from_=1, to=247, textvariable=self.unit_id_var,
                                       width=6, font=('Arial', 9), command=self.update_unit_id)
        self.unit_id_spin.grid(row=0, column=5, pady=2, sticky=tk.W)
        
        # Timeout on same row
        ttk.Label(conn_frame, text="Timeout(ms):", font=('Arial', 9)).grid(row=0, column=6, sticky=tk.E, padx=(10, 5), pady=2)
        self.timeout_var = tk.IntVar(value=self.response_timeout)
        ttk.Spinbox(conn_frame, from_=100, to=10000, textvariable=self.timeout_var,
                   width=6, font=('Arial', 9), increment=100, command=self.update_timeout).grid(row=0, column=7, pady=2, sticky=tk.W)
        
        # Compact connection controls and status on second row
        conn_control_frame = ttk.Frame(config_frame)
        conn_control_frame.pack(fill=tk.X, pady=(4, 2))
        
        # Buttons on left
        self.connect_btn = ttk.Button(conn_control_frame, text="Connect", command=self.connect_to_server, width=10)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.disconnect_btn = ttk.Button(conn_control_frame, text="Disconnect", command=self.disconnect_from_server,
                                        state=tk.DISABLED, width=10)
        self.disconnect_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        # Status in center
        ttk.Label(conn_control_frame, text="Status:", font=('Arial', 9)).pack(side=tk.LEFT, padx=(0, 5))
        self.status_label = tk.Label(conn_control_frame, text="Disconnected", 
                                    bg='#f0f0f0', fg='red', font=('Arial', 9, 'bold'))
        self.status_label.pack(side=tk.LEFT)
        
        # Two-column layout: Request config + Stats | Preview + Log
        content_frame = tk.Frame(main_frame, bg='#f0f0f0')
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.columnconfigure(0, weight=1)  # Request config + Stats
        content_frame.columnconfigure(1, weight=2)  # Preview + Log
        
        # Left column: Request Configuration + Statistics
        left_column = tk.Frame(content_frame, bg='#f0f0f0')
        left_column.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        # Right column: Preview + Communication Log
        right_column = tk.Frame(content_frame, bg='#f0f0f0')
        right_column.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        
        # === LEFT COLUMN ===
        
        # Request Configuration with compact styling
        request_frame = ttk.LabelFrame(left_column, text="Request Configuration", padding="6")
        request_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Compact operation selection
        op_frame = ttk.Frame(request_frame)
        op_frame.pack(fill=tk.X, pady=(0, 6))
        
        ttk.Label(op_frame, text="Operation:", font=('Arial', 9, 'bold')).pack(side=tk.TOP, anchor=tk.W)
        
        self.operation_var = tk.StringVar(value="read")
        ttk.Radiobutton(op_frame, text="Read (0x03)", variable=self.operation_var,
                       value="read", command=self.update_preview).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(op_frame, text="Write (0x10)", variable=self.operation_var,
                       value="write", command=self.update_preview).pack(side=tk.LEFT)
        
        # Compact parameters layout
        params_frame = ttk.Frame(request_frame)
        params_frame.pack(fill=tk.X, pady=(0, 6))
        
        # Start Address
        ttk.Label(params_frame, text="Start Address:", font=('Arial', 9)).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.start_addr_var = tk.StringVar(value="0000")
        self.start_addr_entry = ttk.Entry(params_frame, textvariable=self.start_addr_var, width=8, font=('Arial', 9))
        self.start_addr_entry.grid(row=0, column=1, padx=(5, 2), pady=2, sticky=tk.W)
        self.start_addr_var.trace('w', lambda *args: self.update_preview())
        
        ttk.Label(params_frame, text="(hex)", font=('Arial', 8), foreground='gray').grid(row=0, column=2, sticky=tk.W, pady=2)
        
        # Count (for read)
        self.count_label = ttk.Label(params_frame, text="Count:", font=('Arial', 9))
        self.count_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.count_var = tk.IntVar(value=1)
        self.count_spin = ttk.Spinbox(params_frame, from_=1, to=125, textvariable=self.count_var, width=8, font=('Arial', 9))
        self.count_spin.grid(row=1, column=1, padx=(5, 0), pady=2, sticky=tk.W)
        self.count_var.trace('w', lambda *args: self.update_preview())
        
        # Values for write operation
        self.values_label = ttk.Label(params_frame, text="Values (hex):", font=('Arial', 9))
        self.values_var = tk.StringVar(value="0000,0001,0002")
        self.values_entry = ttk.Entry(params_frame, textvariable=self.values_var, width=25, font=('Arial', 9))
        self.values_var.trace('w', lambda *args: self.update_preview())
        
        # Compact send button
        send_frame = ttk.Frame(request_frame)
        send_frame.pack(fill=tk.X, pady=(6, 0))
        
        self.send_btn = ttk.Button(send_frame, text="Send Request", command=self.send_request, 
                                  state=tk.DISABLED, width=12)
        self.send_btn.pack(side=tk.LEFT)
        
        # Statistics section in left column
        stats_frame = ttk.LabelFrame(left_column, text="Statistics", padding="4")
        stats_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Vertical compact layout
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.X)
        
        ttk.Label(stats_grid, text="Requests:", font=('Arial', 8)).grid(row=0, column=0, sticky=tk.W)
        self.requests_label = ttk.Label(stats_grid, text="0", font=('Arial', 8, 'bold'))
        self.requests_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(stats_grid, text="Responses:", font=('Arial', 8)).grid(row=1, column=0, sticky=tk.W)
        self.responses_label = ttk.Label(stats_grid, text="0", font=('Arial', 8, 'bold'))
        self.responses_label.grid(row=1, column=1, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(stats_grid, text="Timeouts:", font=('Arial', 8)).grid(row=2, column=0, sticky=tk.W)
        self.timeouts_label = ttk.Label(stats_grid, text="0", font=('Arial', 8, 'bold'), foreground="orange")
        self.timeouts_label.grid(row=2, column=1, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(stats_grid, text="Errors:", font=('Arial', 8)).grid(row=3, column=0, sticky=tk.W)
        self.errors_label = ttk.Label(stats_grid, text="0", font=('Arial', 8, 'bold'), foreground="red")
        self.errors_label.grid(row=3, column=1, sticky=tk.W, padx=(5, 0))
        
        ttk.Button(stats_frame, text="Reset", command=self.reset_statistics, width=8).pack(pady=(4, 0))
        
        # === RIGHT COLUMN ===
        
        # Create horizontal layout for Preview and Log side by side
        preview_log_frame = tk.Frame(right_column, bg='#f0f0f0')
        preview_log_frame.pack(fill=tk.BOTH, expand=True)
        preview_log_frame.columnconfigure(0, weight=1)  # Preview column
        preview_log_frame.columnconfigure(1, weight=1)  # Log column
        
        # Request Preview (left half of right column)
        preview_frame = ttk.LabelFrame(preview_log_frame, text="Request Preview", padding="4")
        preview_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 3))
        
        self.preview_text = scrolledtext.ScrolledText(preview_frame, wrap=tk.WORD, height=25,
                                                     font=("Courier", 8), bg='#FAFAFA')
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags with smaller fonts
        self.preview_text.tag_config("header", font=("Courier", 8, "bold"), foreground="#0066CC")
        self.preview_text.tag_config("field", font=("Courier", 8), foreground="#333333")
        self.preview_text.tag_config("value", font=("Courier", 8, "bold"), foreground="#006600")
        self.preview_text.tag_config("hex", font=("Courier", 8, "bold"), foreground="#9966CC")
        
        # Communication Log (right half of right column)
        log_frame = ttk.LabelFrame(preview_log_frame, text="Communication Log", padding="4")
        log_frame.grid(row=0, column=1, sticky='nsew', padx=(3, 0))
        
        # Compact log toolbar
        log_toolbar = ttk.Frame(log_frame)
        log_toolbar.pack(fill=tk.X, pady=(0, 2))
        
        ttk.Checkbutton(log_toolbar, text="Auto-scroll", variable=self.auto_scroll).pack(side=tk.LEFT)
        ttk.Button(log_toolbar, text="Clear", command=self.clear_log, width=6).pack(side=tk.RIGHT)
        
        # Compact log display
        self.log_display = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=25,
                                                    font=("Courier", 8))
        self.log_display.pack(fill=tk.BOTH, expand=True)
        
        # Configure log tags with smaller fonts
        self.log_display.tag_config("info", foreground="blue", font=("Courier", 8))
        self.log_display.tag_config("request", foreground="green", font=("Courier", 8))
        self.log_display.tag_config("response", foreground="purple", font=("Courier", 8))
        self.log_display.tag_config("error", foreground="red", font=("Courier", 8))
        self.log_display.tag_config("timeout", foreground="orange", font=("Courier", 8))
        self.log_display.tag_config("system", foreground="gray", font=("Courier", 8))
        
        # Initialize UI state
        self.update_operation_ui()
    
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
                
                self.preview_text.insert(tk.END, f"Multi Read Request:\n")
                self.preview_text.insert(tk.END, f"  Transaction ID: 0x{frame.transaction_id:04X}\n")
                self.preview_text.insert(tk.END, f"  Unit ID: {frame.unit_id}\n")
                self.preview_text.insert(tk.END, f"  Function: Read Holding Registers (0x03)\n")
                self.preview_text.insert(tk.END, f"  Start Address: 0x{start_addr:04X} ({start_addr})\n")
                self.preview_text.insert(tk.END, f"  Count: {count}\n\n")
                
                frame_bytes = frame.to_bytes()
                hex_str = " ".join(f"{b:02X}" for b in frame_bytes)
                self.preview_text.insert(tk.END, f"Raw bytes ({len(frame_bytes)}):\n{hex_str}")
                
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
                    
                    self.preview_text.insert(tk.END, f"Multi Write Request:\n")
                    self.preview_text.insert(tk.END, f"  Transaction ID: 0x{frame.transaction_id:04X}\n")
                    self.preview_text.insert(tk.END, f"  Unit ID: {frame.unit_id}\n")
                    self.preview_text.insert(tk.END, f"  Function: Write Multiple Registers (0x10)\n")
                    self.preview_text.insert(tk.END, f"  Start Address: 0x{start_addr:04X} ({start_addr})\n")
                    self.preview_text.insert(tk.END, f"  Count: {len(values)}\n")
                    
                    values_str = ", ".join(f"0x{v:04X}" for v in values[:8])
                    if len(values) > 8:
                        values_str += f"... ({len(values)} total)"
                    self.preview_text.insert(tk.END, f"  Values: [{values_str}]\n\n")
                    
                    frame_bytes = frame.to_bytes()
                    hex_str = " ".join(f"{b:02X}" for b in frame_bytes)
                    self.preview_text.insert(tk.END, f"Raw bytes ({len(frame_bytes)}):\n{hex_str}")
                    
                except ValueError as e:
                    self.preview_text.insert(tk.END, f"Invalid values: {str(e)}")
            
            self.preview_text.config(state=tk.DISABLED)
            
        except ValueError:
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, "Invalid parameters")
            self.preview_text.config(state=tk.DISABLED)
    
    def connect_to_server(self):
        """Connect to Modbus TCP server"""
        if self.is_connected:
            return
        
        try:
            server_ip = self.server_ip_var.get().strip()
            server_port = self.server_port_var.get()
            
            if not server_ip:
                messagebox.showerror("Error", "Please enter server IP address")
                return
            
            # Create socket and connect
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5.0)  # 5 second connection timeout
            self.client_socket.connect((server_ip, server_port))
            
            with self.connection_lock:
                self.is_connected = True
            
            # Update UI
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            self.send_btn.config(state=tk.NORMAL)
            self.server_ip_entry.config(state=tk.DISABLED)
            self.server_port_spin.config(state=tk.DISABLED)
            self.status_label.config(text="Connected", fg="green")
            
            self.add_log(f"Connected to {server_ip}:{server_port}", "info")
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            self.disconnect_from_server()
    
    def disconnect_from_server(self):
        """Disconnect from server"""
        with self.connection_lock:
            self.is_connected = False
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        
        # Update UI
        self.connect_btn.config(state=tk.NORMAL)
        self.disconnect_btn.config(state=tk.DISABLED)
        self.send_btn.config(state=tk.DISABLED)
        self.server_ip_entry.config(state=tk.NORMAL)
        self.server_port_spin.config(state=tk.NORMAL)
        self.status_label.config(text="Disconnected", fg=self.COLORS['fg_disconnected'])
        
        self.add_log("Disconnected", "info")
    
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
                operation_desc = f"Write {len(values)} registers to 0x{start_addr:04X}: [{values_preview}]"
            
            # Send request
            request_bytes = frame.to_bytes()
            self.client_socket.send(request_bytes)
            
            self.request_count += 1
            self.update_statistics()
            
            # Log request
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.add_log(f"[{timestamp}] TX Request (TID: {self.transaction_id:04X}):", "request")
            self.add_log(f"  {operation_desc}", "request")
            
            # Store pending request for timeout handling
            self.pending_requests[self.transaction_id] = {
                'timestamp': datetime.datetime.now(),
                'operation': operation,
                'frame': frame
            }
            
            # Schedule timeout check
            self.frame.after(self.response_timeout, 
                           lambda tid=self.transaction_id: self.check_timeout(tid))
            
            # Start response listener if not already running
            threading.Thread(target=self.receive_response, daemon=True).start()
            
            # Increment transaction ID
            self.transaction_id = (self.transaction_id % 65535) + 1
            self.update_preview()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid parameters: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send request: {str(e)}")
            self.disconnect_from_server()
    
    def receive_response(self):
        """Receive and process response (runs in thread)"""
        if not self.is_connected or not self.client_socket:
            return
        
        try:
            # Set short timeout for receiving
            self.client_socket.settimeout(self.response_timeout / 1000.0)
            
            # Receive response (minimum 8 bytes for MBAP header + function)
            data = self.client_socket.recv(1024)
            if not data:
                return
            
            # Parse response
            response = ModbusTCPFrame.from_bytes(data)
            if response:
                self.handle_response(response)
            
        except socket.timeout:
            # Timeout handled by timeout checker
            pass
        except Exception as e:
            if self.is_connected:
                self.frame.after(0, lambda: self.add_log(f"Receive error: {str(e)}", "error"))
    
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
            
            # Check for exception response
            if response.function_code & 0x80:
                parsed = ModbusTCPParser.parse_exception_response(response)
                if parsed:
                    self.error_count += 1
                    self.update_statistics()
                    self.add_log(f"  Exception: {parsed['exception_name']}", "error")
                else:
                    self.add_log(f"  Unknown exception response", "error")
                return
            
            # Parse normal response
            if response.function_code == ModbusFunctionCode.READ_HOLDING_REGISTERS:
                parsed = ModbusTCPParser.parse_read_holding_registers_response(response)
                if parsed:
                    values = parsed['values']
                    values_str = ", ".join(f"0x{v:04X}" for v in values[:8])
                    if len(values) > 8:
                        values_str += f"... ({len(values)} total)"
                    self.add_log(f"  Read Response: [{values_str}]", "response")
                else:
                    self.add_log(f"  Invalid read response format", "error")
            
            elif response.function_code == ModbusFunctionCode.WRITE_MULTIPLE_REGISTERS:
                parsed = ModbusTCPParser.parse_write_multiple_registers_response(response)
                if parsed:
                    self.add_log(f"  Write Response: Address=0x{parsed['start_address']:04X}, Count={parsed['count']}", "response")
                else:
                    self.add_log(f"  Invalid write response format", "error")
            else:
                self.add_log(f"  Unknown response function: 0x{response.function_code:02X}", "error")
        
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