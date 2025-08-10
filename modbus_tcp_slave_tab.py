#!/usr/bin/env python3
"""
Modbus TCP Slave Tab - 4-Column Responsive Layout
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import socket
import threading
import datetime
import csv
from typing import Optional, Dict, List, Any, Tuple
from modbus_tcp_protocol import (
    ModbusTCPFrame, ModbusTCPBuilder, ModbusTCPParser, ModbusRegisterMap,
    ModbusFunctionCode, ModbusException
)


class ModbusTCPSlaveTab:
    """Modbus TCP Slave implementation with 4-column responsive layout."""
    
    # Color scheme matching original tabs
    COLORS = {
        'bg_main': '#f0f0f0',           # Light gray main background
        'bg_server': '#e3f2fd',         # Light blue for server config (like host address)
        'bg_stats': '#f3e5f5',          # Light purple for statistics (like operation)
        'bg_error': '#fff3e0',          # Light amber for error simulation (like preview)
        'bg_registers': '#e8f5e9',      # Light green for register management (like params)
        'bg_log': '#ffffff',            # White for log display
        'bg_regmap': '#ffffff',         # White for register map display
        'fg_running': '#4caf50',        # Green for running status
        'fg_stopped': '#f44336',        # Red for stopped status
        'fg_connected': '#4caf50',      # Green for connected
        'fg_disconnected': '#666666',   # Gray for disconnected
        'border_dark': '#9e9e9e',       # Dark gray for borders
    }
    
    def __init__(self, parent_frame: ttk.Frame):
        """Initialize Modbus TCP Slave Tab."""
        self.frame = parent_frame
        
        # Server state
        self.server_socket: Optional[socket.socket] = None
        self.client_socket: Optional[socket.socket] = None
        self.client_address: Optional[Tuple[str, int]] = None
        self.is_running = False
        self.is_connected = False
        self.server_thread: Optional[threading.Thread] = None
        self.client_thread: Optional[threading.Thread] = None
        self.socket_lock = threading.Lock()
        
        # Modbus state  
        self.register_map = ModbusRegisterMap()
        self.unit_id = 1
        
        # Statistics
        self.connection_count = 0
        self.request_count = 0
        self.response_count = 0
        self.error_count = 0
        
        # Error simulation
        self.simulate_errors = tk.BooleanVar(value=False)
        self.error_type = tk.StringVar(value="none")
        
        # UI state
        self.auto_scroll = tk.BooleanVar(value=True)
        self.current_layout = 'wide'
        
        # Build UI
        self.create_widgets()
        
        # Initialize views
        self.refresh_register_view()
        self.update_statistics()
    
    def create_widgets(self):
        """Create Modbus TCP Slave tab UI elements"""
        # Main container with consistent styling
        self.main_frame = tk.Frame(self.frame, bg=self.COLORS['bg_main'])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top 4-column layout with responsive design
        self.top4 = tk.Frame(self.main_frame, bg=self.COLORS['bg_main'])
        self.top4.pack(fill=tk.X, pady=(0, 10))
        
        # Configure responsive grid (4 equal columns)
        for c in range(4):
            self.top4.grid_columnconfigure(c, weight=1, uniform="four")
        self.top4.grid_rowconfigure(0, weight=0)
        
        # Create the four sections
        self.create_server_config_section()
        self.create_statistics_section()
        self.create_error_simulation_section()
        self.create_register_management_section()
        
        # Initial layout (wide mode)
        self.set_layout_mode('wide')
        
        # Bottom section - Two-column layout
        self.create_bottom_layout()
        
        # Bind window resize event for responsive layout
        self.frame.bind('<Configure>', self.on_window_resize)
    
    def create_server_config_section(self):
        """Create Server Configuration section (Column 1)"""
        self.server_frame = tk.LabelFrame(self.top4, text="Server Configuration",
                                         bg=self.COLORS['bg_server'],
                                         fg='#01579b',
                                         font=('Arial', 10, 'bold'),
                                         relief=tk.RAISED, bd=2)
        
        # Content container with proper background
        server_content = tk.Frame(self.server_frame, bg=self.COLORS['bg_server'])
        server_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        
        # Row 1: IP: [127.0.0.1] Port: [502] Unit: [1]
        row1 = tk.Frame(server_content, bg=self.COLORS['bg_server'])
        row1.pack(fill=tk.X, pady=(0, 4))
        
        # IP field - more compact
        tk.Label(row1, text="IP:", font=('Arial', 10), bg=self.COLORS['bg_server'], 
                width=3, anchor='e').pack(side=tk.LEFT)
        self.ip_var = tk.StringVar(value="127.0.0.1")
        self.ip_entry = ttk.Entry(row1, textvariable=self.ip_var, width=10, font=('Arial', 10))
        self.ip_entry.pack(side=tk.LEFT, padx=(2, 8))
        
        # Port field - more compact
        tk.Label(row1, text="Port:", font=('Arial', 10), bg=self.COLORS['bg_server'], 
                width=4, anchor='e').pack(side=tk.LEFT)
        self.port_var = tk.IntVar(value=502)
        self.port_spin = ttk.Spinbox(row1, from_=1, to=65535, textvariable=self.port_var, 
                                    width=5, font=('Arial', 10))
        self.port_spin.pack(side=tk.LEFT, padx=(2, 8))
        
        # Unit ID field - very compact
        tk.Label(row1, text="Unit:", font=('Arial', 10), bg=self.COLORS['bg_server'], 
                width=4, anchor='e').pack(side=tk.LEFT)
        self.unit_id_var = tk.IntVar(value=self.unit_id)
        self.unit_id_spin = ttk.Spinbox(row1, from_=1, to=247, textvariable=self.unit_id_var,
                                       width=3, font=('Arial', 10), command=self.update_unit_id)
        self.unit_id_spin.pack(side=tk.LEFT, padx=(2, 0))
        
        # Row 1.5: [Start Server] [Stop Server] - separate row to ensure visibility
        button_row = tk.Frame(server_content, bg=self.COLORS['bg_server'])
        button_row.pack(fill=tk.X, pady=(4, 4))
        
        self.start_btn = ttk.Button(button_row, text="Start Server", command=self.start_server, 
                                   width=12)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        self.stop_btn = ttk.Button(button_row, text="Stop Server", command=self.stop_server,
                                  state=tk.DISABLED, width=12)
        self.stop_btn.pack(side=tk.LEFT)
        
        # Row 2: Status: Server Stopped    Connection: No client connected
        row2 = tk.Frame(server_content, bg=self.COLORS['bg_server'])
        row2.pack(fill=tk.X, pady=(4, 0))
        
        # Status section
        tk.Label(row2, text="Status:", font=('Arial', 9), bg=self.COLORS['bg_server']).pack(side=tk.LEFT)
        self.status_label = tk.Label(row2, text="Server Stopped", bg=self.COLORS['bg_server'], 
                                    fg=self.COLORS['fg_stopped'], font=('Arial', 9, 'bold'))
        self.status_label.pack(side=tk.LEFT, padx=(4, 20))
        
        # Connection section
        tk.Label(row2, text="Connection:", font=('Arial', 9), bg=self.COLORS['bg_server']).pack(side=tk.LEFT)
        self.connection_label = tk.Label(row2, text="No client connected", 
                                        bg=self.COLORS['bg_server'], fg=self.COLORS['fg_disconnected'],
                                        font=('Arial', 9))
        self.connection_label.pack(side=tk.LEFT, padx=(4, 0))
    
    def create_statistics_section(self):
        """Create Statistics section (Column 2)"""
        self.stats_frame = tk.LabelFrame(self.top4, text="Statistics",
                                        bg=self.COLORS['bg_stats'],
                                        fg='#4a148c',
                                        font=('Arial', 10, 'bold'),
                                        relief=tk.RAISED, bd=2)
        
        # Content container
        stats_content = tk.Frame(self.stats_frame, bg=self.COLORS['bg_stats'])
        stats_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        
        # Single compact row layout
        stats_row = tk.Frame(stats_content, bg=self.COLORS['bg_stats'])
        stats_row.pack(fill=tk.X, pady=2)
        
        # Conn: 0  Req: 0  Resp: 0  Err: 0  [Reset]
        tk.Label(stats_row, text="Conn:", font=('Arial', 9), bg=self.COLORS['bg_stats']).pack(side=tk.LEFT)
        self.connections_label = tk.Label(stats_row, text="0", font=('Arial', 9, 'bold'), 
                                         bg=self.COLORS['bg_stats'])
        self.connections_label.pack(side=tk.LEFT, padx=(2, 8))
        
        tk.Label(stats_row, text="Req:", font=('Arial', 9), bg=self.COLORS['bg_stats']).pack(side=tk.LEFT)
        self.requests_label = tk.Label(stats_row, text="0", font=('Arial', 9, 'bold'), 
                                      bg=self.COLORS['bg_stats'])
        self.requests_label.pack(side=tk.LEFT, padx=(2, 8))
        
        tk.Label(stats_row, text="Resp:", font=('Arial', 9), bg=self.COLORS['bg_stats']).pack(side=tk.LEFT)
        self.responses_label = tk.Label(stats_row, text="0", font=('Arial', 9, 'bold'), 
                                       bg=self.COLORS['bg_stats'])
        self.responses_label.pack(side=tk.LEFT, padx=(2, 8))
        
        tk.Label(stats_row, text="Err:", font=('Arial', 9), bg=self.COLORS['bg_stats']).pack(side=tk.LEFT)
        self.errors_label = tk.Label(stats_row, text="0", font=('Arial', 9, 'bold'), 
                                    fg='red', bg=self.COLORS['bg_stats'])
        self.errors_label.pack(side=tk.LEFT, padx=(2, 0))
        
        ttk.Button(stats_row, text="Reset", command=self.reset_statistics,
                  width=8).pack(side=tk.RIGHT)
    
    def create_error_simulation_section(self):
        """Create Error Simulation section (Column 3)"""
        self.error_frame = tk.LabelFrame(self.top4, text="Error Simulation",
                                        bg=self.COLORS['bg_error'],
                                        fg='#e65100',
                                        font=('Arial', 10, 'bold'),
                                        relief=tk.RAISED, bd=2)
        
        # Content container
        error_content = tk.Frame(self.error_frame, bg=self.COLORS['bg_error'])
        error_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        
        # Checkbox with matching background
        self.error_checkbox = tk.Checkbutton(error_content, text="Enable Error Simulation",
                                           variable=self.simulate_errors, bg=self.COLORS['bg_error'],
                                           command=self.toggle_error_options, font=('Arial', 9))
        self.error_checkbox.pack(anchor=tk.W, pady=(0, 4))
        
        # Radio buttons in 2-column layout with matching background
        radio_frame = tk.Frame(error_content, bg=self.COLORS['bg_error'])
        radio_frame.pack(fill=tk.X, padx=4, pady=2)
        radio_frame.grid_columnconfigure(0, weight=1)
        radio_frame.grid_columnconfigure(1, weight=1)
        
        error_types = [
            ("No Error", "none"),
            ("Illegal Function", "illegal_function"),
            ("Illegal Address", "illegal_address"),
            ("Illegal Value", "illegal_value"),
            ("Device Failure", "device_failure"),
            ("", "")  # Empty for 2-column alignment
        ]
        
        self.error_radios = []
        for i, (text, value) in enumerate(error_types):
            if text:  # Skip empty entries
                row = i // 2
                col = i % 2
                radio = tk.Radiobutton(radio_frame, text=text, variable=self.error_type,
                                     value=value, state=tk.DISABLED, bg=self.COLORS['bg_error'],
                                     font=('Arial', 8))
                radio.grid(row=row, column=col, sticky=tk.W, pady=1, padx=2)
                self.error_radios.append(radio)
        
        self.error_type.set("none")
    
    def create_register_management_section(self):
        """Create Register Management section (Column 4)"""
        self.reg_frame = tk.LabelFrame(self.top4, text="Register Management",
                                      bg=self.COLORS['bg_registers'],
                                      fg='#1b5e20',
                                      font=('Arial', 10, 'bold'),
                                      relief=tk.RAISED, bd=2)
        
        # Content container
        reg_content = tk.Frame(self.reg_frame, bg=self.COLORS['bg_registers'])
        reg_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        
        # Row 1: Addr: [0000] Value: [0000] [Set] [Export CSV]
        row1 = tk.Frame(reg_content, bg=self.COLORS['bg_registers'])
        row1.pack(fill=tk.X, pady=(0, 4))
        
        # Left side: Input fields with right-aligned labels
        tk.Label(row1, text="Addr:", font=('Arial', 9), bg=self.COLORS['bg_registers'], 
                width=5, anchor='e').pack(side=tk.LEFT)
        self.reg_addr_var = tk.StringVar(value="0000")
        self.reg_addr_entry = ttk.Entry(row1, textvariable=self.reg_addr_var, width=5, font=('Arial', 9))
        self.reg_addr_entry.pack(side=tk.LEFT, padx=(2, 8))
        
        tk.Label(row1, text="Value:", font=('Arial', 9), bg=self.COLORS['bg_registers'], 
                width=5, anchor='e').pack(side=tk.LEFT)
        self.reg_value_var = tk.StringVar(value="0000")
        self.reg_value_entry = ttk.Entry(row1, textvariable=self.reg_value_var, width=5, font=('Arial', 9))
        self.reg_value_entry.pack(side=tk.LEFT, padx=(2, 8))
        
        # Right side: Action buttons grouped together
        button_frame = tk.Frame(row1, bg=self.COLORS['bg_registers'])
        button_frame.pack(side=tk.RIGHT)
        
        ttk.Button(button_frame, text="Set", command=self.set_register_value, 
                  width=6).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(button_frame, text="Export CSV", command=self.export_registers_csv, 
                  width=10).pack(side=tk.LEFT)
        
        # Row 2: [Clear All] [Test Pattern] - secondary actions
        row2 = tk.Frame(reg_content, bg=self.COLORS['bg_registers'])
        row2.pack(fill=tk.X, pady=4)
        
        ttk.Button(row2, text="Clear All", command=self.clear_all_registers, 
                  width=8).pack(side=tk.LEFT, padx=(0, 4))
        
        ttk.Button(row2, text="Test Pattern", command=self.load_test_pattern, 
                  width=12).pack(side=tk.LEFT)
    
    def set_layout_mode(self, mode: str):
        """Set the layout mode: 'wide', 'medium', or 'narrow'"""
        self.current_layout = mode
        
        # Clear existing grid placements
        for child in self.top4.winfo_children():
            child.grid_remove()
        
        if mode == 'wide':
            # 1x4 horizontal layout
            self.server_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
            self.stats_frame.grid(row=0, column=1, sticky="nsew", padx=8)
            self.error_frame.grid(row=0, column=2, sticky="nsew", padx=8)
            self.reg_frame.grid(row=0, column=3, sticky="nsew", padx=(8, 0))
            
            # Configure for 4 columns
            for c in range(4):
                self.top4.grid_columnconfigure(c, weight=1, uniform="four")
        
        elif mode == 'medium':
            # 2x2 grid layout
            self.server_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 6))
            self.stats_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 6))
            self.error_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(6, 0))
            self.reg_frame.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=(6, 0))
            
            # Configure for 2 columns
            for c in range(2):
                self.top4.grid_columnconfigure(c, weight=1, uniform="two")
            for c in range(2, 4):
                self.top4.grid_columnconfigure(c, weight=0)
        
        else:  # narrow - 1x4 vertical stack
            self.server_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
            self.stats_frame.grid(row=1, column=0, sticky="nsew", pady=6)
            self.error_frame.grid(row=2, column=0, sticky="nsew", pady=6)
            self.reg_frame.grid(row=3, column=0, sticky="nsew", pady=(6, 0))
            
            # Single column
            self.top4.grid_columnconfigure(0, weight=1)
            for c in range(1, 4):
                self.top4.grid_columnconfigure(c, weight=0)
    
    def on_window_resize(self, event=None):
        """Handle window resize for responsive layout"""
        if event and event.widget == self.frame:
            width = self.frame.winfo_width()
            
            if width >= 1200:
                new_mode = 'wide'
            elif width >= 900:
                new_mode = 'medium'  
            else:
                new_mode = 'narrow'
            
            if new_mode != self.current_layout:
                self.set_layout_mode(new_mode)
    
    def create_bottom_layout(self):
        """Create the bottom two-column layout (unchanged from original)"""
        # Two-column layout with equal widths for Register Map and Communication Log
        columns_frame = tk.Frame(self.main_frame, bg=self.COLORS['bg_main'])
        columns_frame.pack(fill=tk.BOTH, expand=True)
        # Ensure both columns have exactly equal weights
        columns_frame.columnconfigure(0, weight=1, uniform="bottom_columns")
        columns_frame.columnconfigure(1, weight=1, uniform="bottom_columns")
        columns_frame.rowconfigure(0, weight=1)
        
        # Left column
        left_column = tk.Frame(columns_frame, bg=self.COLORS['bg_main'])
        left_column.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        # Right column
        right_column = tk.Frame(columns_frame, bg=self.COLORS['bg_main'])
        right_column.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        
        # Register Map Display (Left)
        self.create_register_map_display(left_column)
        
        # Communication Log (Right)
        self.create_communication_log(right_column)
    
    def create_register_map_display(self, parent):
        """Create register map display"""
        reg_display_frame = tk.LabelFrame(parent, text="Register Map",
                                         bg=self.COLORS['bg_regmap'],
                                         fg='#212121',
                                         font=('Arial', 10, 'bold'),
                                         relief=tk.RAISED, bd=2)
        reg_display_frame.pack(fill=tk.BOTH, expand=True, padx=5)
        
        # Register map container
        regmap_container = tk.Frame(reg_display_frame, bg=self.COLORS['bg_regmap'])
        regmap_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        
        # Register map with enhanced styling
        self.register_display = scrolledtext.ScrolledText(
            regmap_container, wrap=tk.NONE, height=20, width=50,
            font=("Courier", 11), bg='#FAFAFA',
            relief=tk.SUNKEN, bd=1
        )
        self.register_display.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for better readability
        self.register_display.tag_config("header", font=("Courier", 11, "bold"), foreground="#333333")
        self.register_display.tag_config("address", font=("Courier", 11, "bold"), foreground="#0066CC")
        self.register_display.tag_config("value", font=("Courier", 11), foreground="#006600")
    
    def create_communication_log(self, parent):
        """Create communication log"""
        log_frame = tk.LabelFrame(parent, text="Communication Log",
                                 bg=self.COLORS['bg_log'],
                                 fg='#212121',
                                 font=('Arial', 10, 'bold'),
                                 relief=tk.RAISED, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5)
        
        # Log container
        log_container = tk.Frame(log_frame, bg=self.COLORS['bg_log'])
        log_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        
        # Log toolbar with better alignment
        log_toolbar = tk.Frame(log_container, bg=self.COLORS['bg_log'])
        log_toolbar.pack(fill=tk.X, pady=(0, 8))
        
        # Auto-scroll checkbox
        tk.Checkbutton(log_toolbar, text="Auto-scroll", variable=self.auto_scroll,
                      bg=self.COLORS['bg_log'], font=('Arial', 9)).pack(side=tk.LEFT)
        
        # Clear button
        ttk.Button(log_toolbar, text="Clear Log", command=self.clear_log, 
                  width=10, style='Clear.TButton').pack(side=tk.RIGHT)
        
        # Log display with proper styling
        self.log_display = scrolledtext.ScrolledText(log_container, wrap=tk.WORD, height=20,
                                                    font=("Courier", 10),
                                                    relief=tk.SUNKEN, bd=1)
        self.log_display.pack(fill=tk.BOTH, expand=True)
        
        # Configure log tags
        self.log_display.tag_config("info", foreground="blue")
        self.log_display.tag_config("request", foreground="green")
        self.log_display.tag_config("response", foreground="purple")
        self.log_display.tag_config("error", foreground="red")
        self.log_display.tag_config("system", foreground="gray")
    
    # === EVENT HANDLERS ===
    
    def update_unit_id(self):
        """Update unit ID"""
        self.unit_id = self.unit_id_var.get()
    
    def toggle_error_options(self):
        """Toggle error simulation options"""
        if self.simulate_errors.get():
            for radio in self.error_radios:
                radio.config(state=tk.NORMAL)
        else:
            for radio in self.error_radios:
                radio.config(state=tk.DISABLED)
            self.error_type.set("none")
    
    def start_server(self):
        """Start Modbus TCP server"""
        if self.is_running:
            return
        
        try:
            ip = self.ip_var.get().strip()
            port = self.port_var.get()
            
            if not ip:
                messagebox.showerror("Error", "Please enter IP address")
                return
            
            # Create and bind socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((ip, port))
            self.server_socket.listen(1)
            
            self.is_running = True
            
            # Start server thread
            self.server_thread = threading.Thread(target=self.server_worker, daemon=True)
            self.server_thread.start()
            
            # Update UI
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.ip_entry.config(state=tk.DISABLED)
            self.port_spin.config(state=tk.DISABLED)
            self.status_label.config(text="Server Running", fg=self.COLORS['fg_running'])
            
            self.add_log(f"Server started on {ip}:{port}", "info")
            
        except Exception as e:
            messagebox.showerror("Server Error", f"Failed to start server: {str(e)}")
            self.stop_server()
    
    def stop_server(self):
        """Stop Modbus TCP server"""
        self.is_running = False
        self.is_connected = False
        
        # Close client socket
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        
        # Update UI
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.ip_entry.config(state=tk.NORMAL)
        self.port_spin.config(state=tk.NORMAL)
        self.status_label.config(text="Server Stopped", fg=self.COLORS['fg_stopped'])
        self.connection_label.config(text="No client connected", fg=self.COLORS['fg_disconnected'])
        
        self.add_log("Server stopped", "info")
    
    def server_worker(self):
        """Server worker thread"""
        while self.is_running:
            try:
                if not self.server_socket:
                    break
                
                self.server_socket.settimeout(1.0)
                client_socket, client_address = self.server_socket.accept()
                
                with self.socket_lock:
                    self.client_socket = client_socket
                    self.client_address = client_address
                    self.is_connected = True
                
                self.connection_count += 1
                self.frame.after(0, self.update_statistics)
                self.frame.after(0, lambda: self.connection_label.config(
                    text=f"{client_address[0]}:{client_address[1]}", fg=self.COLORS['fg_connected']))
                self.frame.after(0, lambda: self.add_log(
                    f"Client connected: {client_address[0]}:{client_address[1]}", "info"))
                
                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=self.client_worker, args=(client_socket, client_address), daemon=True)
                client_thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    self.frame.after(0, lambda: self.add_log(f"Server error: {str(e)}", "error"))
                break
    
    def client_worker(self, client_socket: socket.socket, client_address: Tuple[str, int]):
        """Handle client connection"""
        try:
            while self.is_running and self.is_connected:
                client_socket.settimeout(1.0)
                data = client_socket.recv(1024)
                
                if not data:
                    break
                
                # Process request
                response_data = self.process_modbus_request(data)
                if response_data:
                    client_socket.send(response_data)
                
        except socket.timeout:
            # Normal timeout during shutdown
            pass
        except Exception as e:
            if self.is_running:
                self.frame.after(0, lambda: self.add_log(f"Client error: {str(e)}", "error"))
        finally:
            try:
                client_socket.close()
            except:
                pass
            
            with self.socket_lock:
                if self.client_socket == client_socket:
                    self.client_socket = None
                    self.is_connected = False
            
            self.frame.after(0, lambda: self.connection_label.config(text="No client connected", fg=self.COLORS['fg_disconnected']))
            self.frame.after(0, lambda: self.add_log(
                f"Client disconnected: {client_address[0]}:{client_address[1]}", "info"))
    
    def process_modbus_request(self, data: bytes) -> Optional[bytes]:
        """Process Modbus TCP request"""
        try:
            # Parse request
            request = ModbusTCPFrame.from_bytes(data)
            if not request:
                return None
            
            self.request_count += 1
            self.frame.after(0, self.update_statistics)
            
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Check for error simulation
            if self.simulate_errors.get() and self.error_type.get() != "none":
                return self.generate_error_response(request)
            
            # Process based on function code
            if request.function_code == ModbusFunctionCode.READ_HOLDING_REGISTERS:
                parsed = ModbusTCPParser.parse_read_holding_registers_request(request)
                if parsed:
                    values = self.register_map.read_registers(parsed['start_address'], parsed['count'])
                    response = ModbusTCPBuilder.read_holding_registers_response(
                        request.transaction_id, request.unit_id, values)
                    
                    self.frame.after(0, lambda: self.add_log(
                        f"[{timestamp}] Read {parsed['count']} registers from {parsed['start_address']:04X}", "request"))
                    
                    self.response_count += 1
                    self.frame.after(0, self.update_statistics)
                    return response.to_bytes()
            
            elif request.function_code == ModbusFunctionCode.WRITE_MULTIPLE_REGISTERS:
                parsed = ModbusTCPParser.parse_write_multiple_registers_request(request)
                if parsed:
                    self.register_map.write_registers(parsed['start_address'], parsed['values'])
                    response = ModbusTCPBuilder.write_multiple_registers_response(
                        request.transaction_id, request.unit_id,
                        parsed['start_address'], len(parsed['values']))
                    
                    self.frame.after(0, lambda: self.add_log(
                        f"[{timestamp}] Write {len(parsed['values'])} registers to {parsed['start_address']:04X}", "request"))
                    self.frame.after(0, self.refresh_register_view)
                    
                    self.response_count += 1
                    self.frame.after(0, self.update_statistics)
                    return response.to_bytes()
            
            # Unsupported function code
            return self.generate_illegal_function_response(request)
            
        except Exception as e:
            self.error_count += 1
            self.frame.after(0, self.update_statistics)
            self.frame.after(0, lambda: self.add_log(f"Process error: {str(e)}", "error"))
            return None
    
    def generate_error_response(self, request: ModbusTCPFrame) -> bytes:
        """Generate error response based on simulation settings"""
        error_type = self.error_type.get()
        
        if error_type == "illegal_function":
            exception_code = 0x01
        elif error_type == "illegal_address":
            exception_code = 0x02
        elif error_type == "illegal_value":
            exception_code = 0x03
        elif error_type == "device_failure":
            exception_code = 0x04
        else:
            return None
        
        response = ModbusTCPBuilder.exception_response(
            request.transaction_id, request.unit_id,
            request.function_code, exception_code)
        
        self.error_count += 1
        self.frame.after(0, self.update_statistics)
        self.frame.after(0, lambda: self.add_log(f"Simulated error: {error_type}", "error"))
        
        return response.to_bytes()
    
    def generate_illegal_function_response(self, request: ModbusTCPFrame) -> bytes:
        """Generate illegal function response"""
        response = ModbusTCPBuilder.exception_response(
            request.transaction_id, request.unit_id,
            request.function_code, 0x01)
        
        self.error_count += 1
        self.frame.after(0, self.update_statistics)
        self.frame.after(0, lambda: self.add_log(
            f"Illegal function: 0x{request.function_code:02X}", "error"))
        
        return response.to_bytes()
    
    # === UI UPDATE METHODS ===
    
    def set_register_value(self):
        """Set register value"""
        try:
            addr = int(self.reg_addr_var.get(), 16)
            value = int(self.reg_value_var.get(), 16)
            
            if addr > 999:
                messagebox.showerror("Error", "Address must be 0-999")
                return
            
            if value > 65535:
                messagebox.showerror("Error", "Value must be 0-65535")
                return
            
            self.register_map.set_register(addr, value)
            self.refresh_register_view()
            self.add_log(f"Set register {addr:04X} = {value:04X}", "system")
            
        except ValueError:
            messagebox.showerror("Error", "Invalid address or value")
    
    def clear_all_registers(self):
        """Clear all registers"""
        if messagebox.askyesno("Confirm", "Clear all registers to zero?"):
            for i in range(1000):
                self.register_map.set_register(i, 0)
            self.refresh_register_view()
            self.add_log("All registers cleared", "system")
    
    def load_test_pattern(self):
        """Load test pattern"""
        for i in range(20):
            self.register_map.set_register(i, i * 0x1111)
        self.refresh_register_view()
        self.add_log("Test pattern loaded", "system")
    
    def export_registers_csv(self):
        """Export registers to CSV"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export Registers"
            )
            
            if filename:
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["Address", "Value_Hex", "Value_Dec"])
                    
                    for addr in range(1000):
                        value = self.register_map.get_register(addr)
                        if value != 0:  # Only export non-zero values
                            writer.writerow([f"0x{addr:04X}", f"0x{value:04X}", str(value)])
                
                self.add_log(f"Registers exported to {filename}", "system")
                
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {str(e)}")
    
    def refresh_register_view(self):
        """Refresh register map display"""
        self.register_display.config(state=tk.NORMAL)
        self.register_display.delete(1.0, tk.END)
        
        # Header
        self.register_display.insert(tk.END, "Address  Value   Dec\n", "header")
        self.register_display.insert(tk.END, "-------  -----  -----\n", "header")
        
        # Show non-zero registers
        for addr in range(1000):
            value = self.register_map.get_register(addr)
            if value != 0:
                addr_str = f"{addr:04X}"
                value_str = f"{value:04X}"
                dec_str = f"{value:5d}"
                
                self.register_display.insert(tk.END, f"0x{addr_str}  ", "address")
                self.register_display.insert(tk.END, f"0x{value_str}  ", "value")
                self.register_display.insert(tk.END, f"{dec_str}\n")
        
        self.register_display.config(state=tk.DISABLED)
    
    def reset_statistics(self):
        """Reset all statistics"""
        self.connection_count = 0
        self.request_count = 0
        self.response_count = 0
        self.error_count = 0
        self.update_statistics()
        self.add_log("Statistics reset", "system")
    
    def update_statistics(self):
        """Update statistics display"""
        self.connections_label.config(text=str(self.connection_count))
        self.requests_label.config(text=str(self.request_count))
        self.responses_label.config(text=str(self.response_count))
        self.errors_label.config(text=str(self.error_count))
    
    def add_log(self, message: str, tag: str = "system"):
        """Add message to log display"""
        self.log_display.insert(tk.END, message + "\n", tag)
        if self.auto_scroll.get():
            self.log_display.see(tk.END)
    
    def clear_log(self):
        """Clear the log display"""
        self.log_display.delete(1.0, tk.END)