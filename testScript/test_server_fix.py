#!/usr/bin/env python3
"""Test script to verify the Modbus TCP server IP binding fix"""

import socket
import time

def test_server_binding():
    """Test that the server can bind to valid IPs"""
    
    test_cases = [
        ("0.0.0.0", 5020, True, "Bind to all interfaces"),
        ("127.0.0.1", 5021, True, "Bind to localhost"),
        ("169.254.210.91", 5022, False, "Invalid IP (APIPA, not assigned)"),
    ]
    
    print("Testing Modbus TCP Server IP Binding Fix")
    print("=" * 50)
    
    for ip, port, should_succeed, description in test_cases:
        print(f"\nTest: {description}")
        print(f"  IP: {ip}, Port: {port}")
        
        try:
            # Try to create and bind socket
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_socket.bind((ip, port))
            test_socket.listen(1)
            
            if should_succeed:
                print(f"  [SUCCESS] Bound to {ip}:{port}")
            else:
                print(f"  [UNEXPECTED] Should have failed but bound to {ip}:{port}")
            
            test_socket.close()
            
        except OSError as e:
            if e.errno == 10049:  # WSAEADDRNOTAVAIL
                if not should_succeed:
                    print(f"  [EXPECTED] Cannot bind to {ip} (WinError 10049)")
                else:
                    print(f"  [FAILED] Could not bind to {ip} (WinError 10049)")
            else:
                print(f"  [ERROR] {e}")
        
        except Exception as e:
            print(f"  [UNEXPECTED ERROR] {e}")
    
    print("\n" + "=" * 50)
    print("Available IP addresses on this system:")
    
    # Get available IPs
    hostname = socket.gethostname()
    host_ips = socket.gethostbyname_ex(hostname)[2]
    
    print(f"  0.0.0.0 - All interfaces")
    print(f"  127.0.0.1 - Localhost only")
    
    for ip in host_ips:
        if not ip.startswith("169.254"):
            print(f"  {ip} - Network interface")
    
    print("\nRecommendation:")
    print("  Use '0.0.0.0' for testing to accept connections from any interface")
    print("  Use '127.0.0.1' for local-only testing")
    print("  Use a specific IP to bind to a particular network interface")

if __name__ == "__main__":
    test_server_binding()