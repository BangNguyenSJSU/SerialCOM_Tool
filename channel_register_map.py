"""
Channel Register Mapping Helper
Shows the register addresses and values for all 10 channels
"""

def print_channel_registers():
    """Print out all channel register addresses and their test values"""
    
    print("=" * 80)
    print("CHANNEL REGISTER MAPPING - Test Pattern Values")
    print("=" * 80)
    print()
    print("Each channel uses 3 consecutive registers:")
    print("  - Register N+0: Measured Current (mA)")
    print("  - Register N+1: Measured Voltage (mV)")
    print("  - Register N+2: Channel State (0=OFF, 1=ON, 2=FAULT, 3=OVERCURRENT)")
    print()
    print("-" * 80)
    print(f"{'Channel':<10} {'Base Addr':<12} {'Current Reg':<20} {'Voltage Reg':<20} {'State Reg':<20}")
    print(f"{'':10} {'(Hex)':<12} {'Addr : Value':<20} {'Addr : Value':<20} {'Addr : Value':<20}")
    print("-" * 80)
    
    for ch in range(10):
        # Calculate base address for this channel
        base_addr = 0x1A + (ch * 3)
        
        # Calculate test values (same as in the code)
        current_ma = 1000 + ch * 100  # 1.0A to 1.9A (1000mA to 1900mA)
        voltage_mv = 12000 + ch * 100  # 12.0V to 12.9V (12000mV to 12900mV)
        state = 1 if ch < 5 else 0  # First 5 channels ON, rest OFF
        
        # Current register
        current_addr = base_addr
        current_str = f"0x{current_addr:04X} : {current_ma:5d}mA"
        
        # Voltage register
        voltage_addr = base_addr + 1
        voltage_str = f"0x{voltage_addr:04X} : {voltage_mv:5d}mV"
        
        # State register
        state_addr = base_addr + 2
        state_name = ["OFF", "ON", "FAULT", "OVERCURRENT"][state]
        state_str = f"0x{state_addr:04X} : {state:5d} ({state_name})"
        
        print(f"Channel {ch+1:<3} 0x{base_addr:04X}       {current_str:<20} {voltage_str:<20} {state_str:<20}")
    
    print("-" * 80)
    print()
    print("SUMMARY:")
    print(f"  - Total registers used: {10 * 3} (0x{10*3:04X})")
    print(f"  - Address range: 0x{0x1A:04X} to 0x{0x1A + (10*3) - 1:04X}")
    print(f"  - Channels 1-5: ON state (current flowing)")
    print(f"  - Channels 6-10: OFF state (no current)")
    print()
    print("READING EXAMPLES:")
    print("  - To read Channel 1 data: Read 3 registers from 0x001A")
    print("  - To read Channel 5 data: Read 3 registers from 0x002A")
    print("  - To read all channels: Read 30 registers from 0x001A")
    print()
    print("VALUE CONVERSIONS:")
    print("  - Current: Value in mA (divide by 1000 for Amps)")
    print("  - Voltage: Value in mV (divide by 1000 for Volts)")
    print("  - State: 0=OFF, 1=ON, 2=FAULT, 3=OVERCURRENT")

if __name__ == "__main__":
    print_channel_registers()