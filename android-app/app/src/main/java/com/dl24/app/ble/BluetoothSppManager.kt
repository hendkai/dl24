package com.dl24.app.ble

import android.annotation.SuppressLint
import android.bluetooth.*
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.util.UUID

/**
 * Classic Bluetooth SPP (Serial Port Profile) Manager
 * This is what the DL24P actually uses - not BLE!
 */
@SuppressLint("MissingPermission")
class BluetoothSppManager(private val context: Context) {

    companion object {
        // Standard SPP UUID
        val SPP_UUID: UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
    }

    private val bluetoothAdapter: BluetoothAdapter? =
        (context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager).adapter

    private var socket: BluetoothSocket? = null
    private var inputStream: InputStream? = null
    private var outputStream: OutputStream? = null
    private var readJob: Job? = null
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    val connectionState: StateFlow<ConnectionState> = _connectionState

    private val _discoveredDevices = MutableStateFlow<List<BluetoothDevice>>(emptyList())
    val discoveredDevices: StateFlow<List<BluetoothDevice>> = _discoveredDevices

    private val _receivedData = MutableStateFlow<ByteArray?>(null)
    val receivedData: StateFlow<ByteArray?> = _receivedData

    enum class ConnectionState {
        DISCONNECTED, CONNECTING, CONNECTED
    }

    private val discoveryReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            when (intent.action) {
                BluetoothDevice.ACTION_FOUND -> {
                    val device = intent.getParcelableExtra<BluetoothDevice>(BluetoothDevice.EXTRA_DEVICE)
                    device?.let {
                        val currentDevices = _discoveredDevices.value.toMutableList()
                        if (!currentDevices.any { d -> d.address == it.address }) {
                            currentDevices.add(it)
                            _discoveredDevices.value = currentDevices
                        }
                    }
                }
                BluetoothAdapter.ACTION_DISCOVERY_FINISHED -> {
                    // Discovery finished
                }
            }
        }
    }

    fun startDiscovery() {
        _discoveredDevices.value = emptyList()

        // Add paired devices first
        bluetoothAdapter?.bondedDevices?.let { paired ->
            _discoveredDevices.value = paired.toList()
        }

        // Register receiver for discovery
        val filter = IntentFilter().apply {
            addAction(BluetoothDevice.ACTION_FOUND)
            addAction(BluetoothAdapter.ACTION_DISCOVERY_FINISHED)
        }
        context.registerReceiver(discoveryReceiver, filter)

        // Start discovery
        bluetoothAdapter?.startDiscovery()
    }

    fun stopDiscovery() {
        bluetoothAdapter?.cancelDiscovery()
        try {
            context.unregisterReceiver(discoveryReceiver)
        } catch (e: Exception) {
            // Receiver not registered
        }
    }

    fun connect(device: BluetoothDevice) {
        stopDiscovery()
        _connectionState.value = ConnectionState.CONNECTING

        scope.launch {
            try {
                socket = device.createRfcommSocketToServiceRecord(SPP_UUID)
                socket?.connect()

                inputStream = socket?.inputStream
                outputStream = socket?.outputStream

                _connectionState.value = ConnectionState.CONNECTED

                // Start reading data
                startReading()
            } catch (e: IOException) {
                _connectionState.value = ConnectionState.DISCONNECTED
                socket?.close()
                socket = null
            }
        }
    }

    fun disconnect() {
        readJob?.cancel()
        try {
            inputStream?.close()
            outputStream?.close()
            socket?.close()
        } catch (e: IOException) {
            // Ignore
        }
        socket = null
        inputStream = null
        outputStream = null
        _connectionState.value = ConnectionState.DISCONNECTED
    }

    private fun startReading() {
        readJob = scope.launch {
            val buffer = ByteArray(1024)
            while (isActive && socket?.isConnected == true) {
                try {
                    val bytes = inputStream?.read(buffer) ?: -1
                    if (bytes > 0) {
                        val data = buffer.copyOf(bytes)
                        _receivedData.value = data
                    }
                } catch (e: IOException) {
                    if (isActive) {
                        _connectionState.value = ConnectionState.DISCONNECTED
                    }
                    break
                }
            }
        }
    }

    fun sendData(data: ByteArray): Boolean {
        return try {
            outputStream?.write(data)
            outputStream?.flush()
            true
        } catch (e: IOException) {
            false
        }
    }

    fun isBluetoothEnabled(): Boolean = bluetoothAdapter?.isEnabled == true

    fun getPairedDevices(): Set<BluetoothDevice> {
        return bluetoothAdapter?.bondedDevices ?: emptySet()
    }

    fun cleanup() {
        disconnect()
        scope.cancel()
    }
}
