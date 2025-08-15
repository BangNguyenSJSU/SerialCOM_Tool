#!/usr/bin/env python3
"""
Setup script for AI integration
This script configures the AI analyzer with the provided API key
"""

from ai_config import AIConfig
from ai_analyzer import AIAnalyzer

def setup_ai_with_key():
    """Setup AI with the provided API key"""
    # The API key provided by the user
    api_key = "Put your API key here"
    
    print("Setting up AI integration...")
    
    # Create AI config
    config = AIConfig()
    
    # Save the API key
    print("Saving API key...")
    success = config.save_api_key(api_key)
    if success:
        print("[SUCCESS] API key saved successfully")
    else:
        print("[ERROR] Failed to save API key")
        return False
    
    # Test the API key
    print("Testing API connection...")
    analyzer = AIAnalyzer(api_key)
    if analyzer.is_enabled:
        print("[SUCCESS] API connection successful")
        
        # Test with sample data
        print("Testing analysis with sample data...")
        test_data = bytes.fromhex("7E01010548656C6C6F20576F726C640D0A")
        print(f"Test data: {test_data.hex()}")
        print(f"ASCII: {test_data.decode('utf-8', errors='ignore')}")
        
        try:
            result = analyzer.analyze_data(test_data)
            if result:
                print("[SUCCESS] Sample analysis successful")
                print(f"Analysis type: {result.analysis_type}")
                print(f"Confidence: {result.confidence:.1%}")
                print(f"Description: {result.description}")
                if result.suggestions:
                    print("Suggestions:")
                    for suggestion in result.suggestions:
                        print(f"  - {suggestion}")
            else:
                print("[WARNING] Analysis returned no results")
        except Exception as e:
            print(f"[WARNING] Analysis test failed: {e}")
        
    else:
        print("[ERROR] API connection failed")
        return False
    
    print("\n[SUCCESS] AI integration setup complete!")
    print("You can now run the SerialCOM Tool and use AI analysis features.")
    return True

if __name__ == "__main__":
    setup_ai_with_key()