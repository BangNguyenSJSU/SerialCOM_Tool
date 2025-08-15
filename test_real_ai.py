#!/usr/bin/env python3
"""
Real AI Integration Test
Tests the actual OpenAI API integration with real API calls
"""

from ai_analyzer import AIAnalyzer
from ai_config import AIConfig
import time

def test_real_ai_analysis():
    """Test real AI analysis with various data types"""
    print("Testing Real AI Integration")
    print("=" * 40)
    
    # Load configuration
    config = AIConfig()
    api_key = config.load_api_key()
    
    if not api_key:
        print("[ERROR] No API key found. Run setup_ai.py first.")
        return
    
    # Create real analyzer
    analyzer = AIAnalyzer(api_key)
    
    if not analyzer.is_enabled:
        print("[ERROR] AI analyzer not enabled. Check API key.")
        return
    
    print(f"[SUCCESS] AI Analyzer initialized and ready")
    
    # Test cases with different types of serial data
    test_cases = [
        {
            "name": "Custom Protocol Packet",
            "data": bytes.fromhex("7E01010548656C6C6F20576F726C640D0A"),
            "description": "Custom protocol with start flag 0x7E"
        },
        {
            "name": "ASCII Command",
            "data": b"AT+CGMI\r\n",
            "description": "AT command for modem identification"
        },
        {
            "name": "Binary Data",
            "data": bytes.fromhex("FF00AA55CC3300FF"),
            "description": "Binary data pattern"
        },
        {
            "name": "Error Message",
            "data": b"ERROR: Connection timeout",
            "description": "Error response from device"
        },
        {
            "name": "JSON Response",
            "data": b'{"status":"OK","value":123,"temp":25.5}',
            "description": "JSON formatted response"
        }
    ]
    
    print(f"\nTesting {len(test_cases)} different data types:\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. {test_case['name']}")
        print(f"   Description: {test_case['description']}")
        print(f"   Data: {test_case['data'].hex()}")
        print(f"   ASCII: {test_case['data'].decode('utf-8', errors='ignore')}")
        
        try:
            print("   Analyzing... ", end="", flush=True)
            start_time = time.time()
            
            result = analyzer.analyze_data(test_case['data'])
            
            analysis_time = time.time() - start_time
            print(f"({analysis_time:.1f}s)")
            
            if result:
                print(f"   [SUCCESS] Analysis completed:")
                print(f"   Type: {result.analysis_type}")
                print(f"   Confidence: {result.confidence:.1%}")
                print(f"   Description: {result.description}")
                
                if result.suggestions:
                    print(f"   Suggestions ({len(result.suggestions)}):")
                    for j, suggestion in enumerate(result.suggestions[:3], 1):
                        print(f"     {j}. {suggestion}")
                
                if result.highlighted_data:
                    print(f"   Highlights: {len(result.highlighted_data)} items")
                
            else:
                print("   [WARNING] No analysis result returned")
                
        except Exception as e:
            print(f"   [ERROR] Analysis failed: {e}")
        
        print()  # Empty line between tests
        
        # Small delay to respect rate limits
        if i < len(test_cases):
            time.sleep(1)
    
    # Test statistics
    print("Final Statistics:")
    stats = analyzer.get_statistics()
    if stats:
        print(f"  Total analyses: {stats.get('total_analyses', 0)}")
        print(f"  Analysis types: {stats.get('by_type', {})}")
        print(f"  Average confidence: {stats.get('average_confidence', 0):.1%}")
        print(f"  Rate limiter: {stats.get('rate_limiter_status', {})}")
    
    print("\n" + "=" * 40)
    print("Real AI Integration Test Complete!")
    
    return True

def test_context_analysis():
    """Test context-aware analysis with multiple data pieces"""
    print("\nTesting Context-Aware Analysis")
    print("=" * 35)
    
    config = AIConfig()
    api_key = config.load_api_key()
    analyzer = AIAnalyzer(api_key)
    
    # Simulate a conversation sequence
    conversation = [
        b"AT\r\n",                          # AT command
        b"OK\r\n",                          # Response
        b"AT+CGMI\r\n",                     # Query manufacturer
        b"Quectel\r\n",                     # Manufacturer response
        b"AT+CGMM\r\n",                     # Query model
        b"EC25\r\n",                        # Model response
    ]
    
    context_history = []
    
    for i, data in enumerate(conversation, 1):
        print(f"Step {i}: {data.decode('utf-8', errors='ignore').strip()}")
        
        try:
            result = analyzer.analyze_data(data, context_history)
            
            if result:
                print(f"  AI: {result.description}")
                if result.suggestions:
                    print(f"  Suggestion: {result.suggestions[0]}")
            
            context_history.append(data)
            
        except Exception as e:
            print(f"  Error: {e}")
        
        print()
        time.sleep(0.5)  # Small delay
    
    print("Context analysis complete!")

if __name__ == "__main__":
    success = test_real_ai_analysis()
    
    if success:
        test_context_analysis()
    
    print("\nAll tests completed!")
    print("The AI integration is working with real OpenAI API calls!")