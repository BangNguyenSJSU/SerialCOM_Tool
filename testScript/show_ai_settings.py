#!/usr/bin/env python3
"""
Show Current AI Settings
Display the current AI analysis trigger conditions
"""

from ai_config import AIConfig

def show_current_settings():
    """Show current AI analysis settings"""
    print("Current AI Analysis Trigger Conditions")
    print("=" * 42)
    
    config = AIConfig()
    settings = config.get_analysis_settings()
    
    print("🎯 TRIGGER CONDITIONS:")
    print(f"  Minimum data length: {settings.get('min_data_length', 4)} bytes")
    print(f"  Maximum data length: {settings.get('max_data_length', 1024)} bytes")
    print(f"  Analysis delay: {settings.get('analysis_delay_ms', 1000)}ms")
    print(f"  Rate limit: {settings.get('rate_limit_per_minute', 20)} requests/minute")
    
    print("\n🧠 ANALYSIS TYPES:")
    print(f"  Protocol analysis: {'✅' if settings.get('analyze_protocol', True) else '❌'}")
    print(f"  Error detection: {'✅' if settings.get('analyze_errors', True) else '❌'}")
    print(f"  Pattern recognition: {'✅' if settings.get('analyze_patterns', True) else '❌'}")
    print(f"  Auto analysis: {'✅' if settings.get('auto_analysis', True) else '❌'}")
    
    print("\n⚡ API SETTINGS:")
    print(f"  Model: {settings.get('model', 'gpt-3.5-turbo')}")
    print(f"  Max tokens: {settings.get('max_tokens', 500)}")
    print(f"  Temperature: {settings.get('temperature', 0.3)}")
    
    print("\n📋 WHAT TRIGGERS AI ANALYSIS:")
    print("  ✅ ANY RX data ≥ 4 bytes")
    print("  ✅ After 1000ms delay from last analysis")
    print("  ✅ When AI Analysis is enabled")
    print("  ✅ When rate limit allows (20/minute)")
    
    print("\n❌ WHAT DOESN'T TRIGGER:")
    print("  ❌ TX (transmitted) data")
    print("  ❌ Data < 4 bytes")
    print("  ❌ When AI Analysis is disabled")
    print("  ❌ When rate limited")
    print("  ❌ Within 1000ms of previous analysis")

if __name__ == "__main__":
    show_current_settings()