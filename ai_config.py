#!/usr/bin/env python3
"""
AI Configuration Module for SerialCOM Tool
Handles secure storage of API keys and AI analysis settings
"""

import json
import os
import base64
import hashlib
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


class AIConfig:
    """Manages AI configuration and secure API key storage"""
    
    def __init__(self, config_dir: str = None):
        """Initialize AI configuration manager"""
        if config_dir is None:
            config_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "ai_config.json")
        self.key_file = os.path.join(config_dir, ".ai_key")
        
        # Default configuration
        self.default_config = {
            "analysis_settings": {
                "model": "gpt-3.5-turbo",
                "max_tokens": 500,
                "temperature": 0.3,
                "analyze_protocol": True,
                "analyze_errors": True,
                "analyze_patterns": True,
                "min_data_length": 4,
                "max_data_length": 1024,
                "rate_limit_per_minute": 20,
                "auto_analysis": True,
                "analysis_delay_ms": 1000  # Delay between analyses
            },
            "ui_settings": {
                "show_confidence": True,
                "show_suggestions": True,
                "highlight_analysis": True,
                "analysis_history_limit": 100
            },
            "api_settings": {
                "timeout_seconds": 30,
                "retry_attempts": 3,
                "retry_delay_seconds": 2
            }
        }
        
        self.config = self.load_config()
        self._encryption_key = None
    
    def _generate_encryption_key(self, password: str = None) -> bytes:
        """Generate encryption key from password or machine-specific data"""
        if password is None:
            # Use machine-specific information as password
            import platform
            machine_info = f"{platform.node()}{platform.system()}{platform.processor()}"
            password = machine_info.encode('utf-8')
        else:
            password = password.encode('utf-8')
        
        # Create a salt from the config directory path
        salt = hashlib.sha256(self.config_dir.encode('utf-8')).digest()[:16]
        
        # Generate key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def _get_cipher(self) -> Fernet:
        """Get Fernet cipher for encryption/decryption"""
        if self._encryption_key is None:
            self._encryption_key = self._generate_encryption_key()
        return Fernet(self._encryption_key)
    
    def save_api_key(self, api_key: str) -> bool:
        """Encrypt and save API key securely"""
        try:
            if not api_key or not api_key.strip():
                return False
            
            cipher = self._get_cipher()
            encrypted_key = cipher.encrypt(api_key.encode('utf-8'))
            
            # Save to file
            with open(self.key_file, 'wb') as f:
                f.write(encrypted_key)
            
            # Set file permissions (read/write for owner only)
            if os.name != 'nt':  # Unix-like systems
                os.chmod(self.key_file, 0o600)
            
            logger.info("API key saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save API key: {e}")
            return False
    
    def load_api_key(self) -> Optional[str]:
        """Load and decrypt API key"""
        try:
            if not os.path.exists(self.key_file):
                return None
            
            with open(self.key_file, 'rb') as f:
                encrypted_key = f.read()
            
            cipher = self._get_cipher()
            decrypted_key = cipher.decrypt(encrypted_key)
            api_key = decrypted_key.decode('utf-8')
            
            logger.info("API key loaded successfully")
            return api_key
            
        except Exception as e:
            logger.error(f"Failed to load API key: {e}")
            return None
    
    def delete_api_key(self) -> bool:
        """Delete stored API key"""
        try:
            if os.path.exists(self.key_file):
                os.remove(self.key_file)
                logger.info("API key deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to delete API key: {e}")
            return False
    
    def has_api_key(self) -> bool:
        """Check if API key is stored"""
        return os.path.exists(self.key_file)
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Merge with defaults to ensure all keys exist
                merged_config = self.default_config.copy()
                self._deep_merge(merged_config, config)
                return merged_config
            else:
                # Create default config file
                self.save_config(self.default_config)
                return self.default_config.copy()
                
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any] = None) -> bool:
        """Save configuration to file"""
        try:
            if config is None:
                config = self.config
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, separators=(',', ': '))
            
            self.config = config
            logger.info("Configuration saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False
    
    def _deep_merge(self, base: Dict, overlay: Dict):
        """Deep merge overlay dictionary into base dictionary"""
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def get_analysis_settings(self) -> Dict[str, Any]:
        """Get analysis settings"""
        return self.config.get("analysis_settings", self.default_config["analysis_settings"])
    
    def update_analysis_settings(self, settings: Dict[str, Any]) -> bool:
        """Update analysis settings"""
        try:
            self.config["analysis_settings"].update(settings)
            return self.save_config()
        except Exception as e:
            logger.error(f"Failed to update analysis settings: {e}")
            return False
    
    def get_ui_settings(self) -> Dict[str, Any]:
        """Get UI settings"""
        return self.config.get("ui_settings", self.default_config["ui_settings"])
    
    def update_ui_settings(self, settings: Dict[str, Any]) -> bool:
        """Update UI settings"""
        try:
            self.config["ui_settings"].update(settings)
            return self.save_config()
        except Exception as e:
            logger.error(f"Failed to update UI settings: {e}")
            return False
    
    def get_api_settings(self) -> Dict[str, Any]:
        """Get API settings"""
        return self.config.get("api_settings", self.default_config["api_settings"])
    
    def update_api_settings(self, settings: Dict[str, Any]) -> bool:
        """Update API settings"""
        try:
            self.config["api_settings"].update(settings)
            return self.save_config()
        except Exception as e:
            logger.error(f"Failed to update API settings: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults"""
        try:
            self.config = self.default_config.copy()
            return self.save_config()
        except Exception as e:
            logger.error(f"Failed to reset config: {e}")
            return False
    
    def export_config(self, file_path: str, include_sensitive: bool = False) -> bool:
        """Export configuration to file"""
        try:
            export_config = self.config.copy()
            
            if not include_sensitive:
                # Remove sensitive information from export
                if "api_key" in export_config:
                    del export_config["api_key"]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_config, f, indent=2, separators=(',', ': '))
            
            logger.info(f"Configuration exported to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export config: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """Import configuration from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # Validate imported config structure
            if not self._validate_config_structure(imported_config):
                logger.error("Invalid configuration structure")
                return False
            
            # Merge with current config
            self._deep_merge(self.config, imported_config)
            return self.save_config()
            
        except Exception as e:
            logger.error(f"Failed to import config: {e}")
            return False
    
    def _validate_config_structure(self, config: Dict[str, Any]) -> bool:
        """Validate configuration structure"""
        required_sections = ["analysis_settings", "ui_settings", "api_settings"]
        
        for section in required_sections:
            if section not in config:
                continue
            
            if not isinstance(config[section], dict):
                return False
        
        return True
    
    def get_config_status(self) -> Dict[str, Any]:
        """Get configuration status information"""
        return {
            "has_api_key": self.has_api_key(),
            "config_file_exists": os.path.exists(self.config_file),
            "config_file_path": self.config_file,
            "key_file_path": self.key_file,
            "analysis_enabled": self.get_analysis_settings().get("auto_analysis", False)
        }


# Testing function
def test_ai_config():
    """Test AI configuration functionality"""
    print("Testing AI Configuration...")
    
    # Create test config
    config = AIConfig()
    
    # Test API key operations
    test_key = "sk-test-key-12345"
    print(f"Saving test API key...")
    success = config.save_api_key(test_key)
    print(f"Save result: {success}")
    
    print(f"Loading API key...")
    loaded_key = config.load_api_key()
    print(f"Loaded key matches: {loaded_key == test_key}")
    
    # Test configuration
    print(f"Analysis settings: {config.get_analysis_settings()}")
    print(f"Config status: {config.get_config_status()}")
    
    # Cleanup
    config.delete_api_key()
    print("Test completed")


if __name__ == "__main__":
    test_ai_config()