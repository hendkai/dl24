# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

dl24.py is a Python control interface for Atorch DL24P and other Atorch artificial loads (constant-current electronic loads used for battery testing and lab automation). The device communicates over serial (USB-UART, Bluetooth) or TCP (via serial-over-TCP adapters like TasmoCOM).

## Architecture

The codebase uses a hierarchical class structure in a single file (dl24.py):

1. **LowLevelSerPort** (lines 37+) - Serial port communication via pyserial
   - Handles /dev/ttyUSB, /dev/rfcomm (Bluetooth), and pyserial URL handlers
   - Default: 9600 baud, configurable timeout and retries

2. **LowLevelTcpPort** (lines 106+) - Raw TCP socket communication
   - For serial-over-TCP adapters (e.g., ESP8266 running Tasmota)
   - No RFC2217 support, plain TCP only

3. **Instr_Atorch** (lines 214+) - Device protocol implementation
   - Implements two protocols:
     - PX100: Older protocol with fixed prefix/suffix (0xB1 0xB2...0xB6)
     - "Atorch": Newer protocol with checksums (0xFF 0x55 prefix)
   - Handles periodic status updates (1/second) and command-response transactions
   - ADU field indicates device type: 0x01=AC meter, 0x02=DC meter/load (DL24), 0x03=USB meter
   - Protocol details documented in README.md lines 289-453

4. **PowerLoad** (lines 739+) - Command interpreter and high-level interface
   - Parses command-line arguments as a sequence of space-separated commands
   - Config file handling (~/.dl24.cfg or symlink-based naming)
   - Command handlers in handlecommand() method (lines 776+)

## Communication Protocols

### PX100 Protocol (Legacy)
- Commands: 0xB1 0xB2 [cmd] [d1] [d2] 0xB6
- Response: Single byte 0x6F or 7-byte response 0xCA 0xCB [d1] [d2] [d3] 0xCE 0xCF
- Used for set commands and queries

### Atorch Protocol (Modern)
- Packet format: 0xFF 0x55 [type] [ADU] [payload] [checksum]
- Checksum: Sum of bytes from type to payload end, AND 0xFF, XOR 0x44
- Type 0x01: 36-byte periodic status updates (1/second)
- Type 0x02: 8-byte reply to requests
- Type 0x11: 10-byte master requests

## Command System

Commands are executed sequentially from command line. Examples:
- `ON` / `OFF` - Enable/disable load
- `12.5A` or `1250MA` - Set current (supports relative: `+1A`, `-500MA`)
- `10.5VCUT` - Set voltage cutoff
- `QV`, `QA` - Query voltage/current
- `QMV`, `QMA` - Query as integer millivolts/milliamps
- `STATE[:opts]` or `STATEJ[:opts]` - Print state (opts: J=JSON, S=short, T=timestamp, etc.)
- `LISTEN[:opts[:count]]` - Listen to status reports
- `LOOP:[count]` - Repeat subsequent commands
- `SLEEPnn` - Sleep for nn seconds
- `STDIN` - Read commands from stdin
- `VERB[:opts]` - Enable verbose output (P=port, C=communication, D=dataflow, M=commands)

## Configuration

### Config File Location
- Default: ~/.dl24.cfg
- Can use symlinks (dl24a.py → dl24.py) to support multiple devices (~/.dl24a.cfg)
- Generate template: `./dl24.py CFGFILE`

### Config Options
```
serport=/dev/ttyUSB0      # Serial port (takes precedence)
baudrate=9600             # Serial baud rate
waitcomm=1                # Wait for device data before sending (needed for Bluetooth)

host=dt24p.local          # TCP host
port=8888                 # TCP port
```

### Command-Line Config
- `TCP=host[:port]` - Set TCP connection
- `PORT=/dev/ttyX[@baud]` - Set serial port connection
- `WAIT` - Wait for incoming data (required for Bluetooth /dev/rfcomm)
- `ROBUST` - Increase timeouts and retries

## Web GUI

A modern web-based interface is available for battery testing with real-time monitoring and data visualization.

### Components
- **index.html** - Frontend GUI with dark theme, live charts, battery presets, and CSV export
- **dl24_webserver.py** - Flask-based REST API server that bridges the HTML GUI with dl24.py
- **requirements.txt** - Python dependencies (flask, flask-cors, pyserial)

### Starting the Web GUI
```bash
# Install dependencies
pip3 install -r requirements.txt

# Configure device connection in ~/.dl24.cfg
# Example for TCP:
#   host=dt24p.local
#   port=8888
# Example for serial:
#   serport=/dev/ttyUSB0
#   baudrate=9600

# Start the web server
./dl24_webserver.py

# Open browser to http://localhost:5000
```

### Web API Endpoints
- `GET /api/status` - Get current device status and live data
- `POST /api/start` - Start discharge test (params: current, cutoff, maxTime)
- `POST /api/stop` - Stop current test
- `GET /api/data` - Get all recorded data points
- `POST /api/reset` - Reset energy counters
- `GET /api/config` - Get device configuration

### Features
- Real-time voltage, current, power, capacity, energy display
- Battery type presets (LiPo, LiFePO4, NiMH, Li-Ion, Lead-Acid, 18650)
- Live discharge curve visualization
- Automatic test termination on cutoff voltage or max time
- CSV data export
- Test logging with timestamps
- Simulation mode for testing without hardware (set `SIMULATION_MODE = true` in index.html)

## Development Commands

### Testing
No automated tests. Manual testing via command sequences:
```bash
./dl24.py verb:pc state                    # Verbose state query
./dl24.py 0a on loop:50 +20ma sleep1      # Current ramp test
./dl24.py line qmv qma qah qwh            # Multi-value query
```

### Web GUI Testing
```bash
# With hardware connected
./dl24_webserver.py

# Simulation mode (edit index.html, set SIMULATION_MODE = true)
python3 -m http.server 8000
# Then open http://localhost:8000/index.html
```

### Protocol Debugging
- `VERB:PCM` - Show port operations, communication hex dumps, and commands
- `RAWPROTO:xx[:xx:xx:xx:xx]` - Send raw Atorch protocol (cmd + 4 payloads)
- `RAWPX100:xx[:xx:xx]` - Send raw PX100 protocol (cmd + 2 payloads)
- `RAWSEND:xx[:xx...]` - Send raw bytes directly
- `NORETRY` - Disable command retries (speeds up protocol testing)
- `TYPE` - Show detected device type (ADU field)

## Dependencies

### Mandatory (standard library)
- socket, time, select, struct, sys

### Optional (imported as needed)
- serial (pyserial) - For serial port communication
- datetime - For date/time settings
- json - For JSON output format

## Hardware Notes

### DL24P Device
- Constant-current load modes: CC (fully supported), CR/CP/CV (not controllable via protocol)
- Hardware: HC32F030E8PA MCU, RN8209C power sensor, IRFP260 MOSFET
- UART: 9600 bps, N81 (no parity, 1 stop bit)
- Connections: USB-serial (CH340G, non-isolated), Bluetooth, or custom TCP adapter
- MOSFET often fails - be prepared to replace

### Connection Methods
1. USB: CH340G chip, /dev/ttyUSBx (not galvanically isolated!)
2. Bluetooth: /dev/rfcommX (requires WAIT directive)
3. TCP: Serial-over-TCP adapter (e.g., ESP8266 + Tasmota on pins near BT module)

## Test Cycles (18650)

Professional battery testing cycles adapted from TestController procedures:

### Available Cycles
1. **Basic Capacity Test** - 1A discharge, 2-4h, standard verification
2. **Slow Capacity Test** - 0.5A discharge, 5-8h, accurate measurement
3. **Fast Screening** - 2A discharge, 1-2h, quick QC
4. **Advanced Stress Test** - Multi-phase dynamic load (requires CLI)
5. **Cycle Life Test** - Repeated cycles for degradation analysis

### Files
- `test_cycles_18650.json` - Test cycle definitions
- `test_cycle_executor.py` - CLI execution engine
- `TEST_CYCLES_README.md` - Detailed documentation

### Usage
**Web GUI:** Select test cycle from dropdown, auto-configures parameters
**Command Line:** `./test_cycle_executor.py basic_capacity`
**Python:** `from test_cycle_executor import TestCycleExecutor`

## Known Limitations

- Only CC (constant current) mode is accessible via protocol
- Cannot query or set CR/CP/CV modes
- Firmware doesn't support external NTC temperature probe query (as of 2023)
- No device type auto-detection (use ADU field as hint)
- No SCPI support (listed in TODO)
- Advanced multi-phase test cycles require CLI execution (not yet in web GUI)

## Code Style Notes

- Single-file architecture (1264 lines)
- Minimal dependencies philosophy
- Classes use instance variables for state
- Verbose flags controlled via VERB: command
- Port connection persists for entire session unless crashed
- Config filename derived from process name (enables multi-device symlinks)
- Helper functions: getint32/24/16() for byte unpacking (lines 201-208)
- hendrik@tuxedo-os:~/dl24$ ./START_WEB_GUI.sh 
=========================================
  ATorch DL24P Web GUI Starter
=========================================

Checking dependencies...
✅ Dependencies OK

🚀 Starting DL24P Web Server...

   Open your browser to: http://localhost:5000

   Press Ctrl+C to stop

DL24P Web Server starting...
Initializing device connection...
ERROR: unknown serial port or TCP host
Use TCP=<host>[:port] or PORT=[/dev/tty...]
hendrik@tuxedo-os:~/dl24$   Schnelltest, dass alles funktioniert:
  # Zeige aktuellen Status
  ./dl24.py STATE

  # Zeige Spannung und Strom
  ./dl24.py QV QA
Schnelltest,: Befehl nicht gefunden.
{'out': 0, 'V': 0.0}
0.0
0.0
hendrik@tuxedo-os:~/dl24$