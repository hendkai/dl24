package com.dl24.app.ui

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.os.Bundle
import android.widget.SeekBar
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.dl24.app.ble.BleManager
import com.dl24.app.databinding.ActivityDeviceBinding
import com.dl24.app.protocol.AtorchProtocol
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

@SuppressLint("MissingPermission")
class DeviceActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDeviceBinding
    private lateinit var bleManager: BleManager
    private var currentMilliAmps = 1000
    private var cutoffMilliVolts = 2800

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDeviceBinding.inflate(layoutInflater)
        setContentView(binding.root)

        bleManager = BleManager(this)

        val deviceAddress = intent.getStringExtra("device_address") ?: return
        val deviceName = intent.getStringExtra("device_name") ?: "Unknown"

        binding.txtDeviceName.text = deviceName
        binding.txtStatus.text = "Connecting..."

        // Connect to device
        val bluetoothManager = getSystemService(BLUETOOTH_SERVICE) as BluetoothManager
        val device = bluetoothManager.adapter.getRemoteDevice(deviceAddress)
        bleManager.connect(device)

        setupUI()
        observeState()
    }

    private fun setupUI() {
        binding.btnOn.setOnClickListener {
            val cmd = AtorchProtocol.createOnCommand()
            if (bleManager.sendData(cmd)) {
                Toast.makeText(this, "Load ON", Toast.LENGTH_SHORT).show()
            }
        }

        binding.btnOff.setOnClickListener {
            val cmd = AtorchProtocol.createOffCommand()
            if (bleManager.sendData(cmd)) {
                Toast.makeText(this, "Load OFF", Toast.LENGTH_SHORT).show()
            }
        }

        binding.btnReset.setOnClickListener {
            val cmd = AtorchProtocol.createResetCommand()
            bleManager.sendData(cmd)
            Toast.makeText(this, "Counters Reset", Toast.LENGTH_SHORT).show()
        }

        binding.seekCurrent.max = 240  // 0-24A in 0.1A steps
        binding.seekCurrent.progress = 10  // 1A default
        binding.txtCurrentValue.text = "1.0 A"

        binding.seekCurrent.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                currentMilliAmps = progress * 100
                binding.txtCurrentValue.text = String.format("%.1f A", currentMilliAmps / 1000f)
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {
                val cmd = AtorchProtocol.createSetCurrentCommand(currentMilliAmps)
                bleManager.sendData(cmd)
            }
        })

        binding.seekCutoff.max = 300  // 0-30V in 0.1V steps
        binding.seekCutoff.progress = 28  // 2.8V default
        binding.txtCutoffValue.text = "2.8 V"

        binding.seekCutoff.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                cutoffMilliVolts = progress * 100
                binding.txtCutoffValue.text = String.format("%.1f V", cutoffMilliVolts / 1000f)
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {
                val cmd = AtorchProtocol.createSetCutoffCommand(cutoffMilliVolts)
                bleManager.sendData(cmd)
            }
        })

        binding.btnDisconnect.setOnClickListener {
            bleManager.disconnect()
            finish()
        }
    }

    private fun observeState() {
        lifecycleScope.launch {
            bleManager.connectionState.collectLatest { state ->
                binding.txtStatus.text = when (state) {
                    BleManager.ConnectionState.DISCONNECTED -> "Disconnected"
                    BleManager.ConnectionState.CONNECTING -> "Connecting..."
                    BleManager.ConnectionState.CONNECTED -> "Connected"
                    BleManager.ConnectionState.DISCOVERING_SERVICES -> "Discovering..."
                    BleManager.ConnectionState.READY -> "Ready"
                }

                val isReady = state == BleManager.ConnectionState.READY
                binding.btnOn.isEnabled = isReady
                binding.btnOff.isEnabled = isReady
                binding.btnReset.isEnabled = isReady
                binding.seekCurrent.isEnabled = isReady
                binding.seekCutoff.isEnabled = isReady
            }
        }

        lifecycleScope.launch {
            bleManager.receivedData.collectLatest { data ->
                data?.let { parseAndDisplayStatus(it) }
            }
        }
    }

    private fun parseAndDisplayStatus(data: ByteArray) {
        val status = AtorchProtocol.parseStatusPacket(data) ?: return

        runOnUiThread {
            binding.txtVoltage.text = String.format("%.2f V", status.voltage)
            binding.txtCurrent.text = String.format("%.3f A", status.current)
            binding.txtPower.text = String.format("%.2f W", status.power)
            binding.txtCapacity.text = String.format("%.3f Ah", status.capacity)
            binding.txtEnergy.text = String.format("%.2f Wh", status.energy)
            binding.txtTemperature.text = String.format("%d°C", status.temperature)
            binding.txtTime.text = String.format("%02d:%02d:%02d", status.hours, status.minutes, status.seconds)
            binding.txtLoadState.text = if (status.isOn) "ON" else "OFF"
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        bleManager.disconnect()
    }
}
