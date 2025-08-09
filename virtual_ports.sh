#!/bin/bash

echo "============================================"
echo "Creating Virtual Serial Port Pair"
echo "============================================"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🔴 Stopping virtual ports..."
    if [[ ! -z "$SOCAT_PID" ]]; then
        kill $SOCAT_PID 2>/dev/null
    fi
    echo "✅ Virtual ports stopped"
    exit 0
}

# Set up trap to handle Ctrl+C
trap cleanup SIGINT SIGTERM

# Run socat in background and capture the port names
echo "🔧 Starting socat process..."
socat -d -d pty,raw,echo=0 pty,raw,echo=0 2>&1 | while read line; do
    if [[ $line == *"PTY is"* ]]; then
        port=$(echo "$line" | grep -o '/dev/ttys[0-9]*')
        echo "✅ Created virtual port: $port"
    fi
done &

SOCAT_PID=$!

# Wait for ports to be created
sleep 2

echo ""
echo "============================================"
echo "Virtual ports are now active!"
echo "============================================"
echo ""
echo "📋 TESTING INSTRUCTIONS:"
echo "1. Open FIRST terminal window:"
echo "   python serial_gui.py"
echo "   → Connect to the FIRST port shown above"
echo "   → Go to 'Device (Slave)' tab"
echo "   → Set device address to 1"
echo "   → Click 'Load Test Pattern'"
echo ""
echo "2. Open SECOND terminal window:"
echo "   python serial_gui.py"
echo "   → Connect to the SECOND port shown above"
echo "   → Go to 'Host (Master)' tab"
echo "   → Try sending commands to device address 1"
echo ""
echo "🔴 Press Ctrl+C to stop virtual ports"
echo ""

# Keep running until interrupted
wait $SOCAT_PID