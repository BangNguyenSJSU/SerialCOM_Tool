#!/usr/bin/env python3
"""
AI Features Demo for SerialCOM Tool
Demonstrates the new AI analysis capabilities
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import time
import threading
from test_ai_integration import MockAIAnalyzer

class AIFeaturesDemo:
    """Demo application showing AI analysis features"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SerialCOM Tool - AI Features Demo")
        self.root.geometry("1000x700")
        
        # AI components
        self.ai_analyzer = MockAIAnalyzer()
        self.demo_running = False
        
        self.create_widgets()
        
    def create_widgets(self):
        """Create demo interface"""
        # Title
        title_label = tk.Label(self.root, text="🤖 SerialCOM Tool - AI Analysis Demo", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Description
        desc_text = """This demo shows the new AI-powered analysis features integrated into SerialCOM Tool.
The AI can analyze serial communication data in real-time and provide intelligent insights."""
        desc_label = tk.Label(self.root, text=desc_text, font=("Arial", 10), 
                             justify=tk.CENTER, wraplength=800)
        desc_label.pack(pady=5)
        
        # Control frame
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=10)
        
        # Demo buttons
        self.start_btn = ttk.Button(control_frame, text="Start Demo", 
                                   command=self.start_demo)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="Stop Demo", 
                                  command=self.stop_demo, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Clear Log", 
                  command=self.clear_log).pack(side=tk.LEFT, padx=5)
        
        # Features showcase
        features_frame = ttk.LabelFrame(self.root, text="AI Features Overview", padding="10")
        features_frame.pack(fill=tk.X, padx=20, pady=10)
        
        features_text = """
✓ Protocol Detection: Automatically identifies communication protocols and packet structures
✓ Error Analysis: Detects and explains communication errors and protocol violations  
✓ Pattern Recognition: Identifies data patterns, sequences, and repeated structures
✓ Real-time Insights: Provides intelligent analysis of serial data as it arrives
✓ Smart Suggestions: Offers actionable debugging and troubleshooting recommendations
✓ Color-coded Display: Visual highlighting of different analysis types and importance levels
        """.strip()
        
        tk.Label(features_frame, text=features_text, font=("Arial", 10), 
                justify=tk.LEFT).pack(anchor=tk.W)
        
        # Demo display
        display_frame = ttk.LabelFrame(self.root, text="Live Analysis Demo", padding="10")
        display_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Create text display with AI tags
        self.demo_display = scrolledtext.ScrolledText(display_frame, height=20, 
                                                     font=("Consolas", 10))
        self.demo_display.pack(fill=tk.BOTH, expand=True)
        
        # Configure AI analysis tags
        self.demo_display.tag_config("tx", foreground="green", font=("Consolas", 10, "bold"))
        self.demo_display.tag_config("rx", foreground="blue", font=("Consolas", 10, "bold"))
        self.demo_display.tag_config("ai_insight", foreground="#FF6600", 
                                    background="#FFF8E0", font=("Consolas", 10, "bold"))
        self.demo_display.tag_config("ai_protocol", foreground="#8B008B", 
                                    background="#FFF0FF", font=("Consolas", 10, "bold"))
        self.demo_display.tag_config("ai_error", foreground="#DC143C", 
                                    background="#FFE4E1", font=("Consolas", 10, "bold"))
        self.demo_display.tag_config("ai_pattern", foreground="#006400", 
                                    background="#F0FFF0", font=("Consolas", 10, "bold"))
        self.demo_display.tag_config("system", foreground="gray", font=("Consolas", 10))
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready to start demo")
        status_bar = tk.Label(self.root, textvariable=self.status_var, 
                             relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
    def start_demo(self):
        """Start the demo"""
        self.demo_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("Demo running - Simulating serial communication with AI analysis")
        
        # Start demo thread
        demo_thread = threading.Thread(target=self.run_demo, daemon=True)
        demo_thread.start()
        
    def stop_demo(self):
        """Stop the demo"""
        self.demo_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("Demo stopped")
        
    def clear_log(self):
        """Clear the demo log"""
        self.demo_display.delete(1.0, tk.END)
        
    def add_message(self, message, tag="system"):
        """Add message to display"""
        self.demo_display.insert(tk.END, message + "\n", tag)
        self.demo_display.see(tk.END)
        
    def run_demo(self):
        """Run the demo simulation"""
        demo_scenarios = [
            {
                "name": "Custom Protocol Communication",
                "data": [
                    ("TX", bytes.fromhex("7E01010548656C6C6F20576F726C640D0A")),
                    ("RX", bytes.fromhex("7E0181050548656C6C6F15A3"))
                ]
            },
            {
                "name": "Error Condition Detection", 
                "data": [
                    ("TX", b"GET STATUS"),
                    ("RX", b"ERROR: Device not ready")
                ]
            },
            {
                "name": "Data Pattern Analysis",
                "data": [
                    ("TX", b"READ DATA"),
                    ("RX", bytes.fromhex("ABCDEFABCDEFABCDEFABCDEFABCDEF123456"))
                ]
            },
            {
                "name": "Command Sequence",
                "data": [
                    ("TX", b"CMD1"),
                    ("RX", b"OK"),
                    ("TX", b"CMD2"),
                    ("RX", b"OK")
                ]
            }
        ]
        
        for scenario in demo_scenarios:
            if not self.demo_running:
                break
                
            # Add scenario header
            self.root.after(0, self.add_message, 
                          f"\n=== {scenario['name']} ===", "system")
            time.sleep(1)
            
            for direction, data in scenario['data']:
                if not self.demo_running:
                    break
                
                # Display the communication
                timestamp = time.strftime("%H:%M:%S")
                hex_data = data.hex().upper()
                ascii_data = data.decode('utf-8', errors='ignore')
                
                comm_msg = f"[{timestamp}] {direction}: {ascii_data} ({hex_data})"
                tag = "tx" if direction == "TX" else "rx"
                
                self.root.after(0, self.add_message, comm_msg, tag)
                time.sleep(0.5)
                
                # Perform AI analysis
                if direction == "RX":  # Only analyze received data
                    try:
                        result = self.ai_analyzer.analyze_data(data)
                        if result:
                            # Display AI analysis
                            confidence_str = f"({result.confidence:.1%})"
                            ai_msg = f"[{timestamp}] 🤖 AI {confidence_str}: {result.description}"
                            
                            # Determine tag based on analysis type
                            if result.analysis_type == "error":
                                ai_tag = "ai_error"
                            elif result.analysis_type == "protocol":
                                ai_tag = "ai_protocol"
                            elif result.analysis_type == "pattern":
                                ai_tag = "ai_pattern"
                            else:
                                ai_tag = "ai_insight"
                            
                            self.root.after(0, self.add_message, ai_msg, ai_tag)
                            
                            # Add suggestions
                            if result.suggestions:
                                for i, suggestion in enumerate(result.suggestions[:2], 1):
                                    suggestion_msg = f"    💡 {suggestion}"
                                    self.root.after(0, self.add_message, suggestion_msg, "ai_insight")
                                    
                        time.sleep(1)
                        
                    except Exception as e:
                        error_msg = f"    🤖 AI Error: {str(e)}"
                        self.root.after(0, self.add_message, error_msg, "ai_error")
                
                time.sleep(1)
            
            time.sleep(2)  # Pause between scenarios
        
        # Demo completed
        if self.demo_running:
            self.root.after(0, self.add_message, "\n=== Demo Completed ===", "system")
            self.root.after(0, self.stop_demo)
    
    def run(self):
        """Run the demo application"""
        self.root.mainloop()

def main():
    """Main entry point"""
    print("Starting AI Features Demo...")
    demo = AIFeaturesDemo()
    demo.run()

if __name__ == "__main__":
    main()