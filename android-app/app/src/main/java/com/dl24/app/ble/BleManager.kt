package com.dl24.app.ble

import android.annotation.SuppressLint
import android.bluetooth.*
import android.bluetooth.le.*
import android.content.Context
import android.os.Handler
import android.os.Looper
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.util.UUID

@SuppressLint("MissingPermission")
class BleManager(private val context: Context) {

    companion object {
        // Nordic UART Service UUIDs (common for BLE serial)
        val UART_SERVICE_UUID: UUID = UUID.fromString("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
        val UART_TX_CHAR_UUID: UUID = UUID.fromString("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
        val UART_RX_CHAR_UUID: UUID = UUID.fromString("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")
        val CCCD_UUID: UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")

        private const val SCAN_TIMEOUT = 10000L
    }

    private val bluetoothAdapter: BluetoothAdapter? =
        (context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager).adapter

    private var bluetoothGatt: BluetoothGatt? = null
    private var txCharacteristic: BluetoothGattCharacteristic? = null
    private var rxCharacteristic: BluetoothGattCharacteristic? = null

    private val handler = Handler(Looper.getMainLooper())

    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    val connectionState: StateFlow<ConnectionState> = _connectionState

    private val _scanResults = MutableStateFlow<List<ScanResult>>(emptyList())
    val scanResults: StateFlow<List<ScanResult>> = _scanResults

    private val _receivedData = MutableStateFlow<ByteArray?>(null)
    val receivedData: StateFlow<ByteArray?> = _receivedData

    enum class ConnectionState {
        DISCONNECTED, CONNECTING, CONNECTED, DISCOVERING_SERVICES, READY
    }

    private val scanCallback = object : ScanCallback() {
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            val currentResults = _scanResults.value.toMutableList()
            val existingIndex = currentResults.indexOfFirst {
                it.device.address == result.device.address
            }
            if (existingIndex >= 0) {
                currentResults[existingIndex] = result
            } else {
                currentResults.add(result)
            }
            _scanResults.value = currentResults
        }
    }

    private val gattCallback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
            when (newState) {
                BluetoothProfile.STATE_CONNECTED -> {
                    _connectionState.value = ConnectionState.DISCOVERING_SERVICES
                    gatt.discoverServices()
                }
                BluetoothProfile.STATE_DISCONNECTED -> {
                    _connectionState.value = ConnectionState.DISCONNECTED
                    bluetoothGatt?.close()
                    bluetoothGatt = null
                }
            }
        }

        override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS) {
                setupUartService(gatt)
            }
        }

        override fun onCharacteristicChanged(
            gatt: BluetoothGatt,
            characteristic: BluetoothGattCharacteristic,
            value: ByteArray
        ) {
            if (characteristic.uuid == UART_RX_CHAR_UUID) {
                _receivedData.value = value
            }
        }

        @Deprecated("Deprecated in Java")
        override fun onCharacteristicChanged(
            gatt: BluetoothGatt,
            characteristic: BluetoothGattCharacteristic
        ) {
            if (characteristic.uuid == UART_RX_CHAR_UUID) {
                _receivedData.value = characteristic.value
            }
        }
    }

    fun startScan() {
        _scanResults.value = emptyList()
        val scanner = bluetoothAdapter?.bluetoothLeScanner ?: return

        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .build()

        scanner.startScan(null, settings, scanCallback)

        handler.postDelayed({
            stopScan()
        }, SCAN_TIMEOUT)
    }

    fun stopScan() {
        bluetoothAdapter?.bluetoothLeScanner?.stopScan(scanCallback)
    }

    fun connect(device: BluetoothDevice) {
        stopScan()
        _connectionState.value = ConnectionState.CONNECTING
        bluetoothGatt = device.connectGatt(context, false, gattCallback, BluetoothDevice.TRANSPORT_LE)
    }

    fun disconnect() {
        bluetoothGatt?.disconnect()
    }

    private fun setupUartService(gatt: BluetoothGatt) {
        val service = gatt.getService(UART_SERVICE_UUID)
        if (service != null) {
            txCharacteristic = service.getCharacteristic(UART_TX_CHAR_UUID)
            rxCharacteristic = service.getCharacteristic(UART_RX_CHAR_UUID)

            // Enable notifications on RX
            rxCharacteristic?.let { rx ->
                gatt.setCharacteristicNotification(rx, true)
                val descriptor = rx.getDescriptor(CCCD_UUID)
                descriptor?.let {
                    it.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
                    gatt.writeDescriptor(it)
                }
            }

            _connectionState.value = ConnectionState.READY
        } else {
            // Try to find any writable characteristic for custom BLE devices
            for (svc in gatt.services) {
                for (char in svc.characteristics) {
                    if (char.properties and BluetoothGattCharacteristic.PROPERTY_WRITE != 0) {
                        txCharacteristic = char
                    }
                    if (char.properties and BluetoothGattCharacteristic.PROPERTY_NOTIFY != 0) {
                        rxCharacteristic = char
                        gatt.setCharacteristicNotification(char, true)
                    }
                }
            }
            _connectionState.value = ConnectionState.READY
        }
    }

    fun sendData(data: ByteArray): Boolean {
        val gatt = bluetoothGatt ?: return false
        val tx = txCharacteristic ?: return false

        tx.value = data
        tx.writeType = BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
        return gatt.writeCharacteristic(tx)
    }

    fun isBluetoothEnabled(): Boolean = bluetoothAdapter?.isEnabled == true
}
