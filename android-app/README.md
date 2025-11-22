# DL24 BLE Controller - Android App

Android app for controlling Atorch DL24P electronic loads via Bluetooth Low Energy (BLE).

## Features

- BLE device scanning and connection
- Real-time status monitoring (voltage, current, power, capacity, energy, temperature)
- Load control (ON/OFF)
- Adjustable discharge current (0-24A)
- Configurable cutoff voltage
- Counter reset
- Dark theme matching web interface

## Requirements

- Android 8.0 (API 26) or higher
- BLE-capable device
- DL24P with BLE adapter (or ESP32 BLE-to-Serial bridge)

## Building

1. Open project in Android Studio
2. Sync Gradle files
3. Build and run on device

```bash
./gradlew assembleDebug
```

## BLE Compatibility Note

The DL24P natively uses **classic Bluetooth SPP** (Serial Port Profile), not BLE.
To use this app, you need one of:

1. **ESP32 BLE Bridge** - Flash an ESP32 with BLE-to-UART firmware
2. **HM-10/HM-19 Module** - BLE module connected to DL24P UART pins
3. **Custom BLE adapter** - Any BLE-to-Serial bridge

The app uses Nordic UART Service (NUS) UUIDs by default but will also discover
custom BLE characteristics.

## Protocol

Implements the Atorch protocol:
- Packet format: `0xFF 0x55 [type] [ADU] [payload] [checksum]`
- Supports status parsing and command generation
- See `AtorchProtocol.kt` for details

## Project Structure

```
app/src/main/java/com/dl24/app/
├── ble/
│   └── BleManager.kt       # BLE scanning, connection, data transfer
├── protocol/
│   └── AtorchProtocol.kt   # Atorch packet parsing and creation
└── ui/
    ├── MainActivity.kt     # Start screen
    ├── ScanActivity.kt     # Device scanner
    └── DeviceActivity.kt   # Device control panel
```

## License

Same as main dl24 project.
