# DL24P Web GUI Documentation

A modern web-based interface for battery testing with real-time monitoring, custom test cycles, and data visualization.

## Quick Start

```bash
# Install dependencies
pip3 install -r requirements.txt

# Configure device (edit ~/.dl24.cfg)
echo "serport=/dev/ttyUSB0" > ~/.dl24.cfg
# or for TCP: echo -e "host=dt24p.local\nport=8888" > ~/.dl24.cfg

# Start web server
./dl24_webserver.py

# Open browser
xdg-open http://localhost:5000
```

## Features

### Real-Time Monitoring
- Live voltage, current, power, capacity, energy display
- Temperature monitoring
- Connection status indicators
- Auto-reconnect on connection loss

### Test Cycles
- **Built-in cycles**: Simple Discharge, Basic Capacity Test, Slow Capacity Test, Fast Screening, Advanced Stress Test
- **Battery presets**: LiPo (3.7V), LiFePO4 (3.2V), NiMH (1.2V), Li-Ion (3.6V), Lead-Acid (2.0V), 18650 (3.7V)
- **Custom Cycle Builder**: Create your own multi-phase test cycles

### Data Visualization
- Real-time discharge curve chart (Plotly.js)
- Selectable plot values: Voltage, Current, Power, Resistance, Temperature
- Zoom, pan, and export chart images

### Data Export
- CSV export with all measured values
- Includes: timestamp, voltage, current, power, resistance, capacity, energy, temperature

### Test Analysis
- Automatic post-test analysis with ratings
- Capacity rating (Excellent/Good/Fair/Poor)
- Resistance rating
- Voltage stability analysis
- Overall battery health assessment

---

## User Interface Overview

### Main Dashboard

The interface is divided into several sections:

```
+------------------+------------------+
|  Test Control    |  System Status   |
|  - Cycle select  |  - Connection    |
|  - Parameters    |  - Serial port   |
|  - Start/Stop    |  - Load status   |
+------------------+------------------+
|  Live Display                       |
|  - Voltage  - Current  - Power      |
|  - Capacity - Energy   - Temp       |
+-------------------------------------+
|  Progress Bar (%)                   |
+-------------------------------------+
|  Discharge Curve Chart              |
+-------------------------------------+
|  Log Messages                       |
+-------------------------------------+
```

---

## Test Control Panel

### Selecting a Test Cycle

1. **Test Cycle Profile dropdown**: Choose from built-in cycles or saved custom cycles
2. **Battery Preset dropdown**: Auto-configures cutoff voltage for battery type
3. **Parameters**:
   - Discharge Current (A)
   - Cutoff Voltage (V)
   - Max Time (minutes) - only for simple cycles

### Starting a Test

1. Select test cycle and parameters
2. Click **▶ Start Test**
3. Monitor progress in real-time
4. Test stops automatically at cutoff voltage or max time
5. Click **⏹ Stop Test** to stop manually

---

## Cycle Builder

Create custom multi-phase test cycles with the Cycle Builder.

### Opening the Cycle Builder

1. Select any cycle from dropdown
2. Click **✏️ Edit Cycle** button
3. The Cycle Builder panel opens

### Adding Phases

Click one of the phase buttons:
- **➕ Discharge**: Add discharge phase with current, cutoff, and max time
- **➕ Rest**: Add rest period (no load)
- **➕ Ramp**: Add current ramp from start to end value

### Configuring Phases

Each phase has configurable parameters:

**Discharge Phase:**
- Current (A): Discharge current
- Cutoff (V): Voltage to stop this phase
- Max Duration (min): Time limit (0 = until cutoff)

**Rest Phase:**
- Rest Duration (sec): How long to wait

**Ramp Phase:**
- Start (A): Starting current
- End (A): Ending current
- Ramp Duration (min): Time to ramp

### Managing Phases

- **▲/▼ buttons**: Reorder phases
- **✕ button**: Delete phase
- **Phase name field**: Rename the phase

### Quick Templates

Click a template button to load a preset configuration:
- **Simple**: Single discharge phase
- **With Rest**: Discharge → Rest → Discharge
- **Stress Test**: High load → Rest → Low load → Ramp → Final discharge

### Saving Custom Cycles

1. Enter a name in "Cycle Name" field
2. Click **✔️ Save & Apply**
3. Cycle is saved to browser localStorage
4. Appears in dropdown with 📁 icon
5. Persists across browser refreshes

### Deleting Custom Cycles

1. Select a saved cycle (with 📁 icon)
2. Click **🗑️ Delete** button
3. Confirm deletion

---

## Live Display

Shows real-time measurements:

| Value | Description |
|-------|-------------|
| Voltage | Current battery/load voltage |
| Current | Actual discharge current |
| Power | Calculated power (V × A) |
| Capacity | Accumulated mAh |
| Energy | Accumulated mWh |
| Temperature | Device temperature |

---

## Chart Controls

### Plot Options

Check/uncheck to show/hide traces:
- Voltage (V)
- Current (A)
- Power (W)
- Resistance (Ω)
- Temperature (°C)

### Chart Interactions

- **Zoom**: Click and drag to zoom
- **Pan**: Hold shift and drag
- **Reset**: Double-click to reset view
- **Export**: Use Plotly toolbar to save as PNG

---

## Data Export

### Export Measurement File

Click **Export Measure File (CSV)** to download all recorded data.

CSV format includes:
```csv
Time (s),Voltage (V),Current (A),Power (W),Resistance (Ohm),Capacity (mAh),Energy (mWh),Temperature (C)
0,4.15,1.00,4.15,4.15,0.28,1.15,25.0
1,4.14,1.00,4.14,4.14,0.56,2.30,25.0
...
```

---

## Test Analysis

After test completion, click **📊 Show Analysis** to see:

### Analysis Results

- **Total Capacity**: mAh discharged
- **Total Energy**: mWh discharged
- **Runtime**: Test duration
- **Average Current**: Mean discharge current
- **Average Resistance**: Calculated internal resistance
- **Voltage Drop**: Start to end voltage difference

### Ratings

- **Capacity Rating**: Based on expected capacity for battery type
- **Resistance Rating**: Low/Normal/High/Very High
- **Voltage Stability**: Excellent/Good/Fair/Poor
- **Overall Rating**: Combined assessment

---

## System Status Panel

### Connection Indicators

- **Device Connection**: Green = connected, Red = disconnected
- **Load Status**: Shows if load is ON/OFF
- **Test Status**: Idle/Running/Completed

### Serial Port Selection

1. Select port from dropdown
2. Click **Connect** to connect
3. Click **🔄** to refresh port list

---

## Configuration

### Config File (~/.dl24.cfg)

```ini
# Serial connection
serport=/dev/ttyUSB0
baudrate=9600

# Or TCP connection
host=dt24p.local
port=8888

# Optional
waitcomm=1    # Wait for device (needed for Bluetooth)
```

### API Endpoints

The web server provides a REST API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Get current device status |
| `/api/start` | POST | Start test (params: current, cutoff, maxTime) |
| `/api/stop` | POST | Stop current test |
| `/api/data` | GET | Get all recorded data points |
| `/api/reset` | POST | Reset energy counters |
| `/api/config` | GET | Get device configuration |
| `/api/ports` | GET | List available serial ports |
| `/api/connect` | POST | Connect to specific port |

---

## Troubleshooting

### "Server not reachable"
- Check if `./dl24_webserver.py` is running
- Verify no firewall blocking port 5000

### "Device not connected"
- Check serial port in ~/.dl24.cfg
- Verify device is powered on
- Try different USB port
- Check `ls /dev/ttyUSB*`

### "REPLY TIMEOUT" errors
- Device may be busy or disconnected
- Check USB cable connection
- Try reconnecting

### WebSocket connection failed
- Fallback polling is enabled automatically
- Check browser console for errors

---

## Simulation Mode

For testing without hardware:

1. Edit `index.html`
2. Set `SIMULATION_MODE = true` (around line 785)
3. Open `index.html` directly in browser
4. Or run: `python3 -m http.server 8000`

---

## Technical Notes

### Browser Requirements
- Modern browser with JavaScript ES6 support
- WebSocket support for real-time updates
- localStorage for saving custom cycles

### Dependencies
- Flask
- Flask-CORS
- Flask-SocketIO
- pyserial

### Known Limitations
- External NTC temperature sensor not readable via protocol
- Only CC (constant current) mode supported
- Complex multi-phase cycles executed sequentially
