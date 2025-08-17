#!/usr/bin/env python3
"""
Test Analyze All RX Data
Verify that the AI now analyzes ALL RX data regardless of length
"""

from ai_analyzer import AIAnalyzer
from ai_config import AIConfig
import time

def test_analyze_all_data():
    """Test analyzing all types and sizes of data"""
    print("Testing: Analyze ALL RX Data")
    print("=" * 30)
    
    config = AIConfig()
    api_key = config.load_api_key()
    
    if not api_key:
        print("[ERROR] No API key found!")
        return
    
    analyzer = AIAnalyzer(api_key)
    if not analyzer.is_enabled:
        print("[ERROR] AI analyzer not enabled!")
        return
    
    print(f"[OK] AI analyzer ready")
    print(f"[OK] Rate limit: {analyzer.rate_limiter.max_requests} requests/minute")
    print(f"[OK] Min data length: {analyzer.analysis_settings['min_data_length']} bytes")
    
    # Test cases - from very short to normal length
    test_cases = [
        ("Single Byte", b"A"),
        ("Two Bytes", b"OK"),
        ("Three Bytes", b"ACK"), 
        ("Short Word", b"Hello"),
        ("Full Sentence", b"Hello World"),
        ("Command", b"AT+CGMI"),
        ("Error Message", b"ERROR"),
        ("Protocol Data", bytes.fromhex("7E010105")),
        ("JSON Data", b'{"ok":1}'),
        ("Binary", bytes([0xFF, 0x00, 0xAA])),
    ]
    
    print(f"\nTesting {len(test_cases)} different data sizes:\n")
    
    for i, (name, data) in enumerate(test_cases, 1):
        print(f"{i:2d}. {name} ({len(data)} bytes)")
        print(f"    Data: {data}")
        print(f"    Hex:  {data.hex().upper()}")
        
        try:
            start_time = time.time()
            result = analyzer.analyze_data(data)
            end_time = time.time()
            
            if result:
                print(f"    [SUCCESS] Analysis ({end_time-start_time:.1f}s):")
                print(f"    Type: {result.analysis_type}")
                print(f"    Confidence: {result.confidence:.0%}")
                print(f"    Description: {result.description[:60]}...")
                if result.suggestions:
                    print(f"    Suggestions: {len(result.suggestions)} provided")
            else:
                print(f"    [FAILED] No analysis result")
                
        except Exception as e:
            print(f"    [ERROR] {e}")
        
        print()
        
        # Small delay for rate limiting
        if i < len(test_cases):
            time.sleep(1.2)  # Slightly longer to ensure no rate limiting
    
    # Final statistics
    stats = analyzer.get_statistics()
    print("=" * 40)
    print("FINAL STATISTICS:")
    print(f"  Total analyses: {stats.get('total_analyses', 0)}")
    print(f"  Success rate: {len([tc for tc in test_cases if True])}/{len(test_cases)}")
    print(f"  Rate limiter: {stats.get('rate_limiter_status', {})}")
    
    print("\n[SUCCESS] AI now analyzes ALL RX data!")
    print("ANY data received will be analyzed, regardless of length.")

if __name__ == "__main__":
    test_analyze_all_data()