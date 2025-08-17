#!/usr/bin/env python3
"""
Full Application Test with AI
Tests the complete SerialCOM Tool with AI integration
"""

import tkinter as tk
import time
import threading
from serial_gui import SerialGUI
from ai_analyzer import AnalysisResult

def simulate_serial_data_with_ai(app):
    """Simulate serial data reception to test AI analysis"""
    print("Simulating serial communication with AI analysis...")
    
    # Wait a moment for GUI to be ready
    time.sleep(2)
    
    # Test data samples
    test_samples = [
        {
            "name": "AT Command Sequence",
            "data": [
                b"AT\r\n",
                b"OK\r\n", 
                b"AT+CGMI\r\n",
                b"Quectel\r\n"
            ]
        },
        {
            "name": "Custom Protocol",
            "data": [
                bytes.fromhex("7E01010548656C6C6F20576F726C640D0A"),
                bytes.fromhex("7E0181050548656C6C6F15A3")
            ]
        },
        {
            "name": "Error Condition",
            "data": [
                b"GET STATUS\r\n",
                b"ERROR: Device not ready\r\n"
            ]
        }
    ]
    
    for sample in test_samples:
        print(f"\nTesting: {sample['name']}")
        
        for data in sample['data']:
            # Simulate data reception
            app.data_queue.put(('rx', data))
            
            # Small delay between messages
            time.sleep(1.5)
        
        # Longer delay between test sequences
        time.sleep(3)
    
    print("Simulation complete!")

def test_ai_settings_dialog(app):
    """Test the AI settings dialog"""
    print("Testing AI Settings Dialog...")
    
    def open_settings():
        try:
            app.open_ai_settings()
            print("AI Settings dialog opened successfully!")
        except Exception as e:
            print(f"Error opening AI settings: {e}")
    
    # Schedule the settings dialog to open after a delay
    app.root.after(1000, open_settings)

def test_application_with_ai():
    """Test the complete application with AI features"""
    print("Starting Full Application Test with AI Integration")
    print("=" * 55)
    
    # Create the main application
    root = tk.Tk()
    
    try:
        app = SerialGUI(root)
        
        # Check AI components are present
        print("Checking AI Integration:")
        print(f"  AI Config: {'OK' if hasattr(app, 'ai_config') else 'MISSING'}")
        print(f"  AI Toggle Button: {'OK' if hasattr(app, 'ai_toggle_btn') else 'MISSING'}")
        print(f"  AI Status Label: {'OK' if hasattr(app, 'ai_status') else 'MISSING'}")
        print(f"  AI Queue: {'OK' if hasattr(app, 'ai_queue') else 'MISSING'}")
        
        # Check AI status
        app.update_ai_status()
        print(f"  AI Status: {app.ai_status.cget('text')}")
        
        # Test AI text tags
        ai_tags = [tag for tag in app.rx_display.tag_names() if tag.startswith('ai_')]
        print(f"  AI Tags: {len(ai_tags)} configured ({', '.join(ai_tags)})")
        
        # Enable AI analysis for testing
        if app.ai_config.has_api_key():
            print("\nEnabling AI Analysis for testing...")
            try:
                # Try to enable AI
                if hasattr(app, 'ai_analyzer') and app.ai_analyzer:
                    app.ai_enabled.set(True)
                    app.update_ai_status()
                    print("  AI Analysis enabled!")
                    
                    # Start simulation in background
                    sim_thread = threading.Thread(
                        target=simulate_serial_data_with_ai, 
                        args=(app,), 
                        daemon=True
                    )
                    sim_thread.start()
                    
                else:
                    print("  AI Analyzer not initialized")
            except Exception as e:
                print(f"  Error enabling AI: {e}")
        else:
            print("  No API key configured")
        
        # Test the settings dialog
        test_ai_settings_dialog(app)
        
        print("\nApplication launched successfully!")
        print("You should see:")
        print("  1. AI Analysis section in the Data Display tab")
        print("  2. Enable/Disable AI Analysis button")
        print("  3. AI Settings button")
        print("  4. API Key status indicator")
        print("  5. Simulated data with AI analysis (if API key is configured)")
        print("\nClose the application window to end the test.")
        
        # Run the application
        root.mainloop()
        
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nFull Application Test Complete!")

if __name__ == "__main__":
    test_application_with_ai()