package com.dl24.app.protocol

/**
 * Atorch DL24P Protocol Implementation
 *
 * Packet format: 0xFF 0x55 [type] [ADU] [payload] [checksum]
 * Checksum: Sum of bytes from type to payload end, AND 0xFF, XOR 0x44
 */
object AtorchProtocol {

    const val PREFIX_1 = 0xFF.toByte()
    const val PREFIX_2 = 0x55.toByte()

    // Message types
    const val TYPE_STATUS = 0x01.toByte()      // 36-byte periodic status
    const val TYPE_REPLY = 0x02.toByte()       // 8-byte reply
    const val TYPE_REQUEST = 0x11.toByte()     // 10-byte master request

    // ADU types
    const val ADU_AC_METER = 0x01.toByte()
    const val ADU_DC_LOAD = 0x02.toByte()      // DL24
    const val ADU_USB_METER = 0x03.toByte()

    // Commands
    const val CMD_ON = 0x01.toByte()
    const val CMD_OFF = 0x02.toByte()
    const val CMD_SET_CURRENT = 0x03.toByte()
    const val CMD_SET_CUTOFF = 0x30.toByte()
    const val CMD_RESET = 0x05.toByte()

    data class DeviceStatus(
        val voltage: Float,           // Volts
        val current: Float,           // Amps
        val power: Float,             // Watts
        val capacity: Float,          // Ah
        val energy: Float,            // Wh
        val temperature: Int,         // Celsius
        val hours: Int,
        val minutes: Int,
        val seconds: Int,
        val isOn: Boolean,
        val cutoffVoltage: Float
    )

    fun calculateChecksum(data: ByteArray, start: Int, length: Int): Byte {
        var sum = 0
        for (i in start until start + length) {
            sum += data[i].toInt() and 0xFF
        }
        return ((sum and 0xFF) xor 0x44).toByte()
    }

    fun parseStatusPacket(data: ByteArray): DeviceStatus? {
        if (data.size < 36) return null
        if (data[0] != PREFIX_1 || data[1] != PREFIX_2) return null
        if (data[2] != TYPE_STATUS) return null

        // Verify checksum
        val checksum = calculateChecksum(data, 2, 33)
        if (data[35] != checksum) return null

        return DeviceStatus(
            voltage = getInt24(data, 4) / 10f,
            current = getInt24(data, 7) / 1000f,
            capacity = getInt24(data, 10) / 1000f,
            energy = getInt32(data, 13) / 100f,
            power = getInt24(data, 17) / 10f,
            temperature = (data[24].toInt() and 0xFF),
            hours = getInt16(data, 25),
            minutes = data[27].toInt() and 0xFF,
            seconds = data[28].toInt() and 0xFF,
            isOn = (data[29].toInt() and 0xFF) == 1,
            cutoffVoltage = getInt16(data, 30) / 100f
        )
    }

    fun createCommand(cmd: Byte, param1: Int = 0, param2: Int = 0, param3: Int = 0, param4: Int = 0): ByteArray {
        val packet = ByteArray(10)
        packet[0] = PREFIX_1
        packet[1] = PREFIX_2
        packet[2] = TYPE_REQUEST
        packet[3] = ADU_DC_LOAD
        packet[4] = cmd
        packet[5] = param1.toByte()
        packet[6] = param2.toByte()
        packet[7] = param3.toByte()
        packet[8] = param4.toByte()
        packet[9] = calculateChecksum(packet, 2, 7)
        return packet
    }

    fun createSetCurrentCommand(milliAmps: Int): ByteArray {
        val p1 = (milliAmps shr 24) and 0xFF
        val p2 = (milliAmps shr 16) and 0xFF
        val p3 = (milliAmps shr 8) and 0xFF
        val p4 = milliAmps and 0xFF
        return createCommand(CMD_SET_CURRENT, p1, p2, p3, p4)
    }

    fun createSetCutoffCommand(milliVolts: Int): ByteArray {
        val p3 = (milliVolts shr 8) and 0xFF
        val p4 = milliVolts and 0xFF
        return createCommand(CMD_SET_CUTOFF, 0, 0, p3, p4)
    }

    fun createOnCommand(): ByteArray = createCommand(CMD_ON)
    fun createOffCommand(): ByteArray = createCommand(CMD_OFF)
    fun createResetCommand(): ByteArray = createCommand(CMD_RESET)

    private fun getInt16(data: ByteArray, offset: Int): Int {
        return ((data[offset].toInt() and 0xFF) shl 8) or
               (data[offset + 1].toInt() and 0xFF)
    }

    private fun getInt24(data: ByteArray, offset: Int): Int {
        return ((data[offset].toInt() and 0xFF) shl 16) or
               ((data[offset + 1].toInt() and 0xFF) shl 8) or
               (data[offset + 2].toInt() and 0xFF)
    }

    private fun getInt32(data: ByteArray, offset: Int): Int {
        return ((data[offset].toInt() and 0xFF) shl 24) or
               ((data[offset + 1].toInt() and 0xFF) shl 16) or
               ((data[offset + 2].toInt() and 0xFF) shl 8) or
               (data[offset + 3].toInt() and 0xFF)
    }
}
