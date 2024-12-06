package com.example.jarvismk7.services

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import io.socket.client.IO
import io.socket.client.Socket
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.net.URISyntaxException

class BridgeService : Service() {
    private var socket: Socket? = null
    private val serviceScope = CoroutineScope(Dispatchers.IO)
    private var connectionToken: String? = null

    override fun onCreate() {
        super.onCreate()
        initializeSocket()
    }

    private fun initializeSocket() {
        try {
            socket = IO.socket(SERVER_URL).apply {
                on(Socket.EVENT_CONNECT) {
                    Log.d(TAG, "Socket connected")
                    connectionToken?.let { token ->
                        emit("authenticate", JSONObject().put("token", token))
                    }
                }
                on(Socket.EVENT_DISCONNECT) {
                    Log.d(TAG, "Socket disconnected")
                }
                on("execute") { args ->
                    handleCommand(args[0] as JSONObject)
                }
                connect()
            }
        } catch (e: URISyntaxException) {
            Log.e(TAG, "Socket initialization failed", e)
        }
    }

    private fun handleCommand(data: JSONObject) {
        serviceScope.launch {
            try {
                val command = data.getString("command")
                val params = data.optJSONObject("params") ?: JSONObject()
                
                when (command) {
                    "getBatteryLevel" -> handleBatteryLevelCommand()
                    "takeScreenshot" -> handleScreenshotCommand()
                    "launchApp" -> handleLaunchAppCommand(params)
                    // Add more commands as needed
                }
            } catch (e: Exception) {
                Log.e(TAG, "Command execution failed", e)
            }
        }
    }

    private fun handleBatteryLevelCommand() {
        // Implement battery level check
        val batteryLevel = getBatteryLevel()
        emitResponse("batteryLevel", JSONObject().put("level", batteryLevel))
    }

    private fun handleScreenshotCommand() {
        // Implement screenshot capture
        val screenshotPath = takeScreenshot()
        emitResponse("screenshot", JSONObject().put("path", screenshotPath))
    }

    private fun handleLaunchAppCommand(params: JSONObject) {
        val packageName = params.getString("packageName")
        val success = launchApp(packageName)
        emitResponse("appLaunch", JSONObject().put("success", success))
    }

    private fun emitResponse(event: String, data: JSONObject) {
        socket?.emit(event, data)
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        socket?.disconnect()
        super.onDestroy()
    }

    companion object {
        private const val TAG = "BridgeService"
        private const val SERVER_URL = "http://your-server-url:3000"
    }
} 