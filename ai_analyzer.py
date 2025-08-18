#!/usr/bin/env python3
"""
AI Analyzer Module for SerialCOM Tool
Provides intelligent analysis of serial communication data using OpenAI API.

Note:
    Configure logging in your application as needed. This module uses a
    module-level logger.
"""

import openai
import json
import threading
import time
import queue
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
import logging

# Module-level logger; configure logging in the host application
# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Structure for AI analysis results"""
    analysis_type: str          # "protocol", "error", "pattern", "insight"
    confidence: float           # 0.0 to 1.0
    description: str            # Human-readable analysis
    suggestions: List[str]      # Action suggestions
    highlighted_data: Dict[str, str]  # data_snippet -> color_tag mapping
    timestamp: float            # When analysis was performed
    raw_data: str              # Original data analyzed (hex format)


class AIAnalyzer:
    """Main AI analysis engine using OpenAI API"""
    
    def __init__(self, api_key: str = None):
        """Initialize AI analyzer with API key"""
        self.api_key = api_key
        self.client = None
        self.analysis_queue = queue.Queue()
        self.analysis_history = []
        self.is_enabled = False
        self.rate_limiter = RateLimiter(max_requests_per_minute=60)  # More generous for RX analysis
        
        # Analysis settings
        self.analysis_settings = {
            "model": "gpt-3.5-turbo",
            "max_tokens": 500,
            "temperature": 0.3,
            "analyze_protocol": True,
            "analyze_errors": True,
            "analyze_patterns": True,
            "min_data_length": 1,  # Analyze ANY data (even 1 byte)
            "max_data_length": 1024,  # Maximum bytes per analysis
        }
        
        if api_key:
            self.set_api_key(api_key)
    
    def set_api_key(self, api_key: str) -> bool:
        """Set OpenAI API key and initialize client"""
        try:
            self.api_key = api_key
            self.client = openai.OpenAI(api_key=api_key)
            
            # Test the API key with a minimal request
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=1
            )
            
            self.is_enabled = True
            logger.info("OpenAI API key validated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate API key: {e}")
            self.is_enabled = False
            return False
    
    def analyze_data(self, data: bytes, context_history: List[bytes] = None) -> Optional[AnalysisResult]:
        """Analyze serial communication data"""
        if not self.is_enabled or not self.client:
            return None
            
        # Rate limiting (relaxed for RX data analysis)
        if not self.rate_limiter.can_make_request():
            logger.warning("Rate limit exceeded, skipping analysis")
            return None
        
        # Data validation (removed minimum length restriction)
        # Analyze ALL RX data regardless of length
        if len(data) > self.analysis_settings["max_data_length"]:
            data = data[:self.analysis_settings["max_data_length"]]
        
        try:
            # Determine analysis type based on data characteristics
            analysis_type = self._determine_analysis_type(data)
            
            # Generate appropriate prompt
            prompt = self._generate_analysis_prompt(data, analysis_type, context_history)
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.analysis_settings["model"],
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.analysis_settings["max_tokens"],
                temperature=self.analysis_settings["temperature"]
            )
            
            # Parse response
            result = self._parse_api_response(response, data, analysis_type)
            
            # Store in history
            if result:
                self.analysis_history.append(result)
                if len(self.analysis_history) > 100:  # Keep last 100 analyses
                    self.analysis_history.pop(0)
            
            self.rate_limiter.record_request()
            return result
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return AnalysisResult(
                analysis_type="error",
                confidence=1.0,
                description=f"AI analysis failed: {str(e)}",
                suggestions=["Check API key and network connection"],
                highlighted_data={},
                timestamp=time.time(),
                raw_data=data.hex()
            )
    
    def _determine_analysis_type(self, data: bytes) -> str:
        """Determine the type of analysis needed based on data characteristics"""
        hex_data = data.hex()
        ascii_data = data.decode('utf-8', errors='ignore')
        
        # Check for common protocol patterns
        if data.startswith(b'\x7E'):  # Custom protocol start flag
            return "protocol"
        elif any(char in ascii_data.upper() for char in ['ERROR', 'FAIL', 'INVALID']):
            return "error"
        elif len(data) > 10:  # Longer data might show patterns
            return "pattern"
        elif len(data) <= 3:  # Very short data
            return "insight"
        else:
            return "insight"  # Default for any other data
    
    def _generate_analysis_prompt(self, data: bytes, analysis_type: str, context_history: List[bytes] = None) -> str:
        """Generate appropriate analysis prompt based on data and type"""
        hex_data = data.hex().upper()
        ascii_data = data.decode('utf-8', errors='ignore')
        
        base_info = f"""
Analyze this serial communication data:

Hex: {hex_data}
ASCII: {ascii_data}
Length: {len(data)} bytes
        """
        
        if analysis_type == "protocol":
            return base_info + """
Focus on protocol analysis:
1. Identify the communication protocol (if recognizable)
2. Parse packet structure and fields
3. Identify function codes, addresses, data payload
4. Check for checksums or error detection
5. Assess protocol compliance

Provide JSON response with: type, confidence, description, suggestions, highlights
"""
        
        elif analysis_type == "error":
            return base_info + """
Focus on error detection:
1. Identify potential communication errors
2. Check for malformed packets or data
3. Analyze for protocol violations
4. Look for timing or sequence issues
5. Suggest corrective actions

Provide JSON response with: type, confidence, description, suggestions, highlights
"""
        
        elif analysis_type == "pattern":
            context_str = ""
            if context_history:
                recent_data = [d.hex() for d in context_history[-5:]]
                context_str = f"\nRecent context: {recent_data}"
            
            return base_info + context_str + """
Focus on pattern recognition:
1. Identify data patterns and structures
2. Recognize command-response sequences
3. Detect repeated or periodic data
4. Analyze data relationships
5. Identify trends or anomalies

Provide JSON response with: type, confidence, description, suggestions, highlights
"""
        
        else:  # insight
            return base_info + """
Provide general communication insights:
1. Describe the nature of this data
2. Suggest what type of communication this might be
3. Identify any notable characteristics
4. Provide debugging suggestions if applicable
5. Recommend next steps for analysis

Provide JSON response with: type, confidence, description, suggestions, highlights
"""
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for AI analysis"""
        return """You are an expert in serial communication protocols and embedded systems debugging. 
Analyze ALL serial data regardless of length and provide insights in JSON format with these fields:
- type: analysis type (protocol/error/pattern/insight)
- confidence: confidence level (0.0-1.0)
- description: clear explanation of findings
- suggestions: list of actionable recommendations
- highlights: dict mapping data portions to importance levels (high/medium/low)

IMPORTANT: Analyze even single bytes or very short data. Every piece of serial data has meaning.
Focus on practical debugging assistance. Be concise but thorough."""
    
    def _parse_api_response(self, response, data: bytes, analysis_type: str) -> Optional[AnalysisResult]:
        """Parse OpenAI API response into AnalysisResult"""
        try:
            content = response.choices[0].message.content.strip()
            
            # Try to extract JSON from response
            if content.startswith('```json'):
                content = content[7:-3]  # Remove ```json and ```
            elif content.startswith('```'):
                content = content[3:-3]  # Remove ``` markers
            
            # Parse JSON response
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                # If not valid JSON, create response from raw text
                parsed = {
                    "type": analysis_type,
                    "confidence": 0.5,
                    "description": content[:200] + "..." if len(content) > 200 else content,
                    "suggestions": ["Review the analysis for more details"],
                    "highlights": {}
                }
            
            # Map highlights to color tags
            color_mapping = {
                "high": "ai_error",
                "medium": "ai_protocol", 
                "low": "ai_insight"
            }
            
            highlighted_data = {}
            if "highlights" in parsed and isinstance(parsed["highlights"], dict):
                for data_part, importance in parsed["highlights"].items():
                    color_tag = color_mapping.get(importance, "ai_insight")
                    highlighted_data[data_part] = color_tag
            
            return AnalysisResult(
                analysis_type=parsed.get("type", analysis_type),
                confidence=float(parsed.get("confidence", 0.5)),
                description=parsed.get("description", "Analysis completed"),
                suggestions=parsed.get("suggestions", []),
                highlighted_data=highlighted_data,
                timestamp=time.time(),
                raw_data=data.hex()
            )
            
        except Exception as e:
            logger.error(f"Failed to parse API response: {e}")
            return None
    
    def get_analysis_history(self, limit: int = 10) -> List[AnalysisResult]:
        """Get recent analysis history"""
        return self.analysis_history[-limit:]
    
    def clear_history(self):
        """Clear analysis history"""
        self.analysis_history.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get analysis statistics"""
        if not self.analysis_history:
            return {}
        
        total = len(self.analysis_history)
        by_type = {}
        avg_confidence = 0
        
        for result in self.analysis_history:
            by_type[result.analysis_type] = by_type.get(result.analysis_type, 0) + 1
            avg_confidence += result.confidence
        
        avg_confidence /= total
        
        return {
            "total_analyses": total,
            "by_type": by_type,
            "average_confidence": avg_confidence,
            "rate_limiter_status": self.rate_limiter.get_status()
        }


class RateLimiter:
    """Simple rate limiter for API requests"""
    
    def __init__(self, max_requests_per_minute: int = 20):
        self.max_requests = max_requests_per_minute
        self.requests = []
        self.lock = threading.Lock()
    
    def can_make_request(self) -> bool:
        """Check if we can make a request within rate limits"""
        with self.lock:
            now = time.time()
            # Remove requests older than 1 minute
            self.requests = [req_time for req_time in self.requests if now - req_time < 60]
            return len(self.requests) < self.max_requests
    
    def record_request(self):
        """Record a request timestamp"""
        with self.lock:
            self.requests.append(time.time())
    
    def get_status(self) -> Dict[str, Any]:
        """Get rate limiter status"""
        with self.lock:
            now = time.time()
            self.requests = [req_time for req_time in self.requests if now - req_time < 60]
            return {
                "requests_in_last_minute": len(self.requests),
                "max_requests_per_minute": self.max_requests,
                "can_make_request": len(self.requests) < self.max_requests
            }


# Testing function
def test_ai_analyzer():
    """Test function for AI analyzer"""
    # Test data
    test_data = bytes.fromhex("7E01010548656C6C6F20576F726C640D0A")
    
    print("Testing AI Analyzer...")
    print(f"Test data: {test_data.hex()}")
    print(f"ASCII: {test_data.decode('utf-8', errors='ignore')}")
    
    # Note: Actual testing requires valid API key
    analyzer = AIAnalyzer()
    print(f"Analyzer created, enabled: {analyzer.is_enabled}")


if __name__ == "__main__":
    test_ai_analyzer()