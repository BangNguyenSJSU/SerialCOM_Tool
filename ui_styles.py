#!/usr/bin/env python3
"""
Shared UI styles and constants for consistent appearance across all tabs
"""

from tkinter import ttk


# Typography and spacing design tokens
FONTS = {
    "ui": ("Segoe UI", 10),
    "ui_bold": ("Segoe UI", 10, "bold"),
    "ui_small": ("Segoe UI", 9),
    "mono": ("Consolas", 10),
    "mono_small": ("Consolas", 9),
}

SPACING = {
    "padx": 8, 
    "pady": 6,
    "padx_small": 4,
    "pady_small": 3,
    "padx_large": 12,
    "pady_large": 10,
}

# Consistent color scheme across all tabs
COLORS = {
    'bg_main': '#f0f0f0',           # Light gray main background
    'bg_connection': '#e3f2fd',     # Light blue for connection/server config
    'bg_request': '#f3e5f5',        # Light purple for request/operation config
    'bg_preview': '#fff3e0',        # Light amber for preview/error simulation
    'bg_stats': '#e8f5e9',          # Light green for statistics/parameters
    'bg_log': '#ffffff',            # White for log display
    'bg_regmap': '#ffffff',         # White for register map display
    'fg_connected': '#065F46',      # Dark green for connected status
    'fg_disconnected': '#991B1B',   # Dark red for disconnected status
    'fg_running': '#065F46',        # Dark green for running status  
    'fg_stopped': '#991B1B',        # Dark red for stopped status
    'bg_connected': '#D1FAE5',      # Light green background for connected
    'bg_disconnected': '#FEE2E2',   # Light red background for disconnected
    'bg_running': '#D1FAE5',        # Light green background for running
    'bg_stopped': '#FEE2E2',        # Light red background for stopped
    'border_dark': '#9e9e9e',       # Dark gray for borders
}

# Statistics styling
STAT_COLORS = {
    'label': '#6B7280',             # Gray for stat labels
    'value': '#111827',             # Dark gray for stat values
    'warning': '#F59E0B',           # Orange for warnings/timeouts
    'error': '#DC2626',             # Red for errors
}


def init_style():
    """Initialize ttk styles for professional appearance across all tabs"""
    style = ttk.Style()
    
    # Use clean theme
    try:
        style.theme_use("clam")
    except Exception:
        pass
    
    # Global widget polish
    style.configure(".", font=FONTS["ui"])
    style.configure("TButton", padding=(10, 6))
    style.configure("TLabel", foreground="#222")
    style.configure("TEntry", padding=2)
    style.configure("TSpinbox", padding=2)
    style.configure("TLabelframe.Label", font=FONTS["ui_bold"], foreground="#374151")
    style.configure("TLabelframe", padding=8, background=COLORS['bg_main'])
    style.configure("TFrame", background=COLORS['bg_main'])
    
    # Section frames
    style.configure("Section.TLabelframe", background=COLORS['bg_main'])
    
    # Button styles
    style.configure("Accent.TButton", font=FONTS["ui_bold"])
    style.configure("Send.TButton", font=FONTS["ui_bold"])
    style.configure("Clear.TButton", foreground="#DC2626")
    style.configure("Update.TButton", foreground="#2563EB")
    
    # Statistics styles
    style.configure("StatLabel.TLabel", font=("Segoe UI", 9), foreground=STAT_COLORS['label'])
    style.configure("StatValue.TLabel", font=("Segoe UI", 11, "bold"), foreground=STAT_COLORS['value'])
    
    # Status pill styles
    style.configure("Connected.TLabel", font=FONTS["ui_bold"], foreground=COLORS['fg_connected'], 
                   background=COLORS['bg_connected'])
    style.configure("Disconnected.TLabel", font=FONTS["ui_bold"], foreground=COLORS['fg_disconnected'],
                   background=COLORS['bg_disconnected'])
    style.configure("Running.TLabel", font=FONTS["ui_bold"], foreground=COLORS['fg_running'],
                   background=COLORS['bg_running'])
    style.configure("Stopped.TLabel", font=FONTS["ui_bold"], foreground=COLORS['fg_stopped'],
                   background=COLORS['bg_stopped'])
    
    return style


def create_status_pill(parent, text="Disconnected", state="disconnected"):
    """Create a consistent status pill widget"""
    import tkinter as tk
    
    if state == "connected":
        fg, bg = COLORS['fg_connected'], COLORS['bg_connected']
    elif state == "running":
        fg, bg = COLORS['fg_running'], COLORS['bg_running']
    elif state == "stopped":
        fg, bg = COLORS['fg_stopped'], COLORS['bg_stopped']
    else:  # disconnected
        fg, bg = COLORS['fg_disconnected'], COLORS['bg_disconnected']
    
    pill = tk.Label(parent, text=text, bd=0, padx=10, pady=3, 
                   fg=fg, bg=bg, font=FONTS["ui_bold"])
    return pill


def update_status_pill(pill, text, state):
    """Update status pill appearance"""
    if state == "connected":
        fg, bg = COLORS['fg_connected'], COLORS['bg_connected']
    elif state == "running":
        fg, bg = COLORS['fg_running'], COLORS['bg_running']
    elif state == "stopped":
        fg, bg = COLORS['fg_stopped'], COLORS['bg_stopped']
    else:  # disconnected
        fg, bg = COLORS['fg_disconnected'], COLORS['bg_disconnected']
    
    pill.config(text=text, fg=fg, bg=bg)


def configure_text_widget(text_widget, widget_type="log"):
    """Configure text widget with consistent styling"""
    text_widget.configure(
        font=FONTS["mono"], 
        borderwidth=0, 
        highlightthickness=0
    )
    
    if widget_type == "log":
        # Configure log tags with high contrast colors
        text_widget.tag_config("info", foreground="#0066CC", font=FONTS["mono"])
        text_widget.tag_config("request", foreground="#00AA00", font=FONTS["mono"])
        text_widget.tag_config("response", foreground="#AA00AA", font=FONTS["mono"])
        text_widget.tag_config("error", foreground="#CC0000", font=FONTS["mono"])
        text_widget.tag_config("timeout", foreground="#FF8800", font=FONTS["mono"])
        text_widget.tag_config("system", foreground="#666666", font=FONTS["mono"])
        text_widget.tag_config("debug", foreground="#FF6600", font=FONTS["mono"])
    elif widget_type == "preview":
        # Configure preview tags
        text_widget.tag_config("header", font=FONTS["mono"], foreground="#1F4B99")
        text_widget.tag_config("field", font=FONTS["mono"], foreground="#2E2E2E")
        text_widget.tag_config("value", font=FONTS["mono"], foreground="#065F46")
        text_widget.tag_config("hex", font=FONTS["mono"], foreground="#6B21A8")
        text_widget.tag_config("address", font=FONTS["mono"], foreground="#B45309")


def create_separator(parent, orient='horizontal'):
    """Create a consistent separator"""
    sep = ttk.Separator(parent, orient=orient)
    if orient == 'horizontal':
        sep.pack(fill='x', pady=SPACING['pady'], padx=SPACING['padx'])
    else:
        sep.pack(fill='y', padx=SPACING['padx'], pady=SPACING['pady'])
    return sep


# Grid layout helpers
GRID_OPTS = {
    'label': {'sticky': 'e', 'padx': (0, 6), 'pady': 2},
    'field': {'sticky': 'w', 'padx': (0, 18), 'pady': 2},
    'field_last': {'sticky': 'w', 'pady': 2},
}