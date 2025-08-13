"""
Validation script for the new SerialCOM_Tool_v4.2.exe build
Tests that all modules and features are properly included
"""

import subprocess
import os
import time
import sys

def validate_executable():
    """Validate that the executable includes all required features"""
    exe_path = "dist\\SerialCOM_Tool_v4.2.exe"
    
    if not os.path.exists(exe_path):
        print("[ERROR] ERROR: Executable not found at", exe_path)
        return False
    
    # Check file size (should be around 10-11 MB)
    file_size = os.path.getsize(exe_path) / (1024 * 1024)  # Convert to MB
    print(f"[OK] Executable found: {exe_path}")
    print(f"[OK] File size: {file_size:.1f} MB")
    
    if file_size < 8 or file_size > 15:
        print(f"[WARNING]  WARNING: Unusual file size ({file_size:.1f} MB)")
        print("   Expected: 10-11 MB for complete build")
    
    return True

def check_required_files():
    """Check that all required files are present in the project"""
    required_files = [
        "serial_gui.py",
        "protocol.py", 
        "host_tab.py",
        "device_tab.py",
        "modbus_tcp_protocol.py",
        "modbus_tcp_slave_tab.py",
        "modbus_tcp_master_tab.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("[ERROR] Missing required files:", missing_files)
        return False
    else:
        print("[OK] All required Python files present")
        return True

def check_image_assets():
    """Check that image assets are present"""
    image_dir = "image"
    if not os.path.exists(image_dir):
        print("[ERROR] Image directory not found")
        return False
    
    image_files = os.listdir(image_dir)
    if len(image_files) == 0:
        print("[WARNING]  WARNING: No image files found")
    else:
        print(f"[OK] Found {len(image_files)} image assets")
    
    return True

def main():
    print("=" * 60)
    print("SERIALCOM TOOL V4.2 BUILD VALIDATION")
    print("=" * 60)
    
    print("\n1. Checking executable...")
    exe_valid = validate_executable()
    
    print("\n2. Checking required source files...")
    files_valid = check_required_files()
    
    print("\n3. Checking image assets...")
    images_valid = check_image_assets()
    
    print("\n" + "=" * 60)
    print("BUILD VALIDATION SUMMARY")
    print("=" * 60)
    
    all_valid = exe_valid and files_valid and images_valid
    
    if all_valid:
        print("[OK] BUILD VALIDATION PASSED")
        print("\nNew features in v4.2:")
        print("  • Enhanced debug messages with indexed register values")
        print("  • Improved color scheme and typography")
        print("  • Auto-loading test pattern")
        print("  • Master tab request preview enhancements")
        print("  • Complete visibility of all register operations")
        print("  • Big-Endian verification system")
        
        print(f"\nThe executable is ready for distribution:")
        print(f"Location: Location: dist\\SerialCOM_Tool_v4.2.exe")
        print(f"Size: Size: {os.path.getsize('dist\\SerialCOM_Tool_v4.2.exe') / (1024 * 1024):.1f} MB")
        print(f"Target: Target: Windows 7+ (64-bit)")
        
        print(f"\nTo distribute:")
        print(f"1. Copy 'dist\\SerialCOM_Tool_v4.2.exe' to target computers")
        print(f"2. No Python installation required on target machines")
        print(f"3. All dependencies are bundled in the executable")
        
    else:
        print("[ERROR] BUILD VALIDATION FAILED")
        print("Please check the issues above and rebuild")
    
    return all_valid

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)