#!/usr/bin/env python3
"""
Debug AI Analysis Issue
Check why AI might not be responding to data
"""

from ai_analyzer import AIAnalyzer
from ai_config import AIConfig
import time

def debug_ai_analysis():
    """Debug the AI analysis process"""
    print("Debugging AI Analysis Issue")
    print("=" * 30)
    
    # 1. Check API key and configuration
    config = AIConfig()
    if not config.has_api_key():
        print("[ERROR] No API key found!")
        return
    
    api_key = config.load_api_key()
    print(f"[OK] API key loaded: {api_key[:10]}...{api_key[-10:]}")
    
    # 2. Check analyzer initialization
    analyzer = AIAnalyzer(api_key)
    print(f"[OK] Analyzer enabled: {analyzer.is_enabled}")
    
    # 3. Test with the exact data you sent
    test_data = b"hello world"
    print(f"\nTesting with your data: '{test_data.decode()}'")
    print(f"Data length: {len(test_data)} bytes")
    print(f"Hex: {test_data.hex()}")
    
    # 4. Check minimum length setting
    settings = config.get_analysis_settings()
    min_length = settings.get('min_data_length', 4)
    print(f"Minimum data length setting: {min_length} bytes")
    
    if len(test_data) < min_length:
        print(f"[ISSUE] Data too short! {len(test_data)} < {min_length}")
        print("Solution: Data must be at least 4 bytes")
        return
    else:
        print(f"[OK] Data length sufficient: {len(test_data)} >= {min_length}")
    
    # 5. Test actual analysis
    print("\nTesting AI analysis...")
    try:
        start_time = time.time()
        result = analyzer.analyze_data(test_data)
        end_time = time.time()
        
        print(f"Analysis completed in {end_time - start_time:.1f} seconds")
        
        if result:
            print("[SUCCESS] AI analysis result:")
            print(f"  Type: {result.analysis_type}")
            print(f"  Confidence: {result.confidence:.1%}")
            print(f"  Description: {result.description}")
            if result.suggestions:
                print(f"  Suggestions: {len(result.suggestions)} provided")
                for i, suggestion in enumerate(result.suggestions[:2], 1):
                    print(f"    {i}. {suggestion}")
        else:
            print("[ERROR] No analysis result returned!")
            
    except Exception as e:
        print(f"[ERROR] Analysis failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 6. Check rate limiter
    rate_status = analyzer.rate_limiter.get_status()
    print(f"\nRate Limiter Status:")
    print(f"  Requests in last minute: {rate_status['requests_in_last_minute']}")
    print(f"  Max requests per minute: {rate_status['max_requests_per_minute']}")
    print(f"  Can make request: {rate_status['can_make_request']}")
    
    # 7. Test with longer data that should definitely trigger
    print("\nTesting with longer data...")
    longer_data = b"This is a longer test message that should definitely trigger AI analysis"
    try:
        result2 = analyzer.analyze_data(longer_data)
        if result2:
            print(f"[SUCCESS] Longer data analysis: {result2.analysis_type}")
        else:
            print("[ERROR] Even longer data failed!")
    except Exception as e:
        print(f"[ERROR] Longer data analysis failed: {e}")

def check_gui_integration():
    """Check if the GUI integration might have issues"""
    print("\nChecking GUI Integration...")
    
    try:
        import tkinter as tk
        from serial_gui import SerialGUI
        
        # Create minimal test instance
        root = tk.Tk()
        root.withdraw()
        
        app = SerialGUI(root)
        
        # Check AI status
        print(f"AI enabled variable: {app.ai_enabled.get()}")
        print(f"AI analyzer present: {app.ai_analyzer is not None}")
        if app.ai_analyzer:
            print(f"AI analyzer enabled: {app.ai_analyzer.is_enabled}")
        
        # Check if update_ai_status was called
        app.update_ai_status()
        status_text = app.ai_status.cget('text')
        print(f"AI status display: {status_text}")
        
        # Check data processing method
        if hasattr(app, 'perform_ai_analysis'):
            print("[OK] perform_ai_analysis method exists")
        else:
            print("[ERROR] perform_ai_analysis method missing!")
        
        # Check AI queue
        print(f"AI queue empty: {app.ai_queue.empty()}")
        
        root.destroy()
        
    except Exception as e:
        print(f"[ERROR] GUI check failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_ai_analysis()
    check_gui_integration()
    
    print("\n" + "=" * 50)
    print("DEBUGGING COMPLETE")
    print("\nPossible Issues & Solutions:")
    print("1. Data too short - Try sending longer messages")
    print("2. Analysis delay - Wait 2-3 seconds after sending data")
    print("3. Rate limiting - Don't send data too quickly")
    print("4. Threading issue - Check if background analysis is working")
    print("5. Queue processing - Make sure GUI update loop is running")