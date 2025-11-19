#!/bin/bash
# Quick start script for DL24P Web GUI

echo "========================================="
echo "  ATorch DL24P Web GUI Starter"
echo "========================================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    exit 1
fi

# Check if config file exists
if [ ! -f ~/.dl24.cfg ]; then
    echo "⚠️  Config file ~/.dl24.cfg not found!"
    echo ""
    echo "Creating example config file..."
    cat > ~/.dl24.cfg << EOF
# DL24P Configuration
# Uncomment and configure one of the following:

# For TCP connection (e.g., via WiFi adapter):
# host=dt24p.local
# port=8888

# For serial port connection:
# serport=/dev/ttyUSB0
# baudrate=9600

# For Bluetooth connection (remember to add waitcomm):
# serport=/dev/rfcomm0
# baudrate=9600
# waitcomm=1
EOF
    echo "✅ Config file created at ~/.dl24.cfg"
    echo "   Please edit this file and configure your connection!"
    echo ""
    exit 1
fi

# Check if dependencies are installed
echo "Checking dependencies..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask not installed. Installing dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies!"
        exit 1
    fi
fi

echo "✅ Dependencies OK"
echo ""

# Make server executable
chmod +x dl24_webserver.py

# Start the server
echo "🚀 Starting DL24P Web Server..."
echo ""
echo "   Open your browser to: http://localhost:5000"
echo ""
echo "   Press Ctrl+C to stop"
echo ""

./dl24_webserver.py
