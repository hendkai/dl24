package com.dl24.app.ui

import android.annotation.SuppressLint
import android.bluetooth.le.ScanResult
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
import com.dl24.app.ble.BleManager
import com.dl24.app.databinding.ActivityScanBinding
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

class ScanActivity : AppCompatActivity() {

    private lateinit var binding: ActivityScanBinding
    private lateinit var bleManager: BleManager
    private lateinit var adapter: DeviceAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityScanBinding.inflate(layoutInflater)
        setContentView(binding.root)

        bleManager = BleManager(this)

        adapter = DeviceAdapter { result ->
            val intent = Intent(this, DeviceActivity::class.java)
            intent.putExtra("device_address", result.device.address)
            intent.putExtra("device_name", result.device.name ?: "Unknown")
            startActivity(intent)
            finish()
        }

        binding.recyclerDevices.layoutManager = LinearLayoutManager(this)
        binding.recyclerDevices.adapter = adapter

        binding.btnScan.setOnClickListener {
            binding.progressBar.visibility = View.VISIBLE
            binding.btnScan.isEnabled = false
            bleManager.startScan()
        }

        lifecycleScope.launch {
            bleManager.scanResults.collectLatest { results ->
                adapter.updateResults(results)
                if (results.isNotEmpty()) {
                    binding.progressBar.visibility = View.GONE
                    binding.btnScan.isEnabled = true
                }
            }
        }

        // Auto-start scan
        binding.progressBar.visibility = View.VISIBLE
        bleManager.startScan()
    }

    override fun onDestroy() {
        super.onDestroy()
        bleManager.stopScan()
    }

    private class DeviceAdapter(
        private val onClick: (ScanResult) -> Unit
    ) : RecyclerView.Adapter<DeviceAdapter.ViewHolder>() {

        private var results = listOf<ScanResult>()

        @SuppressLint("NotifyDataSetChanged")
        fun updateResults(newResults: List<ScanResult>) {
            results = newResults
            notifyDataSetChanged()
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
            val view = LayoutInflater.from(parent.context)
                .inflate(R.layout.item_device, parent, false)
            return ViewHolder(view)
        }

        @SuppressLint("MissingPermission")
        override fun onBindViewHolder(holder: ViewHolder, position: Int) {
            val result = results[position]
            holder.name.text = result.device.name ?: "Unknown Device"
            holder.address.text = result.device.address
            holder.rssi.text = "${result.rssi} dBm"
            holder.itemView.setOnClickListener { onClick(result) }
        }

        override fun getItemCount() = results.size

        class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
            val name: TextView = view.findViewById(R.id.txtDeviceName)
            val address: TextView = view.findViewById(R.id.txtDeviceAddress)
            val rssi: TextView = view.findViewById(R.id.txtRssi)
        }
    }
}
