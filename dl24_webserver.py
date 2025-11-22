#!/usr/bin/python3
"""
DL24P Web Server - Flask-based REST API for the HTML GUI
Bridges the index.html frontend with dl24.py backend
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
import time
import sys
import os

# Import the dl24 classes
from dl24 import LowLevelSerPort, LowLevelTcpPort, Instr_Atorch, PowerLoad

# Import serial port listing
try:
    from serial.tools import list_ports
except ImportError:
    list_ports = None

app = Flask(__name__, static_folder='.')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Thread lock for serial port access
serial_lock = threading.Lock()

# Global state
test_state = {
    'running': False,
    'start_time': None,
    'data_points': [],
    'current_data': {
        'voltage': 0.0,
        'current': 0.0,
        'power': 0.0,
        'resistance': 0.0,
        'capacity': 0,
        'energy': 0,
        'temperature': 0,
        'runtime': 0
    }
}

# PowerLoad instance
pload = None
connection_health = {
    'last_successful_query': 0,
    'consecutive_failures': 0,
    'max_consecutive_failures': 5,
    'connection_reset_count': 0,
    'last_reset_time': 0,
    'min_reset_interval': 30,  # Seconds between connection resets
    'update_interval': 2.0,  # Start with 2 seconds, increase if problems persist
    'max_update_interval': 10.0,  # Maximum update interval
    'is_connected': False,
    'last_error': None,
    'reconnect_attempts': 0
}
update_thread = None
test_thread = None
last_heartbeat = 0
HEARTBEAT_TIMEOUT = 15  # Seconds without heartbeat before auto-stop

def init_device():
    """Initialize the DL24P device connection"""
    global pload, test_state, connection_health
    try:
        if pload is None:
            pload = PowerLoad()
            pload.verbrun = True  # Enable verbose output for debugging

        # Read config file - use dl24.cfg instead of dl24_webserver.cfg
        if not pload.readconf(name='dl24'):
            print('Warning: Could not read config file, using defaults', file=sys.stderr)

        print(f'Config loaded: {pload.conf}', file=sys.stderr)

        # Check if we have connection settings
        if not pload.conf.get('serport') and not pload.conf.get('host'):
            print('No serial port or host configured', file=sys.stderr)
            print('Please configure connection in the web interface', file=sys.stderr)
            return False

        # Initialize port - catch errors gracefully
        try:
            pload.initport()
            pload.instr.connect()
        except Exception as port_error:
            print(f'Could not connect to port: {port_error}', file=sys.stderr)
            connection_health['last_error'] = str(port_error)
            return False

        connection_health['is_connected'] = True
        connection_health['last_error'] = None
        connection_health['consecutive_failures'] = 0

        # Wait for initial data if needed
        if 'waitcomm' in pload.conf and pload.conf['waitcomm'] == '1':
            print('Waiting for initial communication from device...', file=sys.stderr)
            timeout = 10
            start = time.time()
            while not pload.instr.gotupdate():
                if time.time() - start > timeout:
                    print('Warning: Timeout waiting for device data', file=sys.stderr)
                    break
                time.sleep(0.05)
                pload.instr.recvdata()

        # Detect if device is already running a test
        try:
            # Get device state to check if load is already on
            device_state = pload.instr.cmd_readstate(energy=True, limits=True, temp=True, short=False)
            load_on = device_state.get('out', 0)

            if load_on == 1:
                print('Device load is already ON - detecting as running test', file=sys.stderr)
                test_state['running'] = True
                test_state['start_time'] = time.time()  # Start timing from now
                test_state['data_points'] = []  # Reset data points for this session
                print('Test state synchronized with device state', file=sys.stderr)
            else:
                test_state['running'] = False
                test_state['start_time'] = None
                print('Device load is OFF - ready to start new test', file=sys.stderr)

        except Exception as e:
            print(f'Warning: Could not detect device running state: {e}', file=sys.stderr)
            test_state['running'] = False
            test_state['start_time'] = None

        return True
    except Exception as e:
        print(f'Error initializing device: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc()
        connection_health['is_connected'] = False
        connection_health['last_error'] = str(e)
        return False

def reconnect_device():
    """Attempt to reconnect to the device"""
    global pload, connection_health

    connection_health['reconnect_attempts'] += 1
    print(f'🔄 Reconnect attempt #{connection_health["reconnect_attempts"]}', file=sys.stderr)

    try:
        # Close existing connection if any
        if pload and pload.instr and hasattr(pload.instr, 'comm') and pload.instr.comm:
            try:
                pload.instr.close()
            except:
                pass

        # Check if serial port still exists
        if pload and 'serport' in pload.conf:
            import os
            port_path = pload.conf['serport']
            if not os.path.exists(port_path):
                connection_health['is_connected'] = False
                connection_health['last_error'] = f'Serial port {port_path} not found'
                print(f'❌ Serial port {port_path} not found', file=sys.stderr)
                return False

        # Reinitialize
        if init_device():
            print(f'✅ Reconnection successful', file=sys.stderr)
            connection_health['reconnect_attempts'] = 0
            return True
        else:
            return False

    except Exception as e:
        connection_health['is_connected'] = False
        connection_health['last_error'] = str(e)
        print(f'❌ Reconnection failed: {e}', file=sys.stderr)
        return False

def manage_connection_health(success):
    """Manage connection health and adaptive update intervals"""
    global connection_health, pload

    current_time = time.time()

    if success:
        connection_health['last_successful_query'] = current_time
        connection_health['consecutive_failures'] = 0
        connection_health['is_connected'] = True
        connection_health['last_error'] = None
        # Reduce update interval gradually on success
        if connection_health['update_interval'] > 3.0:
            connection_health['update_interval'] = max(3.0, connection_health['update_interval'] - 0.5)
    else:
        connection_health['consecutive_failures'] += 1
        print(f'⚠️ Connection failure #{connection_health["consecutive_failures"]}', file=sys.stderr)

        # Increase update interval on failures
        connection_health['update_interval'] = min(
            connection_health['max_update_interval'],
            connection_health['update_interval'] + 0.5
        )

        # Mark as disconnected after multiple failures
        if connection_health['consecutive_failures'] >= 3:
            connection_health['is_connected'] = False

        # Attempt connection reset if too many failures
        if (connection_health['consecutive_failures'] >= connection_health['max_consecutive_failures'] and
            current_time - connection_health['last_reset_time'] > connection_health['min_reset_interval']):

            print(f'🔄 Attempting automatic reconnection after {connection_health["consecutive_failures"]} failures', file=sys.stderr)
            connection_health['last_reset_time'] = current_time

            # Use reconnect_device for proper reconnection
            if reconnect_device():
                connection_health['connection_reset_count'] += 1
                print(f'✅ Auto-reconnection successful (reset #{connection_health["connection_reset_count"]})', file=sys.stderr)
            else:
                print(f'❌ Auto-reconnection failed', file=sys.stderr)

def update_data():
    """Background thread to continuously update device data"""
    global test_state, pload
    last_log_time = 0
    last_device_state = {}

    while True:
        if pload and pload.instr and pload.instr.comm:
            try:
                with serial_lock:
                    # Update data from device
                    pload.instr.recvdata()

                    # Get complete device state
                    device_state = pload.instr.cmd_readstate(energy=True, limits=True, temp=True, short=False)
                    load_on = device_state.get('out', 0)

                    # Log state changes (every 30 seconds to avoid spam)
                current_time = time.time()
                if current_time - last_log_time > 30:
                    if (device_state != last_device_state or
                        test_state['running'] != (load_on == 1 and test_state['current_data'].get('current', 0) > 0.01)):

                        print(f'=== DEVICE STATUS UPDATE ===', file=sys.stderr)
                        print(f'Load status: {load_on} ({"ON" if load_on else "OFF"})', file=sys.stderr)
                        print(f'Output voltage: {device_state.get("V", 0) or 0:.3f}V', file=sys.stderr)
                        print(f'Output current: {device_state.get("A", 0) or 0:.3f}A', file=sys.stderr)
                        print(f'Set current: {device_state.get("Iset", 0) or 0:.3f}A', file=sys.stderr)
                        print(f'Capacity: {device_state.get("Ah", 0) or 0:.3f}Ah', file=sys.stderr)
                        print(f'Energy: {device_state.get("Wh", 0) or 0:.3f}Wh', file=sys.stderr)
                        print(f'Temperature: {device_state.get("temp", 0) or 0:.1f}°C', file=sys.stderr)
                        print(f'Cutoff voltage: {device_state.get("Vcut", 0) or 0:.3f}V', file=sys.stderr)
                        print(f'Test running: {test_state["running"]}', file=sys.stderr)

                        last_device_state = device_state.copy()
                        last_log_time = current_time
                        print(f'=== END STATUS UPDATE ===', file=sys.stderr)

                # Enhanced communication error handling
                device_state_str = str(device_state)
                has_comm_errors = (
                    'REPLY TIMEOUT' in device_state_str or
                    'ERR:' in device_state_str or
                    'device reports readiness to read but returned no data' in device_state_str or
                    'cannot send command' in device_state_str
                )

                if has_comm_errors:
                    print(f'⚠️ Communication issue detected - checking device responsiveness', file=sys.stderr)
                    manage_connection_health(False)

                    # Try to recover connection
                    if pload and pload.instr and hasattr(pload.instr, 'comm') and pload.instr.comm:
                        try:
                            # Try to reset communication
                            pload.instr.comm.flushInput()
                            pload.instr.comm.flushOutput()
                            time.sleep(0.2)  # Slightly longer delay
                            print(f'🔄 Communication reset attempted', file=sys.stderr)
                        except Exception as reset_error:
                            print(f'❌ Communication reset failed: {reset_error}', file=sys.stderr)

                # Synchronize test state with device state
                # Only sync if we have valid data (no comm errors)
                if not has_comm_errors:
                    # If device shows load ON but we think test is not running, update our state
                    if load_on == 1 and not test_state['running']:
                        print(f'🔄 STATE SYNC: Device load turned ON - auto-detecting as running test', file=sys.stderr)
                        print(f'   Load: ON, Current: {test_state["current_data"].get("current", 0):.3f}A', file=sys.stderr)
                        test_state['running'] = True
                        if not test_state['start_time']:
                            test_state['start_time'] = time.time()
                            test_state['data_points'] = []  # Reset for new session
                            print(f'   Started new test session at {time.strftime("%H:%M:%S")}', file=sys.stderr)
                    # If device shows load OFF but we think test is running, update our state
                    elif load_on == 0 and test_state['running']:
                        print(f'🔄 STATE SYNC: Device load turned OFF - auto-stopping test tracking', file=sys.stderr)
                        final_runtime = test_state['current_data'].get('runtime', 0)
                        final_capacity = test_state['current_data'].get('capacity', 0)
                        print(f'   Test ended after {final_runtime:.1f}s, {final_capacity:.0f}mAh', file=sys.stderr)
                        test_state['running'] = False
                        test_state['start_time'] = None

                # Use data from device_state (already fetched inside serial_lock)
                # This avoids race conditions and duplicate serial queries
                voltage = device_state.get('V', 0) or 0
                current = device_state.get('A', 0) or 0
                capacity = (device_state.get('Ah', 0) or 0) * 1000  # Convert to mAh
                energy = (device_state.get('Wh', 0) or 0) * 1000    # Convert to mWh
                temp = device_state.get('temp', 0) or 0

                # Calculate resistance (R = V/I, avoid division by zero)
                resistance = (voltage / current) if current > 0.001 else 0.0  # Ω, threshold 1mA

                # Update current data
                test_state['current_data'] = {
                    'voltage': voltage,
                    'current': current,
                    'power': voltage * current,
                    'resistance': resistance,
                    'capacity': capacity,
                    'energy': energy,
                    'temperature': temp,
                    'runtime': (time.time() - test_state['start_time']) if test_state['start_time'] else 0
                }

                # Emit WebSocket update
                try:
                    socketio.emit('status_update', {
                        'connected': connection_health['is_connected'],
                        'running': test_state['running'],
                        'load_on': load_on,
                        'cutoff_voltage': device_state.get('Vcut', 0.0),
                        'set_current': device_state.get('Iset', 0.0),
                        'data': test_state['current_data'],
                        'connection_health': {
                            'consecutive_failures': connection_health['consecutive_failures'],
                            'last_error': connection_health['last_error'],
                            'reconnect_attempts': connection_health['reconnect_attempts'],
                            'update_interval': connection_health['update_interval']
                        }
                    })
                except Exception as ws_error:
                    pass  # WebSocket emit failures are non-critical

                # If test is running, record data point
                if test_state['running']:
                    test_state['data_points'].append({
                        'time': test_state['current_data']['runtime'],
                        'timestamp': time.time(),  # Add Unix timestamp
                        'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),  # Add readable datetime string
                        'voltage': voltage,
                        'current': current,
                        'capacity': capacity
                    })

                    # Successful data update - manage connection health
                    manage_connection_health(True)

            except Exception as e:
                print(f'Error updating data: {e}', file=sys.stderr)
                manage_connection_health(False)
                # Add small delay on errors to prevent rapid-fire error attempts
                time.sleep(0.5)

        # Use adaptive update interval based on connection health
        time.sleep(connection_health['update_interval'])

def test_monitor(cutoff_voltage, max_time):
    """Monitor test and stop when conditions are met"""
    global test_state, pload

    start_time = time.time()
    last_status_log = 0
    voltage_samples = []
    current_samples = []

    print(f'=== TEST MONITOR STARTED ===', file=sys.stderr)
    print(f'Monitoring cutoff: {cutoff_voltage}V, Max time: {max_time}s', file=sys.stderr)
    print(f'Monitoring started at: {time.strftime("%H:%M:%S")}', file=sys.stderr)

    # Wait a moment for data to stabilize after reset
    time.sleep(1)

    while test_state['running']:
        current_voltage = test_state['current_data']['voltage']
        current_current = test_state['current_data']['current']
        elapsed_time = time.time() - start_time

        # Collect samples for trend analysis
        voltage_samples.append(current_voltage)
        current_samples.append(current_current)

        # Keep only last 60 samples (1 minute at 1s interval)
        if len(voltage_samples) > 60:
            voltage_samples.pop(0)
            current_samples.pop(0)

        # Log status every 30 seconds or when significant changes occur
        current_time = time.time()
        if current_time - last_status_log > 30:
            if len(voltage_samples) >= 10:
                avg_voltage = sum(voltage_samples[-10:]) / 10
                avg_current = sum(current_samples[-10:]) / 10
                voltage_trend = voltage_samples[-1] - voltage_samples[0] if len(voltage_samples) > 1 else 0

                print(f'📊 TEST STATUS (t+{elapsed_time:.0f}s):', file=sys.stderr)
                print(f'   V: {avg_voltage:.3f}V (trend: {voltage_trend:+.3f}V)', file=sys.stderr)
                print(f'   I: {avg_current:.3f}A', file=sys.stderr)
                print(f'   Capacity: {test_state["current_data"]["capacity"]:.0f}mAh', file=sys.stderr)
                print(f'   Energy: {test_state["current_data"]["energy"]:.0f}mWh', file=sys.stderr)
                print(f'   Resistance: {test_state["current_data"]["resistance"]:.3f}Ω', file=sys.stderr)

                last_status_log = current_time

        # Only check cutoff if we have valid voltage data (> 1V)
        if current_voltage > 1.0:
            # Check cutoff conditions
            if current_voltage <= cutoff_voltage:
                print(f'🛑 CUTOFF REACHED: {current_voltage:.3f}V <= {cutoff_voltage}V', file=sys.stderr)
                print(f'   Test duration: {elapsed_time:.1f}s', file=sys.stderr)
                print(f'   Final capacity: {test_state["current_data"]["capacity"]:.0f}mAh', file=sys.stderr)
                print(f'   Final energy: {test_state["current_data"]["energy"]:.0f}mWh', file=sys.stderr)
                stop_test_internal()
                break

            if max_time > 0 and elapsed_time >= max_time:
                print(f'⏰ TIME LIMIT REACHED: {elapsed_time:.1f}s >= {max_time}s', file=sys.stderr)
                print(f'   Final voltage: {current_voltage:.3f}V', file=sys.stderr)
                print(f'   Final capacity: {test_state["current_data"]["capacity"]:.0f}mAh', file=sys.stderr)
                print(f'   Final energy: {test_state["current_data"]["energy"]:.0f}mWh', file=sys.stderr)
                stop_test_internal()
                break

            # Check heartbeat timeout (browser closed)
            if last_heartbeat > 0 and time.time() - last_heartbeat > HEARTBEAT_TIMEOUT:
                print(f'🔌 HEARTBEAT TIMEOUT: No browser connection for {HEARTBEAT_TIMEOUT}s', file=sys.stderr)
                print(f'   Auto-stopping test for safety', file=sys.stderr)
                print(f'   Final voltage: {current_voltage:.3f}V', file=sys.stderr)
                print(f'   Final capacity: {test_state["current_data"]["capacity"]:.0f}mAh', file=sys.stderr)
                stop_test_internal()
                break

            # Warn if voltage is approaching cutoff
            if current_voltage <= cutoff_voltage + 0.2:
                print(f'⚠️ LOW VOLTAGE WARNING: {current_voltage:.3f}V (cutoff: {cutoff_voltage}V)', file=sys.stderr)

        time.sleep(1)

    print(f'=== TEST MONITOR ENDED ===', file=sys.stderr)

def stop_test_internal():
    """Internal function to stop test (called from monitor thread)"""
    global test_state, pload

    print(f'⏹️ EXECUTING TEST STOP...', file=sys.stderr)

    if pload and pload.instr and pload.instr.comm:
        try:
            # Read final values before turning off
            final_voltage = pload.instr.cmd_getvolt()
            final_current = pload.instr.cmd_getamp()
            final_capacity = pload.instr.cmd_getah(div=1)
            final_energy = pload.instr.cmd_getwh(div=1)

            print(f'Sending command: Turn load OFF', file=sys.stderr)
            pload.instr.cmd_setonoff(0)

            # Verify load is actually off
            time.sleep(0.2)
            load_status = pload.instr.cmd_getonoff()
            print(f'✓ Load turned OFF, status: {load_status} (0=OFF)', file=sys.stderr)

            print(f'📋 FINAL TEST SUMMARY:', file=sys.stderr)
            print(f'   Final voltage: {final_voltage:.3f}V', file=sys.stderr)
            print(f'   Final current: {final_current:.3f}A', file=sys.stderr)
            print(f'   Total capacity: {final_capacity:.0f}mAh', file=sys.stderr)
            print(f'   Total energy: {final_energy:.0f}mWh', file=sys.stderr)
            print(f'   Test duration: {test_state["current_data"].get("runtime", 0):.1f}s', file=sys.stderr)

        except Exception as e:
            print(f'✗ Error stopping test: {e}', file=sys.stderr)
    else:
        print(f'✗ Device not available for stopping test', file=sys.stderr)

    test_state['running'] = False
    test_state['start_time'] = None  # Reset start time to stop runtime calculation
    print(f'✓ Test state cleared', file=sys.stderr)

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('.', 'index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current device status"""
    device_state = {}

    if pload and pload.instr and pload.instr.comm:
        try:
            with serial_lock:
                # Get complete device state using cmd_readstate()
                device_state = pload.instr.cmd_readstate(energy=True, limits=True, temp=True, short=False)
        except Exception as e:
            print(f'Error getting device status: {e}', file=sys.stderr)
            connection_health['last_error'] = str(e)

    return jsonify({
        'connected': connection_health['is_connected'],
        'running': test_state['running'],
        'load_on': device_state.get('out', 0),
        'cutoff_voltage': device_state.get('Vcut', 0.0),
        'set_current': device_state.get('Iset', 0.0),
        'data': test_state['current_data'],
        'connection_health': {
            'consecutive_failures': connection_health['consecutive_failures'],
            'last_error': connection_health['last_error'],
            'reconnect_attempts': connection_health['reconnect_attempts'],
            'update_interval': connection_health['update_interval']
        }
    })

@app.route('/api/reconnect', methods=['POST'])
def api_reconnect():
    """Manually trigger device reconnection"""
    global test_state

    if test_state['running']:
        return jsonify({
            'success': False,
            'error': 'Cannot reconnect while test is running'
        }), 400

    print('📡 Manual reconnection requested', file=sys.stderr)

    if reconnect_device():
        return jsonify({
            'success': True,
            'message': 'Reconnection successful'
        })
    else:
        return jsonify({
            'success': False,
            'error': connection_health['last_error'] or 'Reconnection failed'
        }), 500

@app.route('/api/start', methods=['POST'])
def start_test():
    """Start a discharge test"""
    global test_state, pload, test_thread

    if test_state['running']:
        return jsonify({'success': False, 'error': 'Test already running'}), 400

    if not pload or not pload.instr or not pload.instr.comm:
        return jsonify({'success': False, 'error': 'Device not connected'}), 400

    data = request.json
    current = float(data.get('current', 1.0))
    cutoff_voltage = float(data.get('cutoff', 3.0))
    max_time = int(data.get('maxTime', 0))  # in seconds

    try:
        print(f'=== STARTING BATTERY TEST ===', file=sys.stderr)
        print(f'Test Parameters: Current={current}A, Cutoff={cutoff_voltage}V, MaxTime={max_time}s', file=sys.stderr)

        # Reset device energy counters before starting new test
        try:
            pload.instr.cmd_resetcounters()
            print(f'✓ Counters reset', file=sys.stderr)
            time.sleep(0.3)
        except Exception as e:
            print(f'✗ Error resetting counters: {e}', file=sys.stderr)

        # Set current
        try:
            pload.instr.cmd_setcurrent(current)
            print(f'✓ Current set to {current}A', file=sys.stderr)
            time.sleep(0.3)
        except Exception as e:
            print(f'✗ Error setting current: {e}', file=sys.stderr)

        # Set cutoff voltage
        try:
            pload.instr.cmd_setcutoff(cutoff_voltage)
            print(f'✓ Cutoff set to {cutoff_voltage}V', file=sys.stderr)
            time.sleep(0.3)
        except Exception as e:
            print(f'✗ Error setting cutoff: {e}', file=sys.stderr)

        # Turn on load
        try:
            pload.instr.cmd_setonoff(1)
            print(f'✓ Load turned ON', file=sys.stderr)
            time.sleep(1.0)  # Wait for device to stabilize
        except Exception as e:
            print(f'✗ Error turning on load: {e}', file=sys.stderr)
            raise e

        print(f'=== DEVICE CONFIGURATION COMPLETE ===', file=sys.stderr)

        # Initialize test state - reset all values
        global last_heartbeat
        last_heartbeat = time.time()  # Initialize heartbeat for timeout check
        test_state['running'] = True
        test_state['start_time'] = time.time()
        test_state['data_points'] = []
        test_state['current_data'] = {
            'voltage': 0.0,
            'current': 0.0,
            'power': 0.0,
            'resistance': 0.0,
            'capacity': 0,  # Reset mAh
            'energy': 0,    # Reset mWh
            'temperature': 0,
            'runtime': 0
        }

        # Start monitoring thread
        test_thread = threading.Thread(target=test_monitor, args=(cutoff_voltage, max_time), daemon=True)
        test_thread.start()

        return jsonify({
            'success': True,
            'message': f'Test started: {current}A until {cutoff_voltage}V'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_test():
    """Stop the current test"""
    global test_state, pload

    if not test_state['running']:
        return jsonify({'success': True, 'message': 'No test running (already stopped)'})

    try:
        print(f'=== STOPPING BATTERY TEST ===', file=sys.stderr)

        # Read final device state before stopping
        try:
            final_state = pload.instr.cmd_readstate(energy=True, limits=True, temp=True, short=False)
            final_voltage = pload.instr.cmd_getvolt()
            final_current = pload.instr.cmd_getamp()
            final_capacity = pload.instr.cmd_getah(div=1)
            final_energy = pload.instr.cmd_getwh(div=1)

            print(f'Final measurements: V={final_voltage:.3f}V, I={final_current:.3f}A, Capacity={final_capacity:.0f}mAh, Energy={final_energy:.0f}mWh', file=sys.stderr)
            print(f'Final device state: Load={final_state.get("out", 0)}, SetCurrent={final_state.get("Iset", 0)}A, Cutoff={final_state.get("Vcut", 0)}V', file=sys.stderr)
        except Exception as e:
            print(f'Warning: Could not read final device state: {e}', file=sys.stderr)

        stop_test_internal()

        print(f'=== TEST STOPPED ===', file=sys.stderr)
        return jsonify({'success': True, 'message': 'Test stopped'})
    except Exception as e:
        print(f'✗ Error stopping test: {e}', file=sys.stderr)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/data', methods=['GET'])
def get_data():
    """Get all recorded data points"""
    return jsonify({
        'dataPoints': test_state['data_points'],
        'count': len(test_state['data_points'])
    })

@app.route('/api/reset', methods=['POST'])
def reset_counters():
    """Reset energy counters"""
    global pload

    if not pload or not pload.instr or not pload.instr.comm:
        return jsonify({'success': False, 'error': 'Device not connected'}), 400

    try:
        pload.instr.cmd_resetcounters()
        return jsonify({'success': True, 'message': 'Counters reset'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    """Heartbeat from browser to prevent auto-stop"""
    global last_heartbeat
    last_heartbeat = time.time()
    return jsonify({'success': True})

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current device configuration"""
    global pload

    if not pload or not pload.instr or not pload.instr.comm:
        return jsonify({'success': False, 'error': 'Device not connected'}), 400

    try:
        return jsonify({
            'success': True,
            'config': {
                'setCurrent': pload.instr.cmd_getsetcurrent(),
                'setCutoff': pload.instr.cmd_getsetcutoff(),
                'outputEnabled': pload.instr.cmd_getonoff()
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ports', methods=['GET'])
def list_serial_ports():
    """List available serial ports"""
    ports = []

    if list_ports is None:
        return jsonify({
            'success': False,
            'error': 'pyserial not installed or list_ports unavailable'
        }), 500

    try:
        # List all available serial ports, filtering out virtual/unused ttyS ports
        for port in list_ports.comports():
            # Skip ttyS ports without real hardware (no USB VID:PID)
            if port.device.startswith('/dev/ttyS') and 'VID:PID' not in port.hwid:
                continue
            ports.append({
                'device': port.device,
                'description': port.description,
                'hwid': port.hwid
            })

        # Get current port from config
        current_port = pload.conf.get('serport', '') if pload else ''
        current_host = pload.conf.get('host', '') if pload else ''
        current_tcp_port = pload.conf.get('port', '') if pload else ''

        return jsonify({
            'success': True,
            'ports': ports,
            'current': {
                'serport': current_port,
                'host': current_host,
                'port': current_tcp_port
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/set_port', methods=['POST'])
def set_serial_port():
    """Change serial port and reconnect"""
    global pload, test_state

    data = request.json
    new_port = data.get('port', '')

    if not new_port:
        return jsonify({'success': False, 'error': 'No port specified'}), 400

    # Don't allow changing port during a running test
    if test_state['running']:
        return jsonify({
            'success': False,
            'error': 'Cannot change port while test is running'
        }), 400

    try:
        print(f'=== CHANGING SERIAL PORT ===', file=sys.stderr)
        print(f'New port: {new_port}', file=sys.stderr)

        # Close existing connection
        if pload and pload.instr and pload.instr.comm:
            print('Closing existing connection...', file=sys.stderr)
            pload.instr.close()

        # Update config file
        config_path = os.path.expanduser('~/.dl24.cfg')
        config_lines = []
        port_updated = False

        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                for line in f:
                    if line.strip().startswith('serport='):
                        config_lines.append(f'serport={new_port}\n')
                        port_updated = True
                    else:
                        config_lines.append(line)

        # If serport wasn't in config, add it
        if not port_updated:
            config_lines.append(f'serport={new_port}\n')

        # Write updated config
        with open(config_path, 'w') as f:
            f.writelines(config_lines)

        print(f'Config file updated: {config_path}', file=sys.stderr)

        # Reinitialize device with new port
        if not init_device():
            return jsonify({
                'success': False,
                'error': f'Could not connect to {new_port}'
            }), 500

        print(f'✅ Successfully connected to {new_port}', file=sys.stderr)

        return jsonify({
            'success': True,
            'message': f'Connected to {new_port}',
            'port': new_port
        })

    except Exception as e:
        print(f'❌ Error changing port: {e}', file=sys.stderr)
        return jsonify({'success': False, 'error': str(e)}), 500

def main():
    """Main entry point"""
    global update_thread, pload

    print('DL24P Web Server starting...')

    # Initialize pload object (needed for API even without connection)
    if pload is None:
        pload = PowerLoad()
        pload.verbrun = True
        pload.readconf(name='dl24')

    print('Initializing device connection...')

    if not init_device():
        print('WARNING: Could not initialize device.')
        print('You can configure the connection in the web interface.')
        print('Select serial port and click Connect.')
    else:
        print('Device connected successfully!')

    # Start background update thread
    update_thread = threading.Thread(target=update_data, daemon=True)
    update_thread.start()
    print('Background data update thread started')

    # Start Flask server
    print('\nWeb server ready!')
    print('Open http://localhost:5000 in your browser')
    print('Press Ctrl+C to stop\n')

    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print('\nShutting down...')
        if pload and pload.instr and pload.instr.comm:
            if test_state['running']:
                pload.instr.cmd_setonoff(0)
            pload.instr.close()
        print('Goodbye!')

if __name__ == '__main__':
    main()
