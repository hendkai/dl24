# 18650 Test Cycles for DL24P

Professional battery testing cycles adapted from TestController procedures for use with ATorch DL24P.

## Available Test Cycles

### 1. Basic Capacity Test
**Duration:** 2-4 hours
**Current:** 1.0A constant
**Purpose:** Standard capacity verification and degradation monitoring

**Procedure:**
1. Initial rest (60s) - Battery stabilization
2. Constant 1A discharge until 2.5V cutoff
3. Data logged every 5 seconds

**Best for:** Regular capacity checks, quality control, cell matching

---

### 2. Slow Capacity Test
**Duration:** 5-8 hours
**Current:** 0.5A constant
**Purpose:** Accurate capacity measurement at low discharge rate

**Procedure:**
1. Extended rest (120s) - Thorough stabilization
2. Constant 0.5A discharge until 2.5V cutoff
3. Data logged every 10 seconds

**Best for:** Precise capacity rating, reference measurements, low-drain applications

---

### 3. Fast Screening Test
**Duration:** 1-2 hours
**Current:** 2.0A constant
**Purpose:** Quick high-rate discharge for cell screening

**Procedure:**
1. Brief rest (30s)
2. Constant 2A discharge until 2.5V cutoff
3. Data logged every 2 seconds

**Best for:** Batch testing, high-drain application verification, quick QC

---

### 4. Advanced Stress Test
**Duration:** 6-8 hours
**Purpose:** Multi-phase dynamic load testing for high-drain applications

**Procedure:**
1. Initial rest (60s)
2. Conditioning phase - 15 min at 1A
3. Ramp up - Linear increase 1A → 2A over 15 min
4. Maximum load hold - 15 min at 2A
5. Ramp down - Linear decrease 2A → 1A over 15 min
6. Final discharge - 1A until 2.5V cutoff

**Best for:** Power tool batteries, high-drain applications, stress testing

**Note:** Multi-phase testing requires manual execution with `test_cycle_executor.py`

---

### 5. Cycle Life Test
**Duration:** Variable (10 cycles)
**Purpose:** Repeated discharge cycles for degradation analysis

**Procedure (per cycle):**
1. Rest before discharge (5 min)
2. 1A discharge to 2.5V cutoff
3. Rest after discharge (10 min)
4. **Manual recharge required before next cycle**

**Best for:** Long-term degradation studies, cycle life analysis

---

## Usage

### Web GUI (Simple Tests)
1. Open http://localhost:5000
2. Select "Test Cycle Profile" dropdown
3. Choose desired test cycle
4. Parameters automatically configured
5. Click "Start Test"

### Command Line (Advanced/Multi-phase Tests)
```bash
# List available cycles
./test_cycle_executor.py

# Run specific cycle
./test_cycle_executor.py basic_capacity
./test_cycle_executor.py advanced_stress

# Data automatically exported to CSV on completion
```

### Python Script Integration
```python
from dl24 import PowerLoad
from test_cycle_executor import TestCycleExecutor

# Initialize device
pload = PowerLoad()
pload.readconf(name='dl24')
pload.initport()
pload.instr.connect()

# Create executor
executor = TestCycleExecutor(pload.instr)

# List cycles
cycles = executor.list_cycles()
print(f'Available: {cycles}')

# Run cycle
executor.run_cycle('basic_capacity')

# Export data
executor.export_data('my_test_results.csv')

# Cleanup
pload.instr.close()
```

---

## Safety Parameters

All test cycles include safety monitoring:

| Parameter | Limit | Action |
|-----------|-------|--------|
| Max Temperature | 50°C (55°C fast test) | Auto-stop |
| Min Temperature | 15°C | Auto-stop |
| Max Voltage | 4.2V | Warning |
| Min Voltage | 2.5V | Cutoff (normal) |
| | 2.0V | Hard cutoff |

---

## Output Data

All tests generate CSV files with the following columns:

- **timestamp** - ISO format datetime
- **elapsed_s** - Seconds since phase start
- **phase** - Current test phase name
- **phase_type** - rest/discharge/ramp
- **voltage_v** - Battery voltage (V)
- **current_a** - Discharge current (A)
- **capacity_mah** - Accumulated capacity (mAh)
- **energy_mwh** - Accumulated energy (mWh)
- **temperature_c** - Device temperature (°C)

---

## Recommendations

### For Capacity Testing
- **New cells:** Use "Basic Capacity Test" (1A)
- **Accurate rating:** Use "Slow Capacity Test" (0.5A)
- **High-drain cells:** Use "Fast Screening" (2A)

### For Quality Control
1. Run "Fast Screening" for initial sorting
2. Use "Basic Capacity Test" for verification
3. Compare against manufacturer specs

### For Research
- Use "Cycle Life Test" for degradation studies
- Use "Advanced Stress Test" for power tool applications
- Log multiple tests to track cell aging

---

## Typical 18650 Expectations

| Cell Type | Capacity | Internal Resistance | Max Continuous |
|-----------|----------|---------------------|----------------|
| Samsung 30Q | 3000mAh | 15-20mΩ | 15A |
| LG HG2 | 3000mAh | 18-25mΩ | 20A |
| Sony VTC6 | 3000mAh | 12-18mΩ | 15A |
| Samsung 25R | 2500mAh | 18-22mΩ | 20A |
| Generic/Rewrap | 1000-2500mAh | 50-200mΩ | 5-10A |

**At 1A discharge (1C for 3000mAh cell):**
- Voltage should start ~4.2V (fully charged)
- Typical runtime: 2.5-3.5 hours
- Final voltage: 2.5-3.0V
- Temperature rise: 5-15°C

---

## File Structure

```
dl24/
├── test_cycles_18650.json      # Test cycle definitions
├── test_cycle_executor.py      # Execution engine
├── dl24_webserver.py           # Web GUI backend
├── index.html                  # Web GUI frontend
└── TEST_CYCLES_README.md       # This file
```

---

## Troubleshooting

**Test stops immediately:**
- Check battery connection
- Verify battery voltage > 2.5V
- Check temperature sensor

**Inconsistent capacity readings:**
- Ensure battery fully charged before test
- Check load current stability
- Verify temperature within range

**Can't start advanced cycles:**
- Use `test_cycle_executor.py` command line
- Check `test_cycles_18650.json` exists
- Verify Python script has execute permission

---

## Credits

Test procedures adapted from TestController 18650 testing methodology.
Implemented for ATorch DL24P electronic load by Claude Code.
