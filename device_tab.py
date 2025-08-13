#!/usr/bin/env python3
"""
Device Tab - Simulates a slave device with register map
Restructured with precise grid alignment and symmetry
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import queue
import datetime
import csv
from typing import Optional, List, Dict, Any
from protocol import (
    Packet, PacketBuilder, PacketParser,
    FunctionCode, ErrorCode, RegisterMap
)
from ui_styles import FONTS, SPACING, COLORS, configure_text_widget


class DeviceTab:
    """Device (Slave) mode implementation for protocol testing.
    
    This tab simulates an embedded device with a register map that responds
    to protocol requests from a host. It processes incoming packets, manages
    a configurable register map, and sends appropriate responses.
    """
    
    # Style constants for consistent grid layout
    PAD = 8              # Standard padding between elements
    OUTER_MARGIN = 12    # Outer container margin
    INTER_PANEL_GAP = 8  # Gap between panels
    INNER_PADDING = 8    # Inner panel padding
    HEADER_H = 28        # Standard header height
    BTN_W = 88           # Standard button width
    BTN_H = 28           # Standard button height
    HEX_ENTRY_W = 72     # Hex entry width
    SEARCH_ENTRY_W = 180 # Search entry width
    LABEL_COL_W = 80     # Label column width
    
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
        self.error_radio_buttons = []  # Store radio button references
        
        # Statistics
        self.request_count = 0
        self.response_count = 0
        self.error_count = 0
        
        # Log controls
        self.incoming_auto_scroll = tk.BooleanVar(value=True)
        self.outgoing_auto_scroll = tk.BooleanVar(value=True)
        self.incoming_search_var = tk.StringVar()
        self.outgoing_search_var = tk.StringVar()
        self.incoming_search_pos = "1.0"
        self.outgoing_search_pos = "1.0"
        
        # Build UI with new grid layout
        self.create_widgets()
        
        # Start processing loop
        self.process_requests()
    
    def create_widgets(self):
        """Create Device tab UI elements with precise grid alignment"""
        # Main container with outer margin
        main_container = ttk.Frame(self.frame, padding=str(self.OUTER_MARGIN))
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create vertical PanedWindow: Top area vs Register Map
        vertical_paned = ttk.PanedWindow(main_container, orient=tk.VERTICAL)
        vertical_paned.pack(fill=tk.BOTH, expand=True)
        
        # Top area frame
        top_area = ttk.Frame(vertical_paned)
        vertical_paned.add(top_area, weight=2)
        
        # Register map frame  
        register_area = ttk.Frame(vertical_paned)
        vertical_paned.add(register_area, weight=1)
        
        # Create horizontal PanedWindow in top area: Left stack vs Logs
        horizontal_paned = ttk.PanedWindow(top_area, orient=tk.HORIZONTAL)
        horizontal_paned.pack(fill=tk.BOTH, expand=True)
        
        # Left stack frame (give more weight for config panels)
        left_stack = ttk.Frame(horizontal_paned)
        horizontal_paned.add(left_stack, weight=2)
        
        # Right logs frame (reduce weight to make narrower)
        right_logs = ttk.Frame(horizontal_paned)
        horizontal_paned.add(right_logs, weight=3)
        
        # Build components
        self.create_left_stack(left_stack)
        self.create_right_logs(right_logs)
        self.create_register_map(register_area)
        
        # Configure resizing
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(0, weight=1)
        
        # Initialize views
        self.refresh_register_view()
        self.update_log_counters()
        self.toggle_error_radios()  # Initialize radio button states
    
    def create_left_stack(self, parent):
        """Create left stack with Device Config and Error Simulation"""
        # Device Configuration Panel
        config_frame = ttk.LabelFrame(parent, text="Device Configuration", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, self.INTER_PANEL_GAP))
        
        # Use grid for better alignment with improved spacing
        input_frame = ttk.Frame(config_frame)
        input_frame.pack(fill=tk.X, pady=(4, 8))
        
        # Configure grid columns for proper alignment
        input_frame.grid_columnconfigure(1, weight=1)  # Address input column
        input_frame.grid_columnconfigure(3, weight=1)  # Size input column
        
        # Address row with better spacing
        ttk.Label(input_frame, text="Address:").grid(row=0, column=0, sticky=tk.E, padx=(0, self.PAD), pady=2)
        self.addr_var = tk.IntVar(value=self.device_address)
        addr_spin = ttk.Spinbox(input_frame, from_=1, to=247, textvariable=self.addr_var, 
                               width=12, command=self.update_device_address)
        addr_spin.grid(row=0, column=1, sticky=tk.W, padx=(0, self.PAD*3), pady=2)
        
        # Size on same row with better spacing
        ttk.Label(input_frame, text="Size:").grid(row=0, column=2, sticky=tk.E, padx=(0, self.PAD), pady=2)
        self.map_size_var = tk.IntVar(value=256)
        size_spin = ttk.Spinbox(input_frame, from_=16, to=1024, textvariable=self.map_size_var, 
                               width=12, increment=16)
        size_spin.grid(row=0, column=3, sticky=tk.W, pady=2)
        
        # Button row - centered buttons with proper widths
        btn_row = ttk.Frame(config_frame)
        btn_row.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 0))
        
        # Create button container for centering
        btn_container = ttk.Frame(btn_row)
        btn_container.pack(expand=True)
        
        # All buttons same width for symmetry
        button_width = 10
        
        resize_btn = ttk.Button(btn_container, text="Resize", width=button_width, 
                               command=self.resize_register_map)
        resize_btn.pack(side=tk.LEFT, padx=3)
        
        clear_btn = ttk.Button(btn_container, text="Clear", width=button_width, 
                              command=self.clear_registers)
        clear_btn.pack(side=tk.LEFT, padx=3)
        
        test_btn = ttk.Button(btn_container, text="Test Pattern", width=button_width+4, 
                             command=self.load_test_pattern)
        test_btn.pack(side=tk.LEFT, padx=3)
        
        # Error Simulation Panel with 2-column layout
        error_frame = ttk.LabelFrame(parent, text="Error Simulation", padding="8")
        error_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
        
        # Enable errors checkbox with command to toggle radio buttons
        self.error_checkbox = ttk.Checkbutton(error_frame, text="Enable Errors", 
                                             variable=self.simulate_errors, 
                                             command=self.toggle_error_radios)
        self.error_checkbox.pack(anchor=tk.W, pady=(0, 4))
        
        # Radio button container using grid for 3-column layout
        radio_container = ttk.Frame(error_frame)
        radio_container.pack(fill=tk.BOTH, expand=True, padx=(20, 0))
        
        # Configure grid columns for 3-column layout
        radio_container.grid_columnconfigure(0, weight=1)
        radio_container.grid_columnconfigure(1, weight=1)
        radio_container.grid_columnconfigure(2, weight=1)
        
        # Radio buttons with tooltips in 3 columns
        # Arrange in 2 rows: Row 1 has 3 items, Row 2 has 2 items
        error_types = [
            ("No Error", "none", "No error simulation", 0, 0),
            ("Invalid Func", "invalid_function", "Return error code 0x01 - Invalid function", 0, 1),
            ("Invalid Addr", "invalid_address", "Return error code 0x02 - Invalid address", 0, 2),
            ("Invalid Value", "invalid_value", "Return error code 0x03 - Invalid value", 1, 0),
            ("Internal Error", "internal_error", "Return error code 0xFF - Internal error", 1, 1)
        ]
        
        self.error_radio_buttons = []
        for text, value, tooltip, row, col in error_types:
            btn = ttk.Radiobutton(radio_container, text=text, variable=self.error_type, 
                                value=value, state="disabled")
            btn.grid(row=row, column=col, sticky=tk.W, padx=(0, 8), pady=2)
            self.create_tooltip(btn, tooltip)
            self.error_radio_buttons.append(btn)
        
        # Set default to "No Error" when disabled
        self.error_type.set("none")
    
    def create_right_logs(self, parent):
        """Create mirrored log panels for incoming and outgoing"""
        # Create horizontal split for the two log panels
        logs_paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        logs_paned.pack(fill=tk.BOTH, expand=True)
        
        # Incoming Requests Panel
        self.incoming_frame = ttk.LabelFrame(logs_paned, text="Incoming Requests (0)", 
                                           padding=str(self.INNER_PADDING))
        logs_paned.add(self.incoming_frame, weight=1)
        
        # Statistics row for incoming
        incoming_stats = ttk.Frame(self.incoming_frame)
        incoming_stats.pack(fill=tk.X, pady=(0, self.PAD))
        
        ttk.Label(incoming_stats, text="Total:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.incoming_total_label = ttk.Label(incoming_stats, text="0", font=("Cascadia Mono", 10, "bold"))
        self.incoming_total_label.pack(side=tk.LEFT, padx=(4, 12))
        
        ttk.Label(incoming_stats, text="Errors:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.incoming_error_label = ttk.Label(incoming_stats, text="0", font=("Cascadia Mono", 10), foreground="red")
        self.incoming_error_label.pack(side=tk.LEFT, padx=(4, 12))
        
        ttk.Button(incoming_stats, text="Reset", width=6, command=self.reset_incoming_stats).pack(side=tk.RIGHT)
        
        # Mirrored toolbar for incoming
        incoming_toolbar = ttk.Frame(self.incoming_frame)
        incoming_toolbar.pack(fill=tk.X, pady=(0, self.PAD))
        
        ttk.Checkbutton(incoming_toolbar, text="Auto-scroll", 
                       variable=self.incoming_auto_scroll).pack(side=tk.LEFT)
        
        ttk.Label(incoming_toolbar, text="Find:").pack(side=tk.LEFT, padx=(self.PAD*2, self.PAD//2))
        incoming_search = ttk.Entry(incoming_toolbar, textvariable=self.incoming_search_var, 
                                   width=22)
        incoming_search.pack(side=tk.LEFT, padx=(0, self.PAD//2))
        ttk.Button(incoming_toolbar, text="Next", width=6,
                  command=self.find_next_incoming).pack(side=tk.LEFT, padx=(0, self.PAD))
        
        # Spacer
        ttk.Frame(incoming_toolbar).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(incoming_toolbar, text="Clear", width=6,
                  command=lambda: self.clear_log(self.incoming_request_log)).pack(side=tk.RIGHT)
        
        # Log text area with reduced width
        self.incoming_request_log = scrolledtext.ScrolledText(
            self.incoming_frame, wrap=tk.NONE, height=12, width=35,
            font=("Cascadia Mono", 9), padx=8, pady=8)
        self.incoming_request_log.pack(fill=tk.BOTH, expand=True)
        
        # Outgoing Responses Panel
        self.outgoing_frame = ttk.LabelFrame(logs_paned, text="Outgoing Responses (0)", 
                                           padding=str(self.INNER_PADDING))
        logs_paned.add(self.outgoing_frame, weight=1)
        
        # Statistics row for outgoing  
        outgoing_stats = ttk.Frame(self.outgoing_frame)
        outgoing_stats.pack(fill=tk.X, pady=(0, self.PAD))
        
        ttk.Label(outgoing_stats, text="Total:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.outgoing_total_label = ttk.Label(outgoing_stats, text="0", font=("Cascadia Mono", 10, "bold"))
        self.outgoing_total_label.pack(side=tk.LEFT, padx=(4, 12))
        
        ttk.Label(outgoing_stats, text="Errors:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.outgoing_error_label = ttk.Label(outgoing_stats, text="0", font=("Cascadia Mono", 10), foreground="red")
        self.outgoing_error_label.pack(side=tk.LEFT, padx=(4, 12))
        
        ttk.Button(outgoing_stats, text="Reset", width=6, command=self.reset_outgoing_stats).pack(side=tk.RIGHT)
        
        # Mirrored toolbar for outgoing
        outgoing_toolbar = ttk.Frame(self.outgoing_frame)
        outgoing_toolbar.pack(fill=tk.X, pady=(0, self.PAD))
        
        ttk.Checkbutton(outgoing_toolbar, text="Auto-scroll", 
                       variable=self.outgoing_auto_scroll).pack(side=tk.LEFT)
        
        ttk.Label(outgoing_toolbar, text="Find:").pack(side=tk.LEFT, padx=(self.PAD*2, self.PAD//2))
        outgoing_search = ttk.Entry(outgoing_toolbar, textvariable=self.outgoing_search_var, 
                                   width=22)
        outgoing_search.pack(side=tk.LEFT, padx=(0, self.PAD//2))
        ttk.Button(outgoing_toolbar, text="Next", width=6,
                  command=self.find_next_outgoing).pack(side=tk.LEFT, padx=(0, self.PAD))
        
        # Spacer
        ttk.Frame(outgoing_toolbar).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(outgoing_toolbar, text="Clear", width=6,
                  command=lambda: self.clear_log(self.outgoing_response_log)).pack(side=tk.RIGHT)
        
        # Log text area with reduced width
        self.outgoing_response_log = scrolledtext.ScrolledText(
            self.outgoing_frame, wrap=tk.NONE, height=12, width=35,
            font=("Cascadia Mono", 9), padx=8, pady=8)
        self.outgoing_response_log.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags
        for log in [self.incoming_request_log, self.outgoing_response_log]:
            log.tag_config("header", foreground="blue", font=("Cascadia Mono", 9, "bold"))
            log.tag_config("data", foreground="black")
            log.tag_config("error", foreground="red")
    
    def create_register_map(self, parent):
        """Create register map section with aligned controls"""
        reg_frame = ttk.LabelFrame(parent, text="Register Map", padding=str(self.INNER_PADDING))
        reg_frame.pack(fill=tk.BOTH, expand=True)
        
        # Control row with aligned clusters
        controls = ttk.Frame(reg_frame)
        controls.pack(fill=tk.X, pady=(0, self.PAD))
        
        # Cluster 1: Address/Value/Set
        cluster1 = ttk.Frame(controls)
        cluster1.pack(side=tk.LEFT)
        
        # Address controls
        addr_row = ttk.Frame(cluster1)
        addr_row.pack(fill=tk.X)
        ttk.Label(addr_row, text="Address:", width=10, anchor=tk.E).pack(side=tk.LEFT)
        self.reg_edit_addr = tk.StringVar(value="0000")
        ttk.Entry(addr_row, textvariable=self.reg_edit_addr, width=10).pack(side=tk.LEFT, padx=self.PAD)
        
        ttk.Label(addr_row, text="Value:", width=8, anchor=tk.E).pack(side=tk.LEFT, padx=(self.PAD, 0))
        self.reg_edit_value = tk.StringVar(value="0000")
        ttk.Entry(addr_row, textvariable=self.reg_edit_value, width=10).pack(side=tk.LEFT, padx=self.PAD)
        
        ttk.Button(addr_row, text="Set", width=6, command=self.set_register).pack(side=tk.LEFT, padx=self.PAD)
        ttk.Button(addr_row, text="Refresh", width=8, command=self.refresh_register_view).pack(side=tk.LEFT, padx=self.PAD)
        
        # Spacer
        ttk.Frame(controls, width=self.PAD*3).pack(side=tk.LEFT)
        
        # Cluster 2: Go to Address
        cluster2 = ttk.Frame(controls)
        cluster2.pack(side=tk.LEFT)
        
        ttk.Label(cluster2, text="Go to:", width=8, anchor=tk.E).pack(side=tk.LEFT)
        self.goto_addr_var = tk.StringVar(value="0000")
        ttk.Entry(cluster2, textvariable=self.goto_addr_var, width=10).pack(side=tk.LEFT, padx=self.PAD)
        ttk.Button(cluster2, text="Go", width=6, command=self.goto_address).pack(side=tk.LEFT, padx=self.PAD)
        
        # Spacer
        ttk.Frame(controls, width=self.PAD*3).pack(side=tk.LEFT)
        
        # Cluster 3: Set Multiple
        cluster3 = ttk.Frame(controls)
        cluster3.pack(side=tk.LEFT)
        
        ttk.Label(cluster3, text="Set Multiple:", width=12, anchor=tk.E).pack(side=tk.LEFT)
        self.multi_params_var = tk.StringVar(value="0000,4,1234")
        ttk.Entry(cluster3, textvariable=self.multi_params_var, width=50).pack(side=tk.LEFT, padx=self.PAD)
        ttk.Button(cluster3, text="Set", width=6, command=self.set_multiple_registers).pack(side=tk.LEFT, padx=self.PAD)
        
        # Export button - right-aligned
        ttk.Button(controls, text="Export CSV", width=12, 
                  command=self.export_registers_csv).pack(side=tk.RIGHT, padx=(self.PAD, 0))
        
        # Register display text area
        self.register_display = scrolledtext.ScrolledText(
            reg_frame, wrap=tk.NONE, height=15, 
            font=("Cascadia Mono", 10), padx=10, pady=10)
        self.register_display.pack(fill=tk.BOTH, expand=True)
    
    def clear_log(self, log_widget):
        """Clear a log widget and reset search position"""
        log_widget.delete(1.0, tk.END)
        if log_widget == self.incoming_request_log:
            self.incoming_search_pos = "1.0"
        else:
            self.outgoing_search_pos = "1.0"
    
    def toggle_error_radios(self):
        """Enable/disable radio buttons based on master checkbox"""
        if self.simulate_errors.get():
            # Enable all radio buttons
            for btn in self.error_radio_buttons:
                btn.config(state="normal")
        else:
            # Disable all radio buttons and force "No Error"
            for btn in self.error_radio_buttons:
                btn.config(state="disabled")
            self.error_type.set("none")  # Force to "No Error" when disabled
    
    def create_tooltip(self, widget, text):
        """Create tooltip for widget"""
        def on_enter(event):
            # Only show tooltip if widget is enabled
            if str(widget.cget('state')) != 'disabled':
                tooltip = tk.Toplevel()
                tooltip.wm_overrideredirect(True)
                tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
                label = tk.Label(tooltip, text=text, background="lightyellow", font=("Segoe UI", 9))
                label.pack()
                widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                delattr(widget, 'tooltip')
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def update_log_counters(self):
        """Update counter labels in panel headers"""
        self.incoming_frame.config(text=f"Incoming Requests ({self.request_count})")
        self.outgoing_frame.config(text=f"Outgoing Responses ({self.response_count})")
    
    def find_next_incoming(self):
        """Find next occurrence in incoming log"""
        search_text = self.incoming_search_var.get()
        if not search_text:
            return
        
        # Search from current position
        pos = self.incoming_request_log.search(search_text, self.incoming_search_pos, tk.END)
        if pos:
            # Found - highlight and move to position
            end_pos = f"{pos}+{len(search_text)}c"
            self.incoming_request_log.tag_remove("search_highlight", "1.0", tk.END)
            self.incoming_request_log.tag_add("search_highlight", pos, end_pos)
            self.incoming_request_log.tag_config("search_highlight", background="yellow")
            self.incoming_request_log.see(pos)
            # Update position for next search
            self.incoming_search_pos = end_pos
        else:
            # Not found - wrap to beginning
            pos = self.incoming_request_log.search(search_text, "1.0", tk.END)
            if pos:
                end_pos = f"{pos}+{len(search_text)}c"
                self.incoming_request_log.tag_remove("search_highlight", "1.0", tk.END)
                self.incoming_request_log.tag_add("search_highlight", pos, end_pos)
                self.incoming_request_log.tag_config("search_highlight", background="yellow")
                self.incoming_request_log.see(pos)
                self.incoming_search_pos = end_pos
            else:
                messagebox.showinfo("Search", "Text not found")
    
    def find_next_outgoing(self):
        """Find next occurrence in outgoing log"""
        search_text = self.outgoing_search_var.get()
        if not search_text:
            return
        
        # Search from current position
        pos = self.outgoing_response_log.search(search_text, self.outgoing_search_pos, tk.END)
        if pos:
            # Found - highlight and move to position
            end_pos = f"{pos}+{len(search_text)}c"
            self.outgoing_response_log.tag_remove("search_highlight", "1.0", tk.END)
            self.outgoing_response_log.tag_add("search_highlight", pos, end_pos)
            self.outgoing_response_log.tag_config("search_highlight", background="yellow")
            self.outgoing_response_log.see(pos)
            # Update position for next search
            self.outgoing_search_pos = end_pos
        else:
            # Not found - wrap to beginning
            pos = self.outgoing_response_log.search(search_text, "1.0", tk.END)
            if pos:
                end_pos = f"{pos}+{len(search_text)}c"
                self.outgoing_response_log.tag_remove("search_highlight", "1.0", tk.END)
                self.outgoing_response_log.tag_add("search_highlight", pos, end_pos)
                self.outgoing_response_log.tag_config("search_highlight", background="yellow")
                self.outgoing_response_log.see(pos)
                self.outgoing_search_pos = end_pos
            else:
                messagebox.showinfo("Search", "Text not found")
    
    def goto_address(self):
        """Go to specific address in register view"""
        try:
            addr = int(self.goto_addr_var.get(), 16)
            if addr >= self.register_map.size:
                messagebox.showerror("Error", f"Address {addr:04X} is beyond register map size ({self.register_map.size})")
                return
            
            # Find the line with this address
            content = self.register_display.get("1.0", tk.END)
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith(f"{addr:04X}:"):
                    line_pos = f"{i+1}.0"
                    self.register_display.see(line_pos)
                    # Highlight the line briefly
                    line_end = f"{i+1}.end"
                    self.register_display.tag_remove("goto_highlight", "1.0", tk.END)
                    self.register_display.tag_add("goto_highlight", line_pos, line_end)
                    self.register_display.tag_config("goto_highlight", background="lightblue")
                    # Remove highlight after 2 seconds
                    self.frame.after(2000, lambda: self.register_display.tag_remove("goto_highlight", "1.0", tk.END))
                    break
            else:
                messagebox.showinfo("Info", f"Address {addr:04X} not visible in current view")
        except ValueError:
            messagebox.showerror("Error", "Invalid hexadecimal address")
    
    def set_multiple_registers(self):
        """Set multiple registers from comma-separated parameters"""
        try:
            params = self.multi_params_var.get().split(',')
            if len(params) < 3:
                messagebox.showerror("Error", "Format: start_addr,count,value (e.g., 0010,4,1234)")
                return
            
            start_addr = int(params[0].strip(), 16)
            count = int(params[1].strip())
            value = int(params[2].strip(), 16)
            
            if start_addr + count > self.register_map.size:
                messagebox.showerror("Error", f"Address range exceeds register map size")
                return
            
            # Set multiple registers with the same value
            for i in range(count):
                if not self.register_map.write(start_addr + i, value):
                    messagebox.showerror("Error", f"Failed to write to address {start_addr + i:04X}")
                    return
            
            self.refresh_register_view()
            # Highlight all changed registers
            for i in range(count):
                self.highlight_register(start_addr + i)
            
            messagebox.showinfo("Success", f"Set {count} registers starting at {start_addr:04X} to value {value:04X}")
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input format: {str(e)}")
    
    def export_registers_csv(self):
        """Export register map to CSV file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Register Map"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                # Write header
                writer.writerow(["Address_Hex", "Address_Dec", "Value_Hex", "Value_Dec"])
                
                # Write register data
                for addr in range(self.register_map.size):
                    value = self.register_map.read(addr)
                    writer.writerow([
                        f"{addr:04X}",
                        str(addr),
                        f"{value:04X}",
                        str(value)
                    ])
            
            messagebox.showinfo("Success", f"Register map exported to {filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export CSV: {str(e)}")
    
    # Keep all existing methods below (update_device_address, resize_register_map, etc.)
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
    
    def reset_incoming_stats(self):
        """Reset incoming statistics"""
        self.request_count = 0
        self.update_statistics()
    
    def reset_outgoing_stats(self):
        """Reset outgoing statistics"""
        self.response_count = 0
        self.error_count = 0
        self.update_statistics()
    
    def reset_statistics(self):
        """Reset all statistics counters"""
        self.request_count = 0
        self.response_count = 0
        self.error_count = 0
        self.update_statistics()
    
    def update_statistics(self):
        """Update statistics display"""
        # Update incoming stats
        self.incoming_total_label.config(text=str(self.request_count))
        
        # Update outgoing stats
        self.outgoing_total_label.config(text=str(self.response_count))
        self.outgoing_error_label.config(text=str(self.error_count))
        
        # For incoming, we could track parse errors separately if needed
        self.incoming_error_label.config(text="0")  # Or track actual incoming errors
        
        self.update_log_counters()
    
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
                if self.incoming_auto_scroll.get():
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
            if self.incoming_auto_scroll.get():
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
        if self.incoming_auto_scroll.get():
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
        # Check for error simulation - only if enabled AND not "none"
        if self.simulate_errors.get() and self.error_type.get() != "none":
            error_type = self.error_type.get()
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
            if self.outgoing_auto_scroll.get():
                self.outgoing_response_log.see(tk.END)
            
        except Exception as e:
            self.outgoing_response_log.insert(tk.END, f"  Send error: {str(e)}\n\n", "error")
            if self.outgoing_auto_scroll.get():
                self.outgoing_response_log.see(tk.END)