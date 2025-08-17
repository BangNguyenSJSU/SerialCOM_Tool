#!/usr/bin/env python3
"""
Shared UI styles and constants for consistent appearance across all tabs
"""

# Only include fonts and spacing that are actually used
FONTS = {
    "default": ("Segoe UI", 10),
    "mono": ("Consolas", 10),
}

SPACING = {
    "padx": 8, 
    "pady": 6,
}

# Consistent color scheme across all tabs
COLORS = {
    'bg_main': '#708090',           # Slate gray main background
    'fg_connected': '#4caf50',      # Green for connected status
    'fg_disconnected': '#f44336',   # Red for disconnected status
}