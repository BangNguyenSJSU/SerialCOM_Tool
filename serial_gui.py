#!/usr/bin/env python3
"""
PySerial GUI Application
A cross-platform serial communication tool with Tkinter interface
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from tkinter import font as tkfont
import serial
import serial.tools.list_ports
import threading
import queue
import datetime
import platform
import os
from typing import Optional, List, Tuple
import json
from host_tab import HostTab
from device_tab import DeviceTab
from modbus_tcp_slave_tab import ModbusTCPSlaveTab
from modbus_tcp_master_tab import ModbusTCPMasterTab
from ai_analyzer import AIAnalyzer
from ai_config import AIConfig
from ai_settings_dialog import AISettingsDialog
from serial_connection import SerialConnection


class ToolTip:
    """Create tooltips for widgets"""
    def __init__(self, widget, text=''):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
    
    def on_enter(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tooltip, text=self.text, justify=tk.LEFT,
                        relief=tk.SOLID, borderwidth=1,
                        font=("Arial", 9))
        label.pack()
    
    def on_leave(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


class SerialGUI:
    """Main GUI application for serial communication with protocol support.
    
    This class manages the main window, serial connection, and coordinates
    between different tabs (Data Display, Hex Display, Host, Device).
    It handles threading for non-blocking I/O and maintains the GUI event loop.
    """
    
    # Color scheme for better UI visualization
    COLORS = {
        'bg_main': '#f0f0f0',           # Light gray main background
        'bg_connection': '#e3f2fd',     # Light blue for connection section
        'bg_options': '#f3e5f5',        # Light purple for options
        'bg_transmit': '#e8f5e9',       # Light green for transmit section
        'bg_macros': '#fff3e0',         # Light amber for macro buttons
        'bg_display': '#ffffff',        # White for text displays
        'fg_connected': '#4caf50',      # Green for connected status
        'fg_disconnected': '#f44336',   # Red for disconnected status
        'fg_highlight': '#2196f3',      # Blue for highlights
        'border_color': '#cccccc',      # Light gray for borders
        'button_active': '#1976d2',     # Dark blue for active buttons
        'button_hover': '#42a5f5',      # Light blue for hover
        
        # Tab-specific colors
        'tab_data': '#2196F3',          # Blue for Data Display tab
        'tab_data_bg': '#E3F2FD',       # Light blue background
        'tab_hex': '#9C27B0',           # Purple for Hex Display tab
        'tab_hex_bg': '#F3E5F5',        # Light purple background
        'tab_host': '#4CAF50',          # Green for Host tab
        'tab_host_bg': '#E8F5E9',       # Light green background
        'tab_device': '#FF9800',        # Orange for Device tab
        'tab_device_bg': '#FFF3E0',     # Light orange background
    }
    
    def __init__(self, root: tk.Tk):
        """Initialize the SerialGUI application.
        
        Args:
            root: The Tkinter root window instance
        """
        self.root = root
        self.root.title("Serial Communication Tool")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        self.root.configure(bg=self.COLORS['bg_main'])
        
        # Serial connection state management
        self.serial_port: Optional[serial.Serial] = None  # Active serial port instance
        self.is_connected = False  # Connection status flag
        
        # Threading and queue for thread-safe data transfer
        # Queue passes data from read thread to GUI thread safely
        self.data_queue = queue.Queue()
        self.read_thread: Optional[threading.Thread] = None  # Background thread for reading serial data
        self.running = False  # Flag to control read thread execution
        
        # AI Analysis components
        self.ai_config = AIConfig()
        self.ai_analyzer: Optional[AIAnalyzer] = None
        self.ai_queue = queue.Queue()  # Queue for AI analysis results
        self.ai_enabled = tk.BooleanVar(value=False)
        self.ai_data_buffer = []  # Buffer for recent data for pattern analysis
        
        # User configurable settings
        self.hex_view_enabled = tk.BooleanVar(value=False)  # Toggle hex display mode
        self.auto_scroll_enabled = tk.BooleanVar(value=True)  # Auto-scroll to latest data
        self.logging_enabled = tk.BooleanVar(value=False)  # Enable CSV logging
        self.log_file = None  # File handle for CSV logging
        
        # Command history for arrow key navigation
        self.command_history: List[str] = []  # List of previously sent commands
        self.history_index = -1  # Current position in history (-1 = no selection)
        
        # After ID for GUI updates
        self.after_id = None
        
        # Build the interface
        self.create_widgets()
        self.refresh_ports()
        
        # Start GUI update loop
        self.update_gui()
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_styles(self):
        """Configure ttk styles with custom colors"""
        style = ttk.Style()
        
        # Configure label styles for different sections
        style.configure('Connection.TLabel')
        style.configure('Options.TLabel')
        style.configure('Transmit.TLabel')
        style.configure('Macros.TLabel')
        
        # Configure button styles
        style.configure('Connect.TButton', foreground=self.COLORS['fg_connected'])
        style.configure('Disconnect.TButton', foreground=self.COLORS['fg_disconnected'])
        
        # Configure LabelFrame styles
        style.configure('Connection.TLabelframe')
        style.configure('Options.TLabelframe')
        style.configure('Transmit.TLabelframe')
        style.configure('Macros.TLabelframe')
        style.configure('Macros.TLabelframe.Label')
        
        # Configure Notebook tab styles for better visibility
        style.configure('TNotebook', borderwidth=0)
        style.configure('TNotebook.Tab', 
                       padding=[20, 12],  # Increased padding for larger tabs
                       font=('Arial', 11, 'bold'))  # Bold font for better visibility
        
        # Configure tab colors for different states
        style.map('TNotebook.Tab',
                 background=[('selected', self.COLORS['bg_main']),  # Same background for selected tab
                            ('active', '#e0e0e0')],    # Light gray on hover
                 foreground=[('selected', '#000000'),  # Black text for selected
                            ('active', '#333333')],     # Dark gray on hover
                 expand=[('selected', [1, 1, 1, 0])])  # Expand selected tab
        
        # Custom styles for each tab (for visual differentiation)
        style.configure('Data.TFrame', background=self.COLORS['bg_main'])
        style.configure('Hex.TFrame', background=self.COLORS['bg_main'])
        style.configure('Host.TFrame', background=self.COLORS['bg_main'])
        style.configure('Device.TFrame', background=self.COLORS['bg_main'])
    
    def create_widgets(self):
        """Create all GUI widgets"""
        # Configure styles for ttk widgets
        self.setup_styles()
        
        # Top frame - Connection controls with blue background
        top_frame = tk.Frame(self.root, bg=self.COLORS['bg_main'])
        top_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Options frame with purple background
        options_frame = tk.Frame(self.root, bg=self.COLORS['bg_main'])
        options_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Checkboxes for options with tooltips
        hex_check = ttk.Checkbutton(options_frame, text="Hex View", variable=self.hex_view_enabled)
        hex_check.pack(side=tk.LEFT, padx=5)
        ToolTip(hex_check, "Display data in hexadecimal format (00-FF)\nUseful for viewing binary protocols")
        
        auto_check = ttk.Checkbutton(options_frame, text="Auto Scroll", variable=self.auto_scroll_enabled)
        auto_check.pack(side=tk.LEFT, padx=5)
        ToolTip(auto_check, "Automatically scroll to show newest data\nDisable to examine earlier messages")
        
        log_check = ttk.Checkbutton(options_frame, text="Log to File", variable=self.logging_enabled, 
                                   command=self.toggle_logging)
        log_check.pack(side=tk.LEFT, padx=5)
        ToolTip(log_check, "Save all communication to a CSV file\nFile will be created in current directory")
        
        # Clear button
        ttk.Button(options_frame, text="Clear Display", command=self.clear_display).pack(side=tk.LEFT, padx=5)
        
        # Main content area with notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Combined data display tab with format multiplexing
        data_tab = ttk.Frame(self.notebook, style='Data.TFrame')
        self.notebook.add(data_tab, text="📊 Data Display")
        
        # Add header label for combined Data Display tab
        data_header = tk.Label(data_tab, text="📊 DATA DISPLAY - Real-time Serial Communication",
                              fg='#333333',
                              font=('Arial', 14, 'bold'), pady=10)
        data_header.pack(fill=tk.X)
        
        # Create independent serial connection for Data Display tab
        self.data_tab_serial = SerialConnection(data_tab, self.on_data_tab_data_received)
        
        # Display format controls
        format_frame = tk.Frame(data_tab, bg=self.COLORS['bg_main'])
        format_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Format selection checkbox
        self.hex_format_var = tk.BooleanVar(value=False)
        self.hex_format_checkbox = ttk.Checkbutton(format_frame, text="Display as Hexadecimal",
                                                  variable=self.hex_format_var,
                                                  command=self.toggle_display_format)
        self.hex_format_checkbox.pack(side=tk.LEFT, padx=10)
        
        # Clear button for current display
        ttk.Button(format_frame, text="Clear Display", 
                  command=self.clear_current_display).pack(side=tk.RIGHT, padx=10)
        
        # Text display (ASCII format)
        self.rx_display = scrolledtext.ScrolledText(data_tab, wrap=tk.WORD, width=80, height=15, 
                                                    font=("Courier", 14), 
                                                    relief=tk.SUNKEN, bd=2)
        self.rx_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.rx_display.config(state=tk.DISABLED)
        
        # Hex display (initially hidden)
        self.hex_display = scrolledtext.ScrolledText(data_tab, wrap=tk.WORD, width=80, height=15, 
                                                     font=("Courier", 14),
                                                     relief=tk.SUNKEN, bd=2)
        self.hex_display.config(state=tk.DISABLED)
        # Don't pack initially - will be shown/hidden by toggle_display_format()
        
        # Command section for Data Display tab
        data_cmd_frame = tk.Frame(data_tab, bg=self.COLORS['bg_main'])
        data_cmd_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Command entry
        ttk.Label(data_cmd_frame, text="Command:").pack(side=tk.LEFT, padx=5)
        self.command_entry = ttk.Entry(data_cmd_frame, width=50)
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.command_entry.bind("<Return>", lambda e: self.send_command())
        self.command_entry.bind("<Up>", self.history_up)
        self.command_entry.bind("<Down>", self.history_down)
        
        # Send button
        self.send_btn = ttk.Button(data_cmd_frame, text="Send", command=self.send_command, state=tk.DISABLED)
        self.send_btn.pack(side=tk.LEFT, padx=5)
        
        # Line ending options
        ttk.Label(data_cmd_frame, text="Line End:").pack(side=tk.LEFT, padx=5)
        self.line_ending_var = tk.StringVar(value="\\r\\n")
        line_endings = ["None", "\\r", "\\n", "\\r\\n"]
        self.line_ending_combo = ttk.Combobox(data_cmd_frame, textvariable=self.line_ending_var, 
                                             values=line_endings, width=8)
        self.line_ending_combo.pack(side=tk.LEFT, padx=5)
        
        # Quick Commands section for Data Display tab
        data_macro_frame = ttk.LabelFrame(data_tab, text="Quick Commands", padding="5")
        data_macro_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        # Create container for centered button alignment
        data_button_container = tk.Frame(data_macro_frame, bg=self.COLORS['bg_main'])
        data_button_container.pack(fill=tk.X, padx=10, pady=5)
        
        # Configure equal spacing for buttons
        for i in range(4):
            data_button_container.grid_columnconfigure(i, weight=1)
        
        button_width = 10
        macro_buttons = [
            ("Reset", "RESET"),
            ("Status", "STATUS"), 
            ("Help", "HELP"),
            ("Version", "VERSION")
        ]
        
        for i, (text, command) in enumerate(macro_buttons):
            btn = ttk.Button(data_button_container, text=text, width=button_width,
                           command=lambda cmd=command: self.send_macro(cmd))
            btn.grid(row=0, column=i, padx=5, sticky='ew')
        
        # AI Analysis section for Data Display tab
        ai_analysis_frame = ttk.LabelFrame(data_tab, text="🤖 AI Analysis", padding="5")
        ai_analysis_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        # AI Controls
        ai_controls = tk.Frame(ai_analysis_frame, bg=self.COLORS['bg_main'])
        ai_controls.pack(fill=tk.X, padx=5, pady=5)
        
        # AI Analysis Toggle Button
        self.ai_toggle_btn = ttk.Button(ai_controls, text="Enable AI Analysis", 
                                       command=self.toggle_ai_analysis)
        self.ai_toggle_btn.pack(side=tk.LEFT, padx=5)
        
        # API Key Status Indicator
        self.ai_status = tk.Label(ai_controls, text="API Key: Not Set", 
                                 fg='#CC0000', font=("Arial", 9))
        self.ai_status.pack(side=tk.LEFT, padx=10)
        
        # AI Settings Button
        self.ai_settings_btn = ttk.Button(ai_controls, text="AI Settings", 
                                         command=self.open_ai_settings)
        self.ai_settings_btn.pack(side=tk.RIGHT, padx=5)
        
        # AI Statistics display
        self.ai_stats_label = tk.Label(ai_controls, text="", 
                                      fg='#666666', font=("Arial", 8))
        self.ai_stats_label.pack(side=tk.RIGHT, padx=10)
        
        # Initialize AI status
        self.update_ai_status()
        
        # Display controls section for Data Display tab
        data_status_frame = tk.Frame(data_tab, bg=self.COLORS['bg_main'])
        data_status_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        # Font size label and controls (improved visibility and layout)
        font_controls_frame = tk.Frame(data_status_frame, bg=self.COLORS['bg_main'], relief=tk.FLAT, bd=1)
        font_controls_frame.pack(side=tk.RIGHT, padx=10, pady=2)
        
        # Font size label with better contrast
        font_label = tk.Label(font_controls_frame, text="Font Size:", fg='#333333',
                             font=("Arial", 10, "bold"), bg=self.COLORS['bg_main'])
        font_label.pack(side=tk.LEFT, padx=(5, 8))
        
        # Font size spinbox with proper width and current value display
        self.font_size_var = tk.IntVar(value=14)
        font_spin = ttk.Spinbox(font_controls_frame, from_=10, to=20, width=5,
                               textvariable=self.font_size_var, command=self.update_font_size,
                               justify='center')
        font_spin.pack(side=tk.LEFT, padx=(0, 8))
        
        # Current size indicator
        self.current_font_label = tk.Label(font_controls_frame, text="(14pt)", fg='#666666',
                                          font=("Arial", 9), bg=self.COLORS['bg_main'])
        self.current_font_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Create tags for different message types (both displays)
        self.rx_display.tag_config("rx", foreground="blue")
        self.rx_display.tag_config("tx", foreground="green")
        self.rx_display.tag_config("error", foreground="red")
        self.rx_display.tag_config("system", foreground="gray")
        
        # AI Analysis Tags
        self.rx_display.tag_config("ai_insight", foreground="#FF6600", 
                                  background="#FFF8E0", font=("Courier", 14, "bold"))
        self.rx_display.tag_config("ai_protocol", foreground="#8B008B", 
                                  background="#FFF0FF", font=("Courier", 14, "bold"))
        self.rx_display.tag_config("ai_error", foreground="#DC143C", 
                                  background="#FFE4E1", font=("Courier", 14, "bold"))
        self.rx_display.tag_config("ai_pattern", foreground="#006400", 
                                  background="#F0FFF0", font=("Courier", 14, "bold"))
        
        # Same tags for hex display
        self.hex_display.tag_config("rx", foreground="blue")
        self.hex_display.tag_config("tx", foreground="green")
        self.hex_display.tag_config("error", foreground="red")
        self.hex_display.tag_config("system", foreground="gray")
        
        # AI Analysis Tags for hex display
        self.hex_display.tag_config("ai_insight", foreground="#FF6600", 
                                   background="#FFF8E0", font=("Courier", 14, "bold"))
        self.hex_display.tag_config("ai_protocol", foreground="#8B008B", 
                                   background="#FFF0FF", font=("Courier", 14, "bold"))
        self.hex_display.tag_config("ai_error", foreground="#DC143C", 
                                   background="#FFE4E1", font=("Courier", 14, "bold"))
        self.hex_display.tag_config("ai_pattern", foreground="#006400", 
                                   background="#F0FFF0", font=("Courier", 14, "bold"))
        
        
        # Host tab (Protocol Master) with green theme
        host_tab = ttk.Frame(self.notebook, style='Host.TFrame')
        self.notebook.add(host_tab, text="📤 Host (Master)")
        
        # Add header label for Host tab
        host_header = tk.Label(host_tab, text="📤 HOST MODE - Master Protocol Controller",
                              fg='#333333',
                              font=('Arial', 14, 'bold'), pady=10)
        host_header.pack(fill=tk.X)
        
        self.host_tab = HostTab(host_tab)
        
        # Device tab (Protocol Slave) with orange theme
        device_tab = ttk.Frame(self.notebook, style='Device.TFrame')
        self.notebook.add(device_tab, text="📥 Device (Slave)")
        
        # Add header label for Device tab
        device_header = tk.Label(device_tab, text="📥 DEVICE MODE - Slave Protocol Simulator",
                                fg='#333333',
                                font=('Arial', 14, 'bold'), pady=10)
        device_header.pack(fill=tk.X)
        
        self.device_tab = DeviceTab(device_tab)
        
        # Modbus TCP Master tab with purple theme
        modbus_master_tab = ttk.Frame(self.notebook, style='Hex.TFrame')
        self.notebook.add(modbus_master_tab, text="🔌 Modbus TCP Master")
        
        # Add header label for Modbus TCP Master tab with improved styling
        modbus_master_header = tk.Label(modbus_master_tab, text="🔌   MODBUS TCP MASTER - Client Mode",
                                       fg='#333333',
                                       font=('Arial', 16, 'bold'), pady=12)
        modbus_master_header.pack(fill=tk.X)
        
        self.modbus_master_tab = ModbusTCPMasterTab(modbus_master_tab)
        
        # Modbus TCP Slave tab with blue theme
        modbus_slave_tab = ttk.Frame(self.notebook, style='Data.TFrame')
        self.notebook.add(modbus_slave_tab, text="🌐 Modbus TCP Slave")
        
        # Add header label for Modbus TCP Slave tab with improved styling
        modbus_slave_header = tk.Label(modbus_slave_tab, text="🌐   MODBUS TCP SLAVE - Server Mode",
                                      fg='#333333',
                                      font=('Arial', 16, 'bold'), pady=12)
        modbus_slave_header.pack(fill=tk.X)
        
        self.modbus_slave_tab = ModbusTCPSlaveTab(modbus_slave_tab)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)
    
    def update_font_size(self):
        """Update font size for all text displays"""
        try:
            new_size = self.font_size_var.get()
            new_font = ("Courier", new_size)
            
            # Update main displays
            self.rx_display.config(font=new_font)
            self.hex_display.config(font=new_font)
            
            # Update tab displays if they exist
            if hasattr(self, 'host_tab') and hasattr(self.host_tab, 'log_display'):
                self.host_tab.log_display.config(font=new_font)
                self.host_tab.preview_text.config(font=("Courier", max(10, new_size-2)))
            
            if hasattr(self, 'device_tab'):
                if hasattr(self.device_tab, 'incoming_request_log'):
                    self.device_tab.incoming_request_log.config(font=new_font)
                if hasattr(self.device_tab, 'outgoing_response_log'):
                    self.device_tab.outgoing_response_log.config(font=new_font)
            
            # Update Modbus TCP tab displays if they exist
            if hasattr(self, 'modbus_slave_tab') and hasattr(self.modbus_slave_tab, 'log_display'):
                self.modbus_slave_tab.log_display.config(font=new_font)
                self.modbus_slave_tab.register_display.config(font=new_font)
            
            if hasattr(self, 'modbus_master_tab') and hasattr(self.modbus_master_tab, 'log_display'):
                self.modbus_master_tab.log_display.config(font=new_font)
                self.modbus_master_tab.preview_text.config(font=new_font)
            
            # Update current font size indicator
            if hasattr(self, 'current_font_label'):
                self.current_font_label.config(text=f"({new_size}pt)")
                    
        except Exception as e:
            print(f"Font update error: {e}")
    
    def refresh_ports(self):
        """Scan and refresh available serial ports.
        
        This method detects both physical serial ports (via pyserial) and
        virtual TTY ports (for testing with socat). Updates the port
        dropdown with all available ports.
        """
        ports = serial.tools.list_ports.comports()
        port_list = []
        
        # Add pyserial detected ports
        for port in ports:
            # Format port description
            if platform.system() == "Windows":
                port_desc = f"{port.device} - {port.description}"
            else:
                port_desc = f"{port.device} ({port.description})"
            port_list.append(port_desc)
        
        # Add virtual TTY ports (for testing with socat)
        import glob
        virtual_ports = glob.glob('/dev/ttys[0-9]*')
        for port_path in sorted(virtual_ports):
            # Check if port is usable
            try:
                with serial.Serial(port_path, timeout=0, write_timeout=0) as test_ser:
                    port_desc = f"{port_path} (Virtual TTY)"
                    if port_desc not in port_list:
                        port_list.append(port_desc)
            except:
                pass  # Skip ports that can't be opened
        
        # Update combo box
        # self.port_combo['values'] = port_list
        # if port_list:
        #     self.port_combo.current(0)
        
        # Add detailed status message with port list
        if port_list:
            self.add_system_message(f"Found {len(port_list)} serial port(s):")
            for i, port_desc in enumerate(port_list[:5], 1):  # Show first 5 ports
                self.add_system_message(f"  {i}. {port_desc}")
            if len(port_list) > 5:
                self.add_system_message(f"  ... and {len(port_list) - 5} more")
        else:
            self.add_system_message("No serial ports found")
    
    def get_parity_constant(self, parity_str: str):
        """Convert parity string to serial constant"""
        parity_map = {
            "None": serial.PARITY_NONE,
            "Even": serial.PARITY_EVEN,
            "Odd": serial.PARITY_ODD,
            "Mark": serial.PARITY_MARK,
            "Space": serial.PARITY_SPACE
        }
        return parity_map.get(parity_str, serial.PARITY_NONE)
    
    def get_stopbits_constant(self, stopbits_str: str):
        """Convert stop bits string to serial constant"""
        stopbits_map = {
            "1": serial.STOPBITS_ONE,
            "1.5": serial.STOPBITS_ONE_POINT_FIVE,
            "2": serial.STOPBITS_TWO
        }
        return stopbits_map.get(stopbits_str, serial.STOPBITS_ONE)
    
    def toggle_connection(self):
        """Connect or disconnect serial port"""
        if not self.is_connected:
            self.connect_serial()
        else:
            self.disconnect_serial()
    
    def connect_serial(self):
        """Establish serial connection with selected port.
        
        Creates a serial connection using the selected parameters,
        starts the read thread for non-blocking I/O, and updates
        the UI to reflect the connected state.
        
        Raises:
            SerialException: If connection fails
        """
        try:
            # Extract port name from combo selection
            # port_selection = self.port_var.get()
            # if not port_selection:
            #     messagebox.showerror("Error", "Please select a serial port")
            #     return
            
            # Extract just the port name (before the dash or parenthesis)
            # if platform.system() == "Windows":
            #     port = port_selection.split(" - ")[0]
            # else:
            #     port = port_selection.split(" (")[0]
            
            # Get connection parameters
            # baud = int(self.baud_var.get())
            # databits = int(self.databits_var.get())
            # parity = self.get_parity_constant(self.parity_var.get())
            # stopbits = self.get_stopbits_constant(self.stopbits_var.get())
            
            # Create serial connection with non-blocking settings
            # self.serial_port = serial.Serial(
            #     port=port,
            #     baudrate=baud,
            #     bytesize=databits,
            #     parity=parity,
            #     stopbits=stopbits,
            #     timeout=0,  # Non-blocking read
            #     write_timeout=0  # Non-blocking write
            # )
            
            self.is_connected = True
            self.running = True
            
            # Update UI
            # self.connect_btn.config(text="Disconnect")
            # self.send_btn.config(state=tk.NORMAL)
            # self.port_combo.config(state=tk.DISABLED)
            # self.baud_combo.config(state=tk.DISABLED)
            # self.databits_combo.config(state=tk.DISABLED)
            # self.parity_combo.config(state=tk.DISABLED)
            # self.stopbits_combo.config(state=tk.DISABLED)
            # self.refresh_btn.config(state=tk.DISABLED)
            
            # Status update (old main connection - now unused)
            # self.add_system_message(f"Connected to {port}")
            
            # Start read thread
            # self.read_thread = threading.Thread(target=self.read_serial_thread, daemon=True)
            # self.read_thread.start()
            
        except serial.SerialException as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            self.add_system_message(f"Connection failed: {str(e)}", "error")
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")
            self.add_system_message(f"Error: {str(e)}", "error")
    
    def disconnect_serial(self):
        """Close serial connection"""
        self.running = False
        
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except:
                pass
        
        self.is_connected = False
        self.serial_port = None
        
        # Update UI
        # self.connect_btn.config(text="Connect")
        # self.send_btn.config(state=tk.DISABLED)
        # self.port_combo.config(state=tk.NORMAL)
        # self.baud_combo.config(state=tk.NORMAL)
        # self.databits_combo.config(state=tk.NORMAL)
        # self.parity_combo.config(state=tk.NORMAL)
        # self.stopbits_combo.config(state=tk.NORMAL)
        # self.refresh_btn.config(state=tk.NORMAL)
        
        # Status update (old main connection - now unused)
        self.add_system_message("Disconnected")
    
    def read_serial_thread(self):
        """Thread function for reading serial data continuously.
        
        This method runs in a separate thread to prevent blocking the GUI.
        It reads data from the serial port, processes it for both raw display
        and protocol handling, then queues it for GUI update.
        
        Key improvements in v2.1:
        - Always attempts to read data (no in_waiting check)
        - Reduced delay for better responsiveness (5ms)
        - Passes raw data to protocol handlers before processing
        """
        buffer = b""
        
        while self.running and self.serial_port:
            try:
                # Always try to read data - don't rely on in_waiting check
                # This prevents missing data due to timing issues that can occur
                # when checking in_waiting before reading (race condition)
                data = self.serial_port.read(4096)  # Read up to 4KB at once
                
                # If no data available, continue to next iteration
                if not data:
                    threading.Event().wait(0.005)  # Reduced delay for better responsiveness
                    continue
                    
                # First, let the device tab process the raw data for protocol packets
                # This allows protocol communication to work alongside normal serial communication
                # The device tab will extract and process any valid protocol packets
                if hasattr(self, 'device_tab') and data:
                    try:
                        self.device_tab.handle_raw_data(data)
                    except:
                        pass  # Don't let device tab errors break main serial reading
                
                # Also let the host tab process raw data for responses
                if hasattr(self, 'host_tab') and data:
                    try:
                        self.host_tab.handle_raw_data(data)
                    except:
                        pass  # Don't let host tab errors break main serial reading
                
                # AI Analysis will be triggered after complete RX messages below
                
                buffer += data
                
                # Process complete lines
                while b'\n' in buffer or b'\r' in buffer:
                    # Find line ending
                    idx_n = buffer.find(b'\n')
                    idx_r = buffer.find(b'\r')
                    
                    if idx_n == -1:
                        idx = idx_r
                    elif idx_r == -1:
                        idx = idx_n
                    else:
                        idx = min(idx_n, idx_r)
                    
                    line = buffer[:idx]
                    buffer = buffer[idx+1:]
                    
                    # Skip if it's just another line ending character
                    if len(buffer) > 0 and buffer[0:1] in (b'\n', b'\r'):
                        buffer = buffer[1:]
                    
                    if line:
                        self.data_queue.put(('rx', line))
                        
                        # AI Analysis Integration - Trigger after complete RX message
                        if self.ai_enabled.get() and self.ai_analyzer:
                            try:
                                # Add to AI analysis buffer
                                self.ai_data_buffer.append(line)
                                if len(self.ai_data_buffer) > 20:  # Keep last 20 messages
                                    self.ai_data_buffer.pop(0)
                                
                                # Trigger AI analysis (async) for complete message
                                threading.Thread(
                                    target=self.perform_ai_analysis,
                                    args=(line, self.ai_data_buffer.copy()),
                                    daemon=True
                                ).start()
                            except Exception as e:
                                self.ai_queue.put(('analysis_error', str(e), line))
                
                # If buffer gets too large without line endings, process it anyway
                if len(buffer) > 1024:
                    self.data_queue.put(('rx', buffer))
                    
                    # AI Analysis Integration - Trigger for large buffer chunks
                    if self.ai_enabled.get() and self.ai_analyzer:
                        try:
                            # Add to AI analysis buffer
                            self.ai_data_buffer.append(buffer)
                            if len(self.ai_data_buffer) > 20:  # Keep last 20 messages
                                self.ai_data_buffer.pop(0)
                            
                            # Trigger AI analysis (async) for complete message
                            threading.Thread(
                                target=self.perform_ai_analysis,
                                args=(buffer, self.ai_data_buffer.copy()),
                                daemon=True
                            ).start()
                        except Exception as e:
                            self.ai_queue.put(('analysis_error', str(e), buffer))
                    
                    buffer = b""
                        
            except serial.SerialException as e:
                self.data_queue.put(('error', f"Read error: {str(e)}"))
                self.running = False
                break
            except Exception as e:
                self.data_queue.put(('error', f"Unexpected error: {str(e)}"))
            
            # Small delay to prevent CPU spinning - reduced for better responsiveness
            threading.Event().wait(0.005)
        
        # Process any remaining data in buffer
        if buffer:
            self.data_queue.put(('rx', buffer))
            
            # AI Analysis Integration - Trigger for remaining buffer data
            if self.ai_enabled.get() and self.ai_analyzer:
                try:
                    # Add to AI analysis buffer
                    self.ai_data_buffer.append(buffer)
                    if len(self.ai_data_buffer) > 20:  # Keep last 20 messages
                        self.ai_data_buffer.pop(0)
                    
                    # Trigger AI analysis (async) for remaining data
                    threading.Thread(
                        target=self.perform_ai_analysis,
                        args=(buffer, self.ai_data_buffer.copy()),
                        daemon=True
                    ).start()
                except Exception as e:
                    self.ai_queue.put(('analysis_error', str(e), buffer))
    
    def update_gui(self):
        """Update GUI with data from queue.
        
        This method is called periodically (every 25ms) via Tkinter's after()
        mechanism. It processes all pending data from the queue and updates
        the display. This ensures thread-safe GUI updates.
        """
        # Process all pending data
        while not self.data_queue.empty():
            try:
                msg_type, data = self.data_queue.get_nowait()
                
                if msg_type == 'rx':
                    self.display_received_data(data)
                elif msg_type == 'error':
                    self.add_system_message(data, "error")
                    # Auto-disconnect on error
                    if self.is_connected:
                        self.disconnect_serial()
                        
            except queue.Empty:
                break
        
        # Process AI analysis results
        while not self.ai_queue.empty():
            try:
                ai_msg_type, ai_data, original_data = self.ai_queue.get_nowait()
                
                if ai_msg_type == 'analysis_result':
                    self.display_ai_analysis(ai_data, original_data)
                elif ai_msg_type == 'analysis_error':
                    self.add_system_message(f"🤖 AI Error: {ai_data}", "error")
                        
            except queue.Empty:
                break
        
        # Schedule next update - reduced interval for better responsiveness
        self.after_id = self.root.after(25, self.update_gui)
    
    def display_received_data(self, data: bytes):
        """Display received data in the text widget"""
        try:
            # Decode data
            text = data.decode('utf-8', errors='replace')
            
            # Display in main window
            self.rx_display.config(state=tk.NORMAL)
            
            # Add timestamp if logging
            if self.logging_enabled.get():
                timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                self.rx_display.insert(tk.END, f"[{timestamp}] RX: ", "system")
            else:
                self.rx_display.insert(tk.END, "RX: ", "system")
            
            self.rx_display.insert(tk.END, text + "\n", "rx")
            
            # Auto-scroll if enabled
            if self.auto_scroll_enabled.get():
                self.rx_display.see(tk.END)
            
            self.rx_display.config(state=tk.DISABLED)
            
            # Update hex display (always update for format switching)
            self.update_hex_display(data, "RX")
            
            # Log to file if enabled
            if self.logging_enabled.get() and self.log_file:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                self.log_file.write(f"{timestamp},RX,{text}\n")
                self.log_file.flush()
                
        except Exception as e:
            self.add_system_message(f"Display error: {str(e)}", "error")
    
    def update_hex_display(self, data: bytes, direction: str):
        """Update hex display tab"""
        self.hex_display.config(state=tk.NORMAL)
        
        # Add timestamp
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.hex_display.insert(tk.END, f"[{timestamp}] {direction}:\n", "system")
        
        # Format hex output (16 bytes per line)
        hex_str = ""
        ascii_str = ""
        
        for i, byte in enumerate(data):
            hex_str += f"{byte:02X} "
            ascii_str += chr(byte) if 32 <= byte < 127 else "."
            
            if (i + 1) % 16 == 0:
                self.hex_display.insert(tk.END, f"{hex_str:<48} | {ascii_str}\n")
                hex_str = ""
                ascii_str = ""
        
        # Handle remaining bytes
        if hex_str:
            self.hex_display.insert(tk.END, f"{hex_str:<48} | {ascii_str}\n")
        
        self.hex_display.insert(tk.END, "\n")
        
        if self.auto_scroll_enabled.get():
            self.hex_display.see(tk.END)
        
        self.hex_display.config(state=tk.DISABLED)
    
    def on_data_tab_data_received(self, msg_type: str, data, timestamp: str):
        """Callback for Data Display tab serial connection."""
        if msg_type == 'rx':
            # Display received data
            self.display_received_data(data)
            
            # Perform AI analysis if enabled
            if hasattr(self, 'ai_analyzer') and self.ai_analyzer:
                # Add to analysis history
                if not hasattr(self, 'ai_analysis_history'):
                    self.ai_analysis_history = []
                self.ai_analysis_history.append(data)
                
                # Keep only last 100 messages
                if len(self.ai_analysis_history) > 100:
                    self.ai_analysis_history.pop(0)
                
                # Perform analysis
                self.perform_ai_analysis(data, self.ai_analysis_history[-10:])
                
        elif msg_type == 'tx':
            # Display sent data
            self.rx_display.config(state=tk.NORMAL)
            if self.logging_enabled.get() and timestamp:
                self.rx_display.insert(tk.END, f"[{timestamp}] TX: ", "system")
            else:
                self.rx_display.insert(tk.END, "TX: ", "system")
            
            try:
                text = data.decode('utf-8', errors='replace')
                self.rx_display.insert(tk.END, text + "\n", "tx")
            except:
                # Show as hex if decode fails
                hex_text = ' '.join(f'{b:02X}' for b in data)
                self.rx_display.insert(tk.END, f"[HEX] {hex_text}\n", "tx")
            
            if self.auto_scroll_enabled.get():
                self.rx_display.see(tk.END)
            self.rx_display.config(state=tk.DISABLED)
            
            # Update hex display
            self.update_hex_display(data, "TX")
            
        elif msg_type == 'error':
            # Display error message
            self.add_system_message(data, "error")
    
    def send_command(self):
        """Send command through Data Display tab's serial port"""
        if not self.data_tab_serial.is_connected:
            return
        
        command = self.command_entry.get()
        if not command:
            return
        
        # Add to history
        if command not in self.command_history:
            self.command_history.append(command)
        self.history_index = -1
        
        # Process line ending
        line_ending = self.line_ending_var.get()
        if line_ending == "\\r":
            command += "\r"
        elif line_ending == "\\n":
            command += "\n"
        elif line_ending == "\\r\\n":
            command += "\r\n"
        
        # Send command through Data Display tab's serial connection
        success = self.data_tab_serial.send_data(command.encode('utf-8'))
        if success:
            # Log to file if enabled (TX display is handled by callback)
            if self.logging_enabled.get() and self.log_file:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                display_cmd = command.rstrip('\r\n')
                self.log_file.write(f"{timestamp},TX,{display_cmd}\n")
                self.log_file.flush()
            
            # Clear entry
            self.command_entry.delete(0, tk.END)
        else:
            self.add_system_message("Failed to send command", "error")
    
    def send_macro(self, macro_command: str):
        """Send a predefined macro command"""
        if self.data_tab_serial.is_connected:
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, macro_command)
            self.send_command()
    
    def history_up(self, event):
        """Navigate command history up"""
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, self.command_history[-(self.history_index + 1)])
    
    def history_down(self, event):
        """Navigate command history down"""
        if self.history_index > 0:
            self.history_index -= 1
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, self.command_history[-(self.history_index + 1)])
        elif self.history_index == 0:
            self.history_index = -1
            self.command_entry.delete(0, tk.END)
    
    def clear_display(self):
        """Clear ASCII data display area"""
        self.rx_display.config(state=tk.NORMAL)
        self.rx_display.delete(1.0, tk.END)
        self.rx_display.config(state=tk.DISABLED)
        
        self.add_system_message("ASCII display cleared")
    
    def clear_hex_display(self):
        """Clear hex display area"""
        self.hex_display.config(state=tk.NORMAL)
        self.hex_display.delete(1.0, tk.END)
        self.hex_display.config(state=tk.DISABLED)
        
        self.add_system_message("Hexadecimal display cleared")
    
    def clear_current_display(self):
        """Clear currently active display"""
        if self.hex_format_var.get():
            self.clear_hex_display()
        else:
            self.clear_display()
    
    def toggle_display_format(self):
        """Toggle between ASCII and hexadecimal display formats"""
        is_hex = self.hex_format_var.get()
        
        if is_hex:
            # Switch to hex display
            self.rx_display.pack_forget()
            self.hex_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            self.add_system_message("Switched to hexadecimal display format")
        else:
            # Switch to ASCII display
            self.hex_display.pack_forget()
            self.rx_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            self.add_system_message("Switched to ASCII display format")
    
    def toggle_logging(self):
        """Toggle file logging"""
        if self.logging_enabled.get():
            # Start logging
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"serial_log_{timestamp}.csv"
            try:
                self.log_file = open(filename, 'w', encoding='utf-8')
                self.log_file.write("Timestamp,Direction,Data\n")
                self.add_system_message(f"Logging to {filename}")
            except Exception as e:
                self.logging_enabled.set(False)
                messagebox.showerror("Error", f"Could not create log file: {str(e)}")
        else:
            # Stop logging
            if self.log_file:
                self.log_file.close()
                self.log_file = None
                self.add_system_message("Logging stopped")
    
    def add_system_message(self, message: str, tag: str = "system"):
        """Add a system message to both displays"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Add to ASCII display
        self.rx_display.config(state=tk.NORMAL)
        self.rx_display.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        if self.auto_scroll_enabled.get():
            self.rx_display.see(tk.END)
        self.rx_display.config(state=tk.DISABLED)
        
        # Add to hex display 
        self.hex_display.config(state=tk.NORMAL)
        self.hex_display.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        if self.auto_scroll_enabled.get():
            self.hex_display.see(tk.END)
        self.hex_display.config(state=tk.DISABLED)
    
    # AI Analysis Methods
    def update_ai_status(self):
        """Update AI status display"""
        if self.ai_config.has_api_key():
            self.ai_status.config(text="API Key: Configured", fg='#006400')
            
            # Try to initialize analyzer if not already done
            if self.ai_analyzer is None:
                api_key = self.ai_config.load_api_key()
                if api_key:
                    self.ai_analyzer = AIAnalyzer(api_key)
                    if self.ai_analyzer.is_enabled:
                        self.ai_status.config(text="API Key: Ready", fg='#006400')
                    else:
                        self.ai_status.config(text="API Key: Invalid", fg='#CC0000')
        else:
            self.ai_status.config(text="API Key: Not Set", fg='#CC0000')
        
        # Update button state
        if self.ai_analyzer and self.ai_analyzer.is_enabled:
            self.ai_toggle_btn.config(state=tk.NORMAL)
        else:
            self.ai_toggle_btn.config(state=tk.DISABLED)
            self.ai_enabled.set(False)
            
        # Update toggle button text
        if self.ai_enabled.get():
            self.ai_toggle_btn.config(text="Disable AI Analysis")
        else:
            self.ai_toggle_btn.config(text="Enable AI Analysis")
    
    def toggle_ai_analysis(self):
        """Toggle AI analysis on/off"""
        if not self.ai_analyzer or not self.ai_analyzer.is_enabled:
            messagebox.showwarning("AI Analysis", "Please configure a valid API key first.")
            self.open_ai_settings()
            return
        
        current_state = self.ai_enabled.get()
        self.ai_enabled.set(not current_state)
        
        if self.ai_enabled.get():
            self.ai_toggle_btn.config(text="Disable AI Analysis")
            self.add_system_message("🤖 AI Analysis enabled", "ai_insight")
        else:
            self.ai_toggle_btn.config(text="Enable AI Analysis")
            self.add_system_message("🤖 AI Analysis disabled", "system")
        
        # Update statistics display
        self.update_ai_stats_display()
    
    def open_ai_settings(self):
        """Open AI settings dialog"""
        AISettingsDialog(self.root, self.ai_config, self.update_ai_status)
    
    def perform_ai_analysis(self, data: bytes, history: List[bytes]):
        """Perform AI analysis in background thread"""
        if not self.ai_analyzer or not self.ai_enabled.get():
            return
            
        try:
            # Analyze data using OpenAI API
            result = self.ai_analyzer.analyze_data(data, history)
            
            if result:
                # Queue result for GUI update
                self.ai_queue.put(('analysis_result', result, data))
            
        except Exception as e:
            self.ai_queue.put(('analysis_error', str(e), data))
    
    def display_ai_analysis(self, analysis, original_data: bytes):
        """Display AI analysis results with visual highlighting"""
        try:
            # Add AI insight message
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            confidence_str = f"({analysis.confidence:.1%})" if hasattr(analysis, 'confidence') else ""
            insight_msg = f"[{timestamp}] 🤖 AI {confidence_str}: {analysis.description}"
            
            # Determine tag based on analysis type and confidence
            if hasattr(analysis, 'analysis_type'):
                if analysis.analysis_type == "error":
                    tag = "ai_error"
                elif analysis.analysis_type == "protocol":
                    tag = "ai_protocol"
                elif analysis.analysis_type == "pattern":
                    tag = "ai_pattern"
                else:
                    tag = "ai_insight"
            else:
                tag = "ai_insight"
            
            # Add to displays
            for display in [self.rx_display, self.hex_display]:
                display.config(state=tk.NORMAL)
                display.insert(tk.END, f"{insight_msg}\n", tag)
                
                # Add suggestions if available
                if hasattr(analysis, 'suggestions') and analysis.suggestions:
                    for suggestion in analysis.suggestions[:3]:  # Limit to 3 suggestions
                        suggestion_msg = f"    💡 {suggestion}\n"
                        display.insert(tk.END, suggestion_msg, "ai_insight")
                
                if self.auto_scroll_enabled.get():
                    display.see(tk.END)
                
                display.config(state=tk.DISABLED)
            
            # Update statistics
            self.update_ai_stats_display()
            
        except Exception as e:
            self.add_system_message(f"AI Display Error: {e}", "error")
    
    def update_ai_stats_display(self):
        """Update AI statistics display"""
        if self.ai_analyzer:
            stats = self.ai_analyzer.get_statistics()
            if stats and stats.get("total_analyses", 0) > 0:
                total = stats["total_analyses"]
                avg_conf = stats.get("average_confidence", 0)
                self.ai_stats_label.config(text=f"Analyses: {total} | Avg Confidence: {avg_conf:.1%}")
            else:
                self.ai_stats_label.config(text="")
        else:
            self.ai_stats_label.config(text="")
    
    def on_closing(self):
        """Handle window close event"""
        # Stop operations
        self.running = False
        
        # Cancel after callback
        if self.after_id:
            self.root.after_cancel(self.after_id)
        
        # Disconnect if connected
        if self.is_connected:
            self.disconnect_serial()
        
        # Close log file
        if self.log_file:
            self.log_file.close()
        
        # Destroy window
        self.root.destroy()


def main():
    """Main entry point"""
    root = tk.Tk()
    app = SerialGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()