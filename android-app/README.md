# DL24 Controller - Android App

Android app for controlling Atorch DL24P electronic loads via classic Bluetooth (SPP).

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
- DL24P with Bluetooth module (built-in)

## Building

1. Open project in Android Studio
2. Sync Gradle files
3. Build and run on device

```bash
./gradlew assembleDebug
```

## Bluetooth Connection

The DL24P uses **classic Bluetooth SPP** (Serial Port Profile) - the same as the official Atorch app.

1. Pair your DL24P in Android Bluetooth settings first
2. Open the app and select your device
3. The app connects via RFCOMM (SPP UUID: 00001101-0000-1000-8000-00805F9B34FB)

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
