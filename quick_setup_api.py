#!/usr/bin/env python3
"""
Quick API Key Setup
Properly configures the API key and verifies the setup
"""

from ai_config import AIConfig
from ai_analyzer import AIAnalyzer

def setup_api_key():
    """Setup API key properly"""
    print("Quick API Key Setup")
    print("=" * 20)
    
    # Your API key
    api_key = "Your API key here"
    
    config = AIConfig()
    
    print("1. Saving API key...")
    success = config.save_api_key(api_key)
    if success:
        print("   [SUCCESS] API key saved")
    else:
        print("   [ERROR] Failed to save API key")
        return False
    
    print("2. Verifying API key...")
    loaded_key = config.load_api_key()
    if loaded_key == api_key:
        print("   [SUCCESS] API key verified")
    else:
        print("   [ERROR] API key verification failed")
        return False
    
    print("3. Testing AI analyzer...")
    analyzer = AIAnalyzer(api_key)
    if analyzer.is_enabled:
        print("   [SUCCESS] AI analyzer working")
    else:
        print("   [ERROR] AI analyzer failed")
        return False
    
    print("4. Testing with sample data...")
    try:
        result = analyzer.analyze_data(b"hello world test message")
        if result:
            print(f"   [SUCCESS] Analysis: {result.analysis_type} - {result.description[:50]}...")
        else:
            print("   [WARNING] No analysis result")
    except Exception as e:
        print(f"   [ERROR] Analysis failed: {e}")
        return False
    
    print("\n" + "=" * 40)
    print("SETUP COMPLETE!")
    print("\nNow do this:")
    print("1. Launch the application: python serial_gui.py")
    print("2. Go to Data Display tab")
    print("3. Click 'Enable AI Analysis'")
    print("4. Send some test data")
    print("5. You should see AI analysis appear!")
    
    return True

if __name__ == "__main__":
    setup_api_key()