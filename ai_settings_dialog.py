#!/usr/bin/env python3
"""
AI Settings Dialog for SerialCOM Tool
Provides GUI for configuring AI analysis settings and API key management
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
from ai_config import AIConfig
from ai_analyzer import AIAnalyzer
import logging

logger = logging.getLogger(__name__)


class AISettingsDialog:
    """Dialog for configuring AI analysis settings"""
    
    def __init__(self, parent: tk.Tk, ai_config: AIConfig, update_callback: Callable = None):
        """Initialize AI settings dialog
        
        Args:
            parent: Parent window
            ai_config: AI configuration instance
            update_callback: Function to call when settings are updated
        """
        self.parent = parent
        self.ai_config = ai_config
        self.update_callback = update_callback
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("AI Analysis Settings")
        self.dialog.geometry("600x500")
        self.dialog.resizable(True, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.center_dialog()
        
        # Variables for settings
        self.api_key_var = tk.StringVar()
        self.model_var = tk.StringVar()
        self.max_tokens_var = tk.IntVar()
        self.temperature_var = tk.DoubleVar()
        self.analyze_protocol_var = tk.BooleanVar()
        self.analyze_errors_var = tk.BooleanVar()
        self.analyze_patterns_var = tk.BooleanVar()
        self.auto_analysis_var = tk.BooleanVar()
        self.rate_limit_var = tk.IntVar()
        self.analysis_delay_var = tk.IntVar()
        
        # Test variables
        self.test_result_var = tk.StringVar(value="Not tested")
        
        # Load current settings
        self.load_current_settings()
        
        # Create GUI
        self.create_widgets()
        
        # Bind close event
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
    
    def center_dialog(self):
        """Center dialog on parent window"""
        self.dialog.update_idletasks()
        
        # Get parent window position and size
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Calculate dialog position
        dialog_width = self.dialog.winfo_reqwidth()
        dialog_height = self.dialog.winfo_reqheight()
        
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"+{x}+{y}")
    
    def load_current_settings(self):
        """Load current settings from configuration"""
        # Load API key
        api_key = self.ai_config.load_api_key()
        if api_key:
            # Mask API key for display
            masked_key = f"{api_key[:8]}...{api_key[-8:]}" if len(api_key) > 16 else "•" * len(api_key)
            self.api_key_var.set(masked_key)
        
        # Load analysis settings
        analysis_settings = self.ai_config.get_analysis_settings()
        self.model_var.set(analysis_settings.get("model", "gpt-3.5-turbo"))
        self.max_tokens_var.set(analysis_settings.get("max_tokens", 500))
        self.temperature_var.set(analysis_settings.get("temperature", 0.3))
        self.analyze_protocol_var.set(analysis_settings.get("analyze_protocol", True))
        self.analyze_errors_var.set(analysis_settings.get("analyze_errors", True))
        self.analyze_patterns_var.set(analysis_settings.get("analyze_patterns", True))
        self.auto_analysis_var.set(analysis_settings.get("auto_analysis", True))
        self.rate_limit_var.set(analysis_settings.get("rate_limit_per_minute", 20))
        self.analysis_delay_var.set(analysis_settings.get("analysis_delay_ms", 1000))
    
    def create_widgets(self):
        """Create dialog widgets"""
        # Main notebook for tabs
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # API Configuration Tab
        api_frame = ttk.Frame(notebook)
        notebook.add(api_frame, text="API Configuration")
        self.create_api_tab(api_frame)
        
        # Analysis Settings Tab
        analysis_frame = ttk.Frame(notebook)
        notebook.add(analysis_frame, text="Analysis Settings")
        self.create_analysis_tab(analysis_frame)
        
        # Testing Tab
        test_frame = ttk.Frame(notebook)
        notebook.add(test_frame, text="Testing")
        self.create_test_tab(test_frame)
        
        # Button frame
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Buttons
        ttk.Button(button_frame, text="Save", command=self.on_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Apply", command=self.on_apply).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Reset to Defaults", command=self.on_reset).pack(side=tk.LEFT, padx=5)
    
    def create_api_tab(self, parent):
        """Create API configuration tab"""
        # API Key section
        api_group = ttk.LabelFrame(parent, text="OpenAI API Configuration", padding="10")
        api_group.pack(fill=tk.X, padx=10, pady=10)
        
        # API Key input
        tk.Label(api_group, text="API Key:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        key_frame = tk.Frame(api_group)
        key_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        key_frame.columnconfigure(0, weight=1)
        
        self.api_key_entry = tk.Entry(key_frame, textvariable=self.api_key_var, width=50, show="•")
        self.api_key_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(key_frame, text="Show", command=self.toggle_api_key_visibility).grid(row=0, column=1, padx=(5, 0))
        ttk.Button(key_frame, text="New Key", command=self.set_new_api_key).grid(row=0, column=2, padx=(5, 0))
        
        # API Key instructions
        instructions = tk.Text(api_group, height=4, wrap=tk.WORD, bg="#f9f9f9", relief=tk.FLAT)
        instructions.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        instructions.insert(tk.END, 
            "To get your OpenAI API key:\n"
            "1. Visit https://platform.openai.com/api-keys\n"
            "2. Sign in to your OpenAI account\n"
            "3. Create a new API key\n"
            "4. Copy and paste it above")
        instructions.config(state=tk.DISABLED)
        
        # Model selection
        tk.Label(api_group, text="Model:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=(10, 5))
        model_combo = ttk.Combobox(api_group, textvariable=self.model_var, width=20, state="readonly")
        model_combo['values'] = ("gpt-3.5-turbo", "gpt-4", "gpt-4-turbo")
        model_combo.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 5))
        
        # Rate limiting
        tk.Label(api_group, text="Rate Limit (req/min):", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky=tk.W, pady=5)
        rate_spin = ttk.Spinbox(api_group, from_=1, to=60, textvariable=self.rate_limit_var, width=10)
        rate_spin.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Configure grid weights
        api_group.columnconfigure(1, weight=1)
    
    def create_analysis_tab(self, parent):
        """Create analysis settings tab"""
        # Analysis types
        types_group = ttk.LabelFrame(parent, text="Analysis Types", padding="10")
        types_group.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Checkbutton(types_group, text="Protocol Analysis", variable=self.analyze_protocol_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(types_group, text="Error Detection", variable=self.analyze_errors_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(types_group, text="Pattern Recognition", variable=self.analyze_patterns_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(types_group, text="Automatic Analysis", variable=self.auto_analysis_var).pack(anchor=tk.W, pady=2)
        
        # Advanced settings
        advanced_group = ttk.LabelFrame(parent, text="Advanced Settings", padding="10")
        advanced_group.pack(fill=tk.X, padx=10, pady=10)
        
        # Max tokens
        tk.Label(advanced_group, text="Max Tokens:").grid(row=0, column=0, sticky=tk.W, pady=5)
        tokens_spin = ttk.Spinbox(advanced_group, from_=100, to=2000, textvariable=self.max_tokens_var, width=10)
        tokens_spin.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Temperature
        tk.Label(advanced_group, text="Temperature:").grid(row=1, column=0, sticky=tk.W, pady=5)
        temp_spin = ttk.Spinbox(advanced_group, from_=0.0, to=1.0, increment=0.1, textvariable=self.temperature_var, width=10)
        temp_spin.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Analysis delay
        tk.Label(advanced_group, text="Analysis Delay (ms):").grid(row=2, column=0, sticky=tk.W, pady=5)
        delay_spin = ttk.Spinbox(advanced_group, from_=500, to=5000, increment=500, textvariable=self.analysis_delay_var, width=10)
        delay_spin.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Help text
        help_text = tk.Text(advanced_group, height=6, wrap=tk.WORD, bg="#f9f9f9", relief=tk.FLAT)
        help_text.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        help_text.insert(tk.END,
            "Settings Explanation:\n"
            "• Max Tokens: Maximum length of AI response (higher = more detailed)\n"
            "• Temperature: Creativity level (0.0 = focused, 1.0 = creative)\n"
            "• Analysis Delay: Minimum time between analyses (prevents rate limiting)")
        help_text.config(state=tk.DISABLED)
        
        advanced_group.columnconfigure(1, weight=1)
    
    def create_test_tab(self, parent):
        """Create testing tab"""
        test_group = ttk.LabelFrame(parent, text="API Connection Test", padding="10")
        test_group.pack(fill=tk.X, padx=10, pady=10)
        
        # Test button
        test_btn = ttk.Button(test_group, text="Test API Connection", command=self.test_api_connection)
        test_btn.pack(pady=10)
        
        # Test result
        tk.Label(test_group, text="Test Result:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        result_label = tk.Label(test_group, textvariable=self.test_result_var, 
                               font=("Arial", 10), fg="#333333", justify=tk.LEFT)
        result_label.pack(anchor=tk.W, pady=5)
        
        # Sample analysis
        sample_group = ttk.LabelFrame(parent, text="Sample Analysis", padding="10")
        sample_group.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Sample data input
        tk.Label(sample_group, text="Test Data (hex):").pack(anchor=tk.W, pady=5)
        self.sample_data_var = tk.StringVar(value="7E01010548656C6C6F20576F726C640D0A")
        sample_entry = tk.Entry(sample_group, textvariable=self.sample_data_var, width=50)
        sample_entry.pack(fill=tk.X, pady=5)
        
        # Analyze button
        ttk.Button(sample_group, text="Analyze Sample", command=self.analyze_sample).pack(pady=10)
        
        # Analysis result
        self.sample_result = tk.Text(sample_group, height=8, wrap=tk.WORD)
        self.sample_result.pack(fill=tk.BOTH, expand=True, pady=5)
    
    def toggle_api_key_visibility(self):
        """Toggle API key visibility"""
        if self.api_key_entry['show'] == "•":
            self.api_key_entry.config(show="")
        else:
            self.api_key_entry.config(show="•")
    
    def set_new_api_key(self):
        """Prompt for new API key"""
        new_key = tk.simpledialog.askstring(
            "New API Key", 
            "Enter your OpenAI API key:",
            show="*"
        )
        if new_key:
            self.api_key_var.set(new_key)
    
    def test_api_connection(self):
        """Test API connection"""
        try:
            api_key = self.api_key_var.get()
            if not api_key or "•" in api_key:
                # Get real API key if masked
                api_key = self.ai_config.load_api_key()
            
            if not api_key:
                self.test_result_var.set("❌ No API key provided")
                return
            
            # Create temporary analyzer for testing
            test_analyzer = AIAnalyzer(api_key)
            
            if test_analyzer.is_enabled:
                self.test_result_var.set("✅ API connection successful")
            else:
                self.test_result_var.set("❌ API connection failed - Invalid key")
                
        except Exception as e:
            self.test_result_var.set(f"❌ Connection error: {str(e)}")
    
    def analyze_sample(self):
        """Analyze sample data"""
        try:
            # Get API key
            api_key = self.api_key_var.get()
            if not api_key or "•" in api_key:
                api_key = self.ai_config.load_api_key()
            
            if not api_key:
                self.sample_result.delete(1.0, tk.END)
                self.sample_result.insert(tk.END, "No API key configured")
                return
            
            # Get sample data
            hex_data = self.sample_data_var.get().strip()
            try:
                data = bytes.fromhex(hex_data)
            except ValueError:
                self.sample_result.delete(1.0, tk.END)
                self.sample_result.insert(tk.END, "Invalid hex data")
                return
            
            # Create analyzer and analyze
            analyzer = AIAnalyzer(api_key)
            if not analyzer.is_enabled:
                self.sample_result.delete(1.0, tk.END)
                self.sample_result.insert(tk.END, "API key invalid")
                return
            
            self.sample_result.delete(1.0, tk.END)
            self.sample_result.insert(tk.END, "Analyzing... Please wait...")
            self.dialog.update()
            
            result = analyzer.analyze_data(data)
            
            # Display result
            self.sample_result.delete(1.0, tk.END)
            if result:
                output = f"Analysis Type: {result.analysis_type}\n"
                output += f"Confidence: {result.confidence:.1%}\n"
                output += f"Description: {result.description}\n\n"
                
                if result.suggestions:
                    output += "Suggestions:\n"
                    for suggestion in result.suggestions:
                        output += f"• {suggestion}\n"
                
                self.sample_result.insert(tk.END, output)
            else:
                self.sample_result.insert(tk.END, "Analysis failed or returned no results")
                
        except Exception as e:
            self.sample_result.delete(1.0, tk.END)
            self.sample_result.insert(tk.END, f"Error: {str(e)}")
    
    def on_save(self):
        """Save settings and close dialog"""
        if self.save_settings():
            self.dialog.destroy()
    
    def on_apply(self):
        """Apply settings without closing dialog"""
        self.save_settings()
    
    def on_cancel(self):
        """Cancel and close dialog"""
        self.dialog.destroy()
    
    def on_reset(self):
        """Reset to default settings"""
        if messagebox.askyesno("Reset Settings", "Reset all settings to defaults?"):
            self.ai_config.reset_to_defaults()
            self.load_current_settings()
            messagebox.showinfo("Reset Complete", "Settings have been reset to defaults")
    
    def save_settings(self) -> bool:
        """Save current settings"""
        try:
            # Save API key if it's been entered or changed
            api_key = self.api_key_var.get()
            if api_key and "•" not in api_key:
                # Always save if it's not masked (user entered a new key)
                if not self.ai_config.save_api_key(api_key):
                    messagebox.showerror("Error", "Failed to save API key")
                    return False
                print(f"DEBUG: Saved API key: {api_key[:10]}...{api_key[-10:]}")
            elif api_key and "•" in api_key:
                # If it's masked, it means the key was already loaded and not changed
                print("DEBUG: API key is masked, not saving (already configured)")
            else:
                print("DEBUG: No API key to save")
            
            # Save analysis settings
            analysis_settings = {
                "model": self.model_var.get(),
                "max_tokens": self.max_tokens_var.get(),
                "temperature": self.temperature_var.get(),
                "analyze_protocol": self.analyze_protocol_var.get(),
                "analyze_errors": self.analyze_errors_var.get(),
                "analyze_patterns": self.analyze_patterns_var.get(),
                "auto_analysis": self.auto_analysis_var.get(),
                "rate_limit_per_minute": self.rate_limit_var.get(),
                "analysis_delay_ms": self.analysis_delay_var.get()
            }
            
            if not self.ai_config.update_analysis_settings(analysis_settings):
                messagebox.showerror("Error", "Failed to save analysis settings")
                return False
            
            # Call update callback
            if self.update_callback:
                self.update_callback()
            
            messagebox.showinfo("Settings Saved", "AI analysis settings have been saved successfully")
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
            return False


# Import this in serial_gui.py
import tkinter.simpledialog

# Test function
def test_ai_settings_dialog():
    """Test the AI settings dialog"""
    root = tk.Tk()
    root.title("Test AI Settings Dialog")
    root.geometry("400x200")
    
    from ai_config import AIConfig
    config = AIConfig()
    
    def open_dialog():
        AISettingsDialog(root, config)
    
    ttk.Button(root, text="Open AI Settings", command=open_dialog).pack(pady=50)
    
    root.mainloop()


if __name__ == "__main__":
    test_ai_settings_dialog()