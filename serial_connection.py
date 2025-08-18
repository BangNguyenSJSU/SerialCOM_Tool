#!/usr/bin/env python3
"""
Serial Connection Management - Reusable class for tab-independent serial connections
"""

import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import queue
import datetime
import time
import glob
import platform
from typing import Optional, List, Callable


class SerialConnection:
    """Manages an independent serial connection for a tab.
    
    Provides connection management, port discovery, threading for non-blocking I/O,
    and a data queue for received data. Each tab can have its own instance.
    """
    
    def __init__(self, parent_frame: tk.Widget, on_data_received: Optional[Callable] = None):
        """Initialize serial connection manager.
        
        Args:
            parent_frame: Parent widget for the connection UI
            on_data_received: Optional callback when data is received
        """
        self.parent_frame = parent_frame
        self.on_data_received = on_data_received
        
        # Serial connection state
        self.serial_port: Optional[serial.Serial] = None
        self.is_connected = False
        self.running = False
        
        # Threading and data
        self.read_thread: Optional[threading.Thread] = None
        self.data_queue = queue.Queue()
        
        # UI variables
        self.port_var = tk.StringVar()
        self.baud_var = tk.IntVar(value=115200)
        self.data_bits_var = tk.IntVar(value=8)
        self.parity_var = tk.StringVar(value="None")
        self.stop_bits_var = tk.IntVar(value=1)
        
        # Create UI
        self.create_connection_ui()
        
        # Start periodic check for received data
        self.check_data_queue()
    
    def create_connection_ui(self):
        """Create the connection control UI."""
        # Connection frame
        conn_frame = tk.LabelFrame(self.parent_frame, text="Serial Connection", 
                                  font=("Arial", 10, "bold"), relief=tk.GROOVE, bd=2)
        conn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Port selection row
        port_row = tk.Frame(conn_frame)
        port_row.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(port_row, text="Port:").pack(side=tk.LEFT)
        self.port_combo = ttk.Combobox(port_row, textvariable=self.port_var, width=20)
        self.port_combo.pack(side=tk.LEFT, padx=(5, 10))
        
        tk.Button(port_row, text="Refresh", command=self.refresh_ports).pack(side=tk.LEFT)
        
        # Connection buttons
        btn_frame = tk.Frame(port_row)
        btn_frame.pack(side=tk.RIGHT)
        
        self.connect_btn = tk.Button(btn_frame, text="Connect", 
                                   command=self.connect_serial, bg="#4CAF50", fg="white")
        self.connect_btn.pack(side=tk.LEFT, padx=2)
        
        self.disconnect_btn = tk.Button(btn_frame, text="Disconnect", 
                                      command=self.disconnect_serial, bg="#f44336", fg="white")
        self.disconnect_btn.pack(side=tk.LEFT, padx=2)
        
        # Settings row
        settings_row = tk.Frame(conn_frame)
        settings_row.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(settings_row, text="Baud:").pack(side=tk.LEFT)
        baud_combo = ttk.Combobox(settings_row, textvariable=self.baud_var, width=10,
                                 values=[9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600])
        baud_combo.pack(side=tk.LEFT, padx=(5, 10))
        
        tk.Label(settings_row, text="Data:").pack(side=tk.LEFT)
        data_combo = ttk.Combobox(settings_row, textvariable=self.data_bits_var, width=5,
                                 values=[5, 6, 7, 8])
        data_combo.pack(side=tk.LEFT, padx=(5, 10))
        
        tk.Label(settings_row, text="Parity:").pack(side=tk.LEFT)
        parity_combo = ttk.Combobox(settings_row, textvariable=self.parity_var, width=8,
                                   values=["None", "Even", "Odd", "Mark", "Space"])
        parity_combo.pack(side=tk.LEFT, padx=(5, 10))
        
        tk.Label(settings_row, text="Stop:").pack(side=tk.LEFT)
        stop_combo = ttk.Combobox(settings_row, textvariable=self.stop_bits_var, width=5,
                                 values=[1, 1.5, 2])
        stop_combo.pack(side=tk.LEFT, padx=(5, 10))
        
        # Status row
        status_row = tk.Frame(conn_frame)
        status_row.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = tk.Label(status_row, text="●", font=("Arial", 12), fg="red")
        self.status_label.pack(side=tk.LEFT)
        
        self.status_text = tk.Label(status_row, text="Disconnected", font=("Arial", 10))
        self.status_text.pack(side=tk.LEFT, padx=5)
        
        # Initial port refresh
        self.refresh_ports()
        self.update_ui_state()
    
    def refresh_ports(self):
        """Refresh available serial ports."""
        ports = []
        
        # Get standard ports
        for port_info in serial.tools.list_ports.comports():
            ports.append(f"{port_info.device} ({port_info.description})")
        
        # Add virtual TTY ports (macOS/Linux)
        if platform.system() in ['Darwin', 'Linux']:
            virtual_ports = glob.glob('/dev/ttys[0-9]*')
            for port_path in sorted(virtual_ports):
                try:
                    with serial.Serial(port_path, timeout=0, write_timeout=0) as test_ser:
                        ports.append(f"{port_path} (Virtual TTY)")
                except:
                    pass
        
        # Update combobox
        self.port_combo['values'] = ports
        if ports and not self.port_var.get():
            self.port_combo.set(ports[0])
    
    def connect_serial(self):
        """Connect to the selected serial port."""
        if self.is_connected:
            return
            
        port_text = self.port_var.get()
        if not port_text:
            messagebox.showerror("Error", "Please select a serial port")
            return
        
        # Extract port name from the display text
        port_name = port_text.split(' ')[0]
        
        try:
            # Convert parity setting
            parity_map = {
                "None": serial.PARITY_NONE,
                "Even": serial.PARITY_EVEN,
                "Odd": serial.PARITY_ODD,
                "Mark": serial.PARITY_MARK,
                "Space": serial.PARITY_SPACE
            }
            
            # Create serial connection
            self.serial_port = serial.Serial(
                port=port_name,
                baudrate=self.baud_var.get(),
                bytesize=self.data_bits_var.get(),
                parity=parity_map[self.parity_var.get()],
                stopbits=self.stop_bits_var.get(),
                timeout=0,  # Non-blocking reads
                write_timeout=1
            )
            
            self.is_connected = True
            self.running = True
            
            # Start read thread
            self.read_thread = threading.Thread(target=self._read_serial_thread, daemon=True)
            self.read_thread.start()
            
            self.update_ui_state()
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to {port_name}:\n{str(e)}")
    
    def disconnect_serial(self):
        """Disconnect from serial port."""
        if not self.is_connected:
            return
            
        self.running = False
        self.is_connected = False
        
        # Close serial port
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except:
                pass
        
        self.serial_port = None
        self.update_ui_state()
    
    def _read_serial_thread(self):
        """Thread function for reading serial data."""
        while self.running and self.serial_port:
            try:
                # Read data (non-blocking)
                data = self.serial_port.read(4096)  # Read up to 4KB
                if not data:
                    time.sleep(0.005)  # 5ms delay
                    continue
                
                # Add timestamp and put in queue
                timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                self.data_queue.put(('rx', data, timestamp))
                
            except Exception as e:
                # Connection error - disconnect
                self.data_queue.put(('error', f"Read error: {str(e)}", None))
                self.running = False
                break
    
    def check_data_queue(self):
        """Periodically check for received data and call callback."""
        try:
            while True:
                msg_type, data, timestamp = self.data_queue.get_nowait()
                
                if msg_type == 'error':
                    # Handle read errors
                    self.is_connected = False
                    self.update_ui_state()
                    if self.on_data_received:
                        self.on_data_received('error', data, timestamp)
                elif self.on_data_received:
                    self.on_data_received(msg_type, data, timestamp)
                    
        except queue.Empty:
            pass
        
        # Schedule next check
        self.parent_frame.after(25, self.check_data_queue)
    
    def send_data(self, data: bytes) -> bool:
        """Send data through the serial port.
        
        Args:
            data: Bytes to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_connected or not self.serial_port:
            return False
            
        try:
            self.serial_port.write(data)
            
            # Add to queue for logging
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.data_queue.put(('tx', data, timestamp))
            return True
            
        except Exception as e:
            if self.on_data_received:
                self.on_data_received('error', f"Send error: {str(e)}", None)
            return False
    
    def update_ui_state(self):
        """Update UI elements based on connection state."""
        if self.is_connected:
            self.status_label.config(fg="green")
            self.status_text.config(text="Connected")
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            self.port_combo.config(state=tk.DISABLED)
        else:
            self.status_label.config(fg="red")
            self.status_text.config(text="Disconnected")
            self.connect_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.DISABLED)
            self.port_combo.config(state=tk.NORMAL)
    
    def get_port_info(self) -> str:
        """Get formatted port information string."""
        if self.is_connected and self.serial_port:
            return (f"{self.serial_port.port} - {self.baud_var.get()},{self.data_bits_var.get()},"
                   f"{self.parity_var.get()[0]},{self.stop_bits_var.get()}")
        return ""
    
    def cleanup(self):
        """Clean up resources when tab is closed."""
        self.disconnect_serial()