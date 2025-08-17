#!/usr/bin/env python3
"""
Register Grid Window - Display and edit register names and values from CSV files
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import os
from ui_styles import FONTS, COLORS, SPACING


class RegisterGridWindow:
    """Window for displaying and editing register data in a grid format"""
    
    def __init__(self, parent, modbus_master=None, host_tab=None, title="Register Grid View"):
        """Initialize the register grid window
        
        Args:
            parent: Parent widget
            modbus_master: ModbusTCPMasterTab instance for sending requests
            host_tab: Host tab instance
            title: Window title
        """
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("900x600")
        self.window.configure(bg=COLORS['bg_main'])
        
        # Store reference to modbus master or host tab
        self.modbus_master = modbus_master
        self.host_tab = host_tab
        
        # Data storage
        self.register_data = []
        self.csv_filename = None
        
        # Operation buttons storage
        self.operation_widgets = {}
        
        # Create widgets
        self.create_widgets()
        
        # Focus on the new window
        self.window.focus_set()
        
    def create_widgets(self):
        """Create all widgets for the window"""
        # Top toolbar frame
        toolbar_frame = ttk.Frame(self.window)
        toolbar_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Load CSV button
        self.load_btn = ttk.Button(toolbar_frame, text="📁 Load CSV", 
                                  command=self.load_csv_file)
        self.load_btn.pack(side=tk.LEFT, padx=5)
        
        # Save CSV button
        self.save_btn = ttk.Button(toolbar_frame, text="💾 Save CSV", 
                                  command=self.save_csv_file, state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        # Add row button
        self.add_btn = ttk.Button(toolbar_frame, text="➕ Add Row", 
                                 command=self.add_row, state=tk.DISABLED)
        self.add_btn.pack(side=tk.LEFT, padx=5)
        
        # Delete row button
        self.delete_btn = ttk.Button(toolbar_frame, text="🗑️ Delete Row", 
                                     command=self.delete_selected_rows, state=tk.DISABLED)
        self.delete_btn.pack(side=tk.LEFT, padx=5)
        
        # Current file label
        self.file_label = ttk.Label(toolbar_frame, text="No file loaded", 
                                   font=FONTS['default'])
        self.file_label.pack(side=tk.RIGHT, padx=10)
        
        # Main frame for treeview
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create Treeview with scrollbars
        self.create_treeview(main_frame)
        
        # Status bar
        self.status_label = ttk.Label(self.window, text="Ready", relief=tk.SUNKEN)
        self.status_label.pack(fill=tk.X, side=tk.BOTTOM)
        
    def create_treeview(self, parent):
        """Create the treeview widget with scrollbars"""
        # Create frame for treeview and scrollbars
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Create Treeview
        self.tree = ttk.Treeview(tree_frame, 
                                columns=("address", "name", "value", "description", "operations"),
                                show="tree headings",
                                yscrollcommand=vsb.set,
                                xscrollcommand=hsb.set)
        
        # Configure scrollbars
        vsb.configure(command=self.tree.yview)
        hsb.configure(command=self.tree.xview)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        # Configure grid weights
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Configure columns
        self.tree.heading("#0", text="Index")
        self.tree.heading("address", text="Address")
        self.tree.heading("name", text="Register Name")
        self.tree.heading("value", text="Value")
        self.tree.heading("description", text="Description")
        self.tree.heading("operations", text="Operations")
        
        # Column widths
        self.tree.column("#0", width=60, stretch=False)
        self.tree.column("address", width=100)
        self.tree.column("name", width=200)
        self.tree.column("value", width=100)
        self.tree.column("description", width=250)
        self.tree.column("operations", width=150, stretch=False)
        
        # Bind double-click for editing
        self.tree.bind("<Double-Button-1>", self.on_double_click)
        
        # Bind tree events for operation buttons
        self.tree.bind("<ButtonRelease-1>", self.on_tree_click)
        
    def load_csv_file(self):
        """Load register data from a CSV file"""
        filename = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filename:
            return
            
        try:
            # Clear existing data
            self.clear_tree()
            self.register_data = []
            
            # Read CSV file
            with open(filename, 'r', encoding='utf-8') as file:
                # Try to detect delimiter
                sample = file.read(1024)
                file.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.DictReader(file, delimiter=delimiter)
                
                # Check for required columns
                if reader.fieldnames:
                    # Try to map columns intelligently
                    fieldnames_lower = [f.lower() for f in reader.fieldnames]
                    
                    # Map columns
                    address_col = next((f for f in reader.fieldnames 
                                      if f.lower() in ['address', 'addr', 'register']), None)
                    name_col = next((f for f in reader.fieldnames 
                                   if f.lower() in ['name', 'register_name', 'reg_name']), None)
                    value_col = next((f for f in reader.fieldnames 
                                    if f.lower() in ['value', 'data', 'register_value']), None)
                    desc_col = next((f for f in reader.fieldnames 
                                   if f.lower() in ['description', 'desc', 'comment']), None)
                    
                    # Read data
                    index = 0
                    for row in reader:
                        register = {
                            'index': index,
                            'address': row.get(address_col, '') if address_col else '',
                            'name': row.get(name_col, '') if name_col else '',
                            'value': row.get(value_col, '') if value_col else '',
                            'description': row.get(desc_col, '') if desc_col else ''
                        }
                        
                        # Add to data list
                        self.register_data.append(register)
                        
                        # Add to tree
                        item = self.tree.insert('', 'end', text=str(index),
                                       values=(register['address'], 
                                              register['name'],
                                              register['value'],
                                              register['description'],
                                              ''))
                        
                        # Add operation buttons
                        self.add_operation_buttons(item, register)
                        
                        index += 1
                    
            # Update UI
            self.csv_filename = filename
            self.file_label.config(text=f"File: {os.path.basename(filename)}")
            self.status_label.config(text=f"Loaded {len(self.register_data)} registers")
            
            # Enable buttons
            self.save_btn.config(state=tk.NORMAL)
            self.add_btn.config(state=tk.NORMAL)
            self.delete_btn.config(state=tk.NORMAL)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV file:\n{str(e)}")
            
    def save_csv_file(self):
        """Save register data to a CSV file"""
        filename = filedialog.asksaveasfilename(
            title="Save CSV file",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filename:
            return
            
        try:
            # Get all data from tree
            self.update_data_from_tree()
            
            # Write CSV file
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                fieldnames = ['address', 'name', 'value', 'description']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                
                # Write header
                writer.writeheader()
                
                # Write data
                for register in self.register_data:
                    writer.writerow({
                        'address': register['address'],
                        'name': register['name'],
                        'value': register['value'],
                        'description': register['description']
                    })
                    
            self.status_label.config(text=f"Saved {len(self.register_data)} registers to {os.path.basename(filename)}")
            messagebox.showinfo("Success", "File saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save CSV file:\n{str(e)}")
            
    def add_row(self):
        """Add a new empty row to the grid"""
        index = len(self.register_data)
        
        # Add to data
        new_register = {
            'index': index,
            'address': '',
            'name': '',
            'value': '',
            'description': ''
        }
        self.register_data.append(new_register)
        
        # Add to tree
        item = self.tree.insert('', 'end', text=str(index),
                               values=('', '', '', '', ''))
        
        # Add operation buttons for new row
        self.add_operation_buttons(item, new_register)
        
        # Select and focus the new item
        self.tree.selection_set(item)
        self.tree.focus(item)
        self.tree.see(item)
        
        self.status_label.config(text=f"Added new row (index {index})")
        
    def delete_selected_rows(self):
        """Delete selected rows from the grid"""
        selected_items = self.tree.selection()
        
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select rows to delete")
            return
            
        # Confirm deletion
        if messagebox.askyesno("Confirm Delete", 
                              f"Delete {len(selected_items)} selected row(s)?"):
            # Delete items
            for item in selected_items:
                self.tree.delete(item)
                
            # Rebuild data and reindex
            self.rebuild_data()
            
            self.status_label.config(text=f"Deleted {len(selected_items)} row(s)")
            
    def clear_tree(self):
        """Clear all items from the tree"""
        for item in self.tree.get_children():
            self.tree.delete(item)
            
    def update_data_from_tree(self):
        """Update internal data from tree widget"""
        self.register_data = []
        
        for index, item in enumerate(self.tree.get_children()):
            values = self.tree.item(item, 'values')
            register = {
                'index': index,
                'address': values[0],
                'name': values[1],
                'value': values[2],
                'description': values[3]
            }
            self.register_data.append(register)
            
    def rebuild_data(self):
        """Rebuild data and reindex after deletion"""
        # Get current tree data
        temp_data = []
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            temp_data.append({
                'address': values[0],
                'name': values[1],
                'value': values[2],
                'description': values[3]
            })
            
        # Clear tree
        self.clear_tree()
        
        # Rebuild with new indices
        self.register_data = []
        for index, data in enumerate(temp_data):
            data['index'] = index
            self.register_data.append(data)
            
            # Add to tree
            self.tree.insert('', 'end', text=str(index),
                           values=(data['address'], 
                                  data['name'],
                                  data['value'],
                                  data['description'],
                                  ''))
            
    def on_double_click(self, event):
        """Handle double-click for editing cells"""
        # Get selected item
        item = self.tree.selection()[0]
        column = self.tree.identify_column(event.x)
        
        # Get column index (skip the tree column #0)
        if column == '#0':
            return  # Don't edit index column
            
        col_index = int(column.replace('#', '')) - 1
        
        # Get current value
        values = list(self.tree.item(item, 'values'))
        current_value = values[col_index]
        
        # Create edit window
        self.edit_cell(item, col_index, current_value)
        
    def edit_cell(self, item, col_index, current_value):
        """Create an entry widget to edit a cell"""
        # Get bounding box of the cell
        bbox = self.tree.bbox(item, column=f'#{col_index + 1}')
        if not bbox:
            return
            
        # Create entry widget
        entry = ttk.Entry(self.tree, font=FONTS['default'])
        entry.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
        
        # Set current value
        entry.insert(0, current_value)
        entry.select_range(0, tk.END)
        entry.focus()
        
        # Bind events
        def save_edit(event=None):
            new_value = entry.get()
            values = list(self.tree.item(item, 'values'))
            values[col_index] = new_value
            self.tree.item(item, values=values)
            entry.destroy()
            self.status_label.config(text="Cell updated")
            
        def cancel_edit(event=None):
            entry.destroy()
            
        entry.bind('<Return>', save_edit)
        entry.bind('<Escape>', cancel_edit)
        entry.bind('<FocusOut>', save_edit)
        
    def get_register_data(self):
        """Get the current register data"""
        self.update_data_from_tree()
        return self.register_data

    def add_operation_buttons(self, tree_item, register_data):
        """Add READ and WRITE buttons to a tree item"""
        if not self.modbus_master and not self.host_tab:
            return
            
        # Create a frame to hold the buttons
        button_frame = ttk.Frame(self.tree)
        
        # READ button
        read_btn = ttk.Button(button_frame, text="📖 Read", width=8,
                            command=lambda: self.perform_read(tree_item, register_data))
        read_btn.pack(side=tk.LEFT, padx=2)
        
        # WRITE button  
        write_btn = ttk.Button(button_frame, text="✏️ Write", width=8,
                             command=lambda: self.perform_write(tree_item, register_data))
        write_btn.pack(side=tk.LEFT, padx=2)
        
        # Store the frame reference
        self.operation_widgets[tree_item] = button_frame
        
        # Place the frame in the operations column
        self.tree.set(tree_item, 'operations', '')
        self.update_button_position(tree_item)
        
    def update_button_position(self, tree_item):
        """Update the position of operation buttons for a tree item"""
        if tree_item not in self.operation_widgets:
            return
            
        # Get the bounding box for the operations column
        bbox = self.tree.bbox(tree_item, column='operations')
        if bbox:
            button_frame = self.operation_widgets[tree_item]
            # Place the frame in the center of the cell
            x = bbox[0] + 5
            y = bbox[1] + (bbox[3] - 20) // 2  # Center vertically
            button_frame.place(x=x, y=y)
            
    def on_tree_click(self, event):
        """Handle tree click events to update button positions"""
        # Update all button positions after a short delay
        self.window.after(10, self.update_all_button_positions)
        
    def update_all_button_positions(self):
        """Update positions of all operation buttons"""
        for item in self.operation_widgets:
            self.update_button_position(item)
            
    def perform_read(self, tree_item, register_data):
        """Perform a read operation for the register"""
        try:
            address = register_data.get('address', '')
            if not address:
                messagebox.showwarning("Invalid Address", "Please specify a register address")
                return
                
            # Convert address to integer
            if address.startswith('0x'):
                addr_int = int(address, 16)
            else:
                addr_int = int(address)
                
            # Send read request based on which tab is active
            if self.modbus_master:
                # Check if modbus master is connected
                if not self.modbus_master.is_connected or not self.modbus_master.client_socket:
                    messagebox.showwarning("Not Connected", "Please connect to Modbus server first")
                    return
                    
                # Send read request using Read Multiple (0x03) for single register
                self.status_label.config(text=f"Reading register {address}...")
                
                # Update UI to use the existing read operation
                saved_operation = self.modbus_master.operation_var.get()
                saved_addr = self.modbus_master.start_addr_var.get()
                saved_count = self.modbus_master.count_var.get()
                
                try:
                    # Set up for read operation
                    self.modbus_master.operation_var.set("read")
                    self.modbus_master.start_addr_var.set(f"{addr_int:04X}")
                    self.modbus_master.count_var.set(1)
                    
                    # Send the request
                    self.modbus_master.send_request()
                    
                    # For now, we can't get immediate response - show status
                    self.status_label.config(text=f"Read request sent for register 0x{addr_int:04X}")
                    
                finally:
                    # Restore original values
                    self.modbus_master.operation_var.set(saved_operation)
                    self.modbus_master.start_addr_var.set(saved_addr)
                    self.modbus_master.count_var.set(saved_count)
                    
            elif self.host_tab:
                # Check if host tab is connected
                if not self.host_tab.serial_connection.is_connected:
                    messagebox.showwarning("Not Connected", "Please connect to serial port first")
                    return
                    
                # Send read request through host tab protocol
                self.status_label.config(text=f"Reading register {address}...")
                
                success, result = self.host_tab.send_protocol_request(
                    function_code=0x01,  # Read Single
                    start_addr=addr_int,
                    count=1
                )
                
                if success and isinstance(result, dict) and 'value' in result:
                    # Update the value in the tree
                    values = list(self.tree.item(tree_item, 'values'))
                    values[2] = f"0x{result['value']:04X}"
                    self.tree.item(tree_item, values=values)
                    self.status_label.config(text=f"Read successful: {values[2]}")
                else:
                    error_msg = result if isinstance(result, str) else "Read failed"
                    self.status_label.config(text=error_msg)
                    
        except Exception as e:
            messagebox.showerror("Read Error", f"Failed to read register:\n{str(e)}")
            self.status_label.config(text="Read error")
            
    def perform_write(self, tree_item, register_data):
        """Perform a write operation for the register"""
        try:
            address = register_data.get('address', '')
            value = self.tree.item(tree_item, 'values')[2]  # Get current value from tree
            
            if not address:
                messagebox.showwarning("Invalid Address", "Please specify a register address")
                return
                
            if not value:
                messagebox.showwarning("Invalid Value", "Please specify a value to write")
                return
                
            # Convert address and value to integers
            if address.startswith('0x'):
                addr_int = int(address, 16)
            else:
                addr_int = int(address)
                
            if value.startswith('0x'):
                val_int = int(value, 16)
            else:
                val_int = int(value)
                
            # Send write request based on which tab is active
            if self.modbus_master:
                # Check if modbus master is connected
                if not self.modbus_master.is_connected or not self.modbus_master.client_socket:
                    messagebox.showwarning("Not Connected", "Please connect to Modbus server first")
                    return
                    
                # Send write request using Write Multiple (0x10) for single register
                self.status_label.config(text=f"Writing {value} to register {address}...")
                
                # Update UI to use the existing write operation
                saved_operation = self.modbus_master.operation_var.get()
                saved_addr = self.modbus_master.start_addr_var.get()
                saved_values = self.modbus_master.values_var.get()
                
                try:
                    # Set up for write operation
                    self.modbus_master.operation_var.set("write")
                    self.modbus_master.start_addr_var.set(f"{addr_int:04X}")
                    self.modbus_master.values_var.set(f"{val_int:04X}")
                    
                    # Send the request
                    self.modbus_master.send_request()
                    
                    # Show status
                    self.status_label.config(text=f"Write request sent: 0x{val_int:04X} → 0x{addr_int:04X}")
                    
                finally:
                    # Restore original values
                    self.modbus_master.operation_var.set(saved_operation)
                    self.modbus_master.start_addr_var.set(saved_addr)
                    self.modbus_master.values_var.set(saved_values)
                    
            elif self.host_tab:
                # Check if host tab is connected
                if not self.host_tab.serial_connection.is_connected:
                    messagebox.showwarning("Not Connected", "Please connect to serial port first")
                    return
                    
                # Send write request through host tab protocol
                self.status_label.config(text=f"Writing {value} to register {address}...")
                
                success, result = self.host_tab.send_protocol_request(
                    function_code=0x02,  # Write Single (correct function code)
                    start_addr=addr_int,
                    count=1,
                    values=[val_int]  # Pass as list for write operations
                )
                
                if success:
                    self.status_label.config(text=f"Write successful: {value} → {address}")
                else:
                    error_msg = result if isinstance(result, str) else "Write failed"
                    self.status_label.config(text=error_msg)
                    
        except Exception as e:
            messagebox.showerror("Write Error", f"Failed to write register:\n{str(e)}")
            self.status_label.config(text="Write error")
