#!/usr/bin/python3
"""
18650 Test Cycle Executor for DL24P
Executes multi-phase test cycles defined in JSON format
"""

import json
import time
import sys
from datetime import datetime

class TestCycleExecutor:
    def __init__(self, instr, test_cycle_file='test_cycles_18650.json'):
        self.instr = instr
        self.test_cycles = self.load_test_cycles(test_cycle_file)
        self.current_cycle = None
        self.current_phase = None
        self.phase_start_time = None
        self.cycle_data = []
        self.running = False

    def load_test_cycles(self, filename):
        """Load test cycle definitions from JSON file"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                return data['test_cycles']
        except Exception as e:
            print(f'Error loading test cycles: {e}', file=sys.stderr)
            return {}

    def list_cycles(self):
        """Return list of available test cycles"""
        return list(self.test_cycles.keys())

    def get_cycle_info(self, cycle_name):
        """Get information about a specific test cycle"""
        if cycle_name in self.test_cycles:
            return self.test_cycles[cycle_name]
        return None

    def start_cycle(self, cycle_name):
        """Start executing a test cycle"""
        if cycle_name not in self.test_cycles:
            raise ValueError(f'Unknown test cycle: {cycle_name}')

        self.current_cycle = self.test_cycles[cycle_name]
        self.running = True
        self.cycle_data = []

        print(f'Starting test cycle: {self.current_cycle["name"]}')
        print(f'Description: {self.current_cycle["description"]}')
        print(f'Estimated duration: {self.current_cycle["duration_estimate"]}')

        return True

    def execute_phase(self, phase, phase_num, total_phases):
        """Execute a single phase of the test cycle"""
        self.current_phase = phase
        self.phase_start_time = time.time()

        print(f'\n=== Phase {phase_num}/{total_phases}: {phase["name"]} ===')
        print(f'Description: {phase["description"]}')

        phase_type = phase['type']

        if phase_type == 'rest':
            return self._execute_rest(phase)
        elif phase_type == 'discharge':
            return self._execute_discharge(phase)
        elif phase_type == 'ramp':
            return self._execute_ramp(phase)
        else:
            print(f'Unknown phase type: {phase_type}', file=sys.stderr)
            return False

    def _execute_rest(self, phase):
        """Execute a rest phase (no load)"""
        duration = phase['duration']
        print(f'Resting for {duration} seconds...')

        # Turn off load
        self.instr.cmd_setonoff(0)

        start_time = time.time()
        while time.time() - start_time < duration:
            if not self.running:
                return False

            # Log data during rest
            self._log_datapoint('rest')
            time.sleep(1)

        print('Rest phase completed')
        return True

    def _execute_discharge(self, phase):
        """Execute a constant current discharge phase"""
        current = phase['current']
        cutoff_voltage = phase.get('cutoff_voltage', 2.5)
        max_time = phase.get('max_time', float('inf'))
        duration = phase.get('duration', None)
        log_interval = phase.get('log_interval', 5)

        print(f'Discharge at {current}A')
        if duration:
            print(f'Duration: {duration} seconds')
        else:
            print(f'Cutoff voltage: {cutoff_voltage}V, Max time: {max_time}s')

        # Set current and turn on load
        self.instr.cmd_setcurrent(current)
        self.instr.cmd_setcutoff(cutoff_voltage)
        self.instr.cmd_setonoff(1)

        start_time = time.time()
        last_log = 0

        while True:
            if not self.running:
                self.instr.cmd_setonoff(0)
                return False

            elapsed = time.time() - start_time

            # Check termination conditions
            voltage = self.instr.cmd_getvolt()

            # If duration specified, use that
            if duration and elapsed >= duration:
                print(f'Duration limit reached: {elapsed:.1f}s')
                break

            # Otherwise check voltage and time
            if not duration:
                if voltage <= cutoff_voltage:
                    print(f'Cutoff voltage reached: {voltage:.3f}V')
                    break

                if elapsed >= max_time:
                    print(f'Max time reached: {elapsed:.1f}s')
                    break

            # Log data at specified interval
            if elapsed - last_log >= log_interval:
                self._log_datapoint('discharge')
                last_log = elapsed

                # Print status
                capacity = self.instr.cmd_getah(div=1)
                print(f'  {elapsed:.0f}s: {voltage:.3f}V, {current:.3f}A, {capacity:.0f}mAh')

            time.sleep(0.5)

        self.instr.cmd_setonoff(0)
        print('Discharge phase completed')
        return True

    def _execute_ramp(self, phase):
        """Execute a current ramp phase"""
        start_current = phase['start_current']
        end_current = phase['end_current']
        duration = phase['duration']
        steps = phase.get('steps', 30)  # Number of steps in ramp

        print(f'Ramping from {start_current}A to {end_current}A over {duration}s')

        step_duration = duration / steps
        current_step = (end_current - start_current) / steps

        for step in range(steps):
            if not self.running:
                self.instr.cmd_setonoff(0)
                return False

            current = start_current + (current_step * step)
            self.instr.cmd_setcurrent(current)

            if step == 0:
                self.instr.cmd_setonoff(1)

            # Log data
            self._log_datapoint('ramp')

            voltage = self.instr.cmd_getvolt()
            print(f'  Step {step+1}/{steps}: {current:.2f}A, {voltage:.3f}V')

            time.sleep(step_duration)

        print('Ramp phase completed')
        return True

    def _log_datapoint(self, phase_type):
        """Log a data point during test execution"""
        datapoint = {
            'timestamp': datetime.now().isoformat(),
            'elapsed': time.time() - self.phase_start_time if self.phase_start_time else 0,
            'phase': self.current_phase['name'] if self.current_phase else 'unknown',
            'phase_type': phase_type,
            'voltage': self.instr.cmd_getvolt(),
            'current': self.instr.cmd_getamp(),
            'capacity_mah': self.instr.cmd_getah(div=1),
            'energy_mwh': self.instr.cmd_getwh(div=1),
            'temperature': self.instr.cmd_gettemp()
        }
        self.cycle_data.append(datapoint)

    def run_cycle(self, cycle_name):
        """Run a complete test cycle"""
        if not self.start_cycle(cycle_name):
            return False

        phases = self.current_cycle['phases']
        total_phases = len(phases)

        for i, phase in enumerate(phases, 1):
            success = self.execute_phase(phase, i, total_phases)
            if not success:
                print('\nTest cycle aborted!')
                return False

        print('\n=== Test Cycle Completed Successfully ===')
        return True

    def stop(self):
        """Stop the current test cycle"""
        self.running = False
        self.instr.cmd_setonoff(0)

    def export_data(self, filename=None):
        """Export cycle data to CSV"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'test_cycle_{timestamp}.csv'

        if not self.cycle_data:
            print('No data to export')
            return False

        with open(filename, 'w') as f:
            # Write header
            headers = ['timestamp', 'elapsed_s', 'phase', 'phase_type',
                      'voltage_v', 'current_a', 'capacity_mah',
                      'energy_mwh', 'temperature_c']
            f.write(','.join(headers) + '\n')

            # Write data
            for dp in self.cycle_data:
                row = [
                    dp['timestamp'],
                    f"{dp['elapsed']:.1f}",
                    dp['phase'],
                    dp['phase_type'],
                    f"{dp['voltage']:.3f}",
                    f"{dp['current']:.3f}",
                    f"{dp['capacity_mah']:.1f}",
                    f"{dp['energy_mwh']:.1f}",
                    f"{dp['temperature']:.1f}"
                ]
                f.write(','.join(row) + '\n')

        print(f'Data exported to {filename}')
        return True


# Command-line interface for standalone execution
if __name__ == '__main__':
    from dl24 import PowerLoad

    if len(sys.argv) < 2:
        print('Usage: ./test_cycle_executor.py <cycle_name>')
        print('\nAvailable test cycles:')

        # Load and list cycles
        try:
            with open('test_cycles_18650.json', 'r') as f:
                data = json.load(f)
                for name, cycle in data['test_cycles'].items():
                    print(f'  {name}: {cycle["name"]} - {cycle["description"]}')
        except Exception as e:
            print(f'Error: {e}')
        sys.exit(1)

    cycle_name = sys.argv[1]

    # Initialize device
    print('Initializing DL24P...')
    pload = PowerLoad()
    pload.readconf(name='dl24')
    pload.initport()
    pload.instr.connect()

    # Create executor
    executor = TestCycleExecutor(pload.instr)

    try:
        # Run cycle
        executor.run_cycle(cycle_name)

        # Export data
        executor.export_data()

    except KeyboardInterrupt:
        print('\n\nTest interrupted by user')
        executor.stop()
    except Exception as e:
        print(f'\nError: {e}', file=sys.stderr)
        executor.stop()
    finally:
        pload.instr.close()
        print('Device disconnected')
