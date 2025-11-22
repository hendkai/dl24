package com.dl24.app.ui

import android.annotation.SuppressLint
import android.bluetooth.BluetoothDevice
import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.dl24.app.R
import com.dl24.app.ble.BluetoothSppManager
import com.dl24.app.databinding.ActivityScanBinding
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

class ScanActivity : AppCompatActivity() {

    private lateinit var binding: ActivityScanBinding
    private lateinit var sppManager: BluetoothSppManager
    private lateinit var adapter: DeviceAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityScanBinding.inflate(layoutInflater)
        setContentView(binding.root)

        sppManager = BluetoothSppManager(this)

        adapter = DeviceAdapter { device ->
            val intent = Intent(this, DeviceActivity::class.java)
            intent.putExtra("device_address", device.address)
            intent.putExtra("device_name", device.name ?: "Unknown")
            startActivity(intent)
            finish()
        }

        binding.recyclerDevices.layoutManager = LinearLayoutManager(this)
        binding.recyclerDevices.adapter = adapter

        binding.btnScan.setOnClickListener {
            binding.progressBar.visibility = View.VISIBLE
            binding.btnScan.isEnabled = false
            sppManager.startDiscovery()
        }

        lifecycleScope.launch {
            sppManager.discoveredDevices.collectLatest { devices ->
                adapter.updateDevices(devices)
                if (devices.isNotEmpty()) {
                    binding.progressBar.visibility = View.GONE
                    binding.btnScan.isEnabled = true
                }
            }
        }

        // Show paired devices immediately
        val paired = sppManager.getPairedDevices().toList()
        if (paired.isNotEmpty()) {
            adapter.updateDevices(paired)
        } else {
            binding.progressBar.visibility = View.VISIBLE
            sppManager.startDiscovery()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        sppManager.stopDiscovery()
    }

    private class DeviceAdapter(
        private val onClick: (BluetoothDevice) -> Unit
    ) : RecyclerView.Adapter<DeviceAdapter.ViewHolder>() {

        private var devices = listOf<BluetoothDevice>()

        @SuppressLint("NotifyDataSetChanged")
        fun updateDevices(newDevices: List<BluetoothDevice>) {
            devices = newDevices
            notifyDataSetChanged()
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
            val view = LayoutInflater.from(parent.context)
                .inflate(R.layout.item_device, parent, false)
            return ViewHolder(view)
        }

        @SuppressLint("MissingPermission")
        override fun onBindViewHolder(holder: ViewHolder, position: Int) {
            val device = devices[position]
            holder.name.text = device.name ?: "Unknown Device"
            holder.address.text = device.address
            holder.rssi.text = if (device.bondState == BluetoothDevice.BOND_BONDED) "Paired" else ""
            holder.itemView.setOnClickListener { onClick(device) }
        }

        override fun getItemCount() = devices.size

        class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
            val name: TextView = view.findViewById(R.id.txtDeviceName)
            val address: TextView = view.findViewById(R.id.txtDeviceAddress)
            val rssi: TextView = view.findViewById(R.id.txtRssi)
        }
    }
}
