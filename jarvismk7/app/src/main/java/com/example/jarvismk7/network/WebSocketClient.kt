package com.example.jarvismk7.network

import android.os.BatteryManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.Log
import org.json.JSONObject
import java.util.concurrent.TimeUnit
import okhttp3.*
import okio.ByteString
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap
import kotlinx.coroutines.*
import java.util.concurrent.atomic.AtomicInteger

class WebSocketClient {
    private var webSocket: WebSocket? = null
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .connectTimeout(10, TimeUnit.SECONDS)
        .pingInterval(15, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .build()

    private var serverUrl: String? = null
    private var token: String? = null
    private var isConnected = false
    private var reconnectAttempts = AtomicInteger(0)
    private var maxReconnectAttempts = 5
    private var reconnectDelayMs = 5000L
    private var heartbeatInterval = 15000L
    private var commandTimeout = 30000L
    private val mainHandler = Handler(Looper.getMainLooper())
    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())

    private val pendingCommands = ConcurrentHashMap<String, CommandRequest>()
    private val metrics = ConnectionMetrics()

    var onMessageReceived: ((String) -> Unit)? = null
    var onConnectionStateChanged: ((Boolean) -> Unit)? = null
    var onReconnecting: (() -> Unit)? = null
    var onCommandTimeout: ((String, String) -> Unit)? = null
    var onError: ((String, String?) -> Unit)? = null

    data class CommandRequest(
        val command: String,
        val params: JSONObject,
        val timestamp: Long,
        var timeoutJob: Job? = null
    )

    inner class ConnectionMetrics {
        var totalCommands = AtomicInteger(0)
        var successfulCommands = AtomicInteger(0)
        var failedCommands = AtomicInteger(0)
        var averageResponseTime = 0L
        var lastResponseTime = 0L
        var connectionUptime = 0L
        private var connectionStartTime = 0L

        fun onConnected() {
            connectionStartTime = System.currentTimeMillis()
        }

        fun onDisconnected() {
            if (connectionStartTime > 0) {
                connectionUptime += System.currentTimeMillis() - connectionStartTime
            }
        }

        fun updateResponseTime(responseTime: Long) {
            lastResponseTime = responseTime
            averageResponseTime = if (averageResponseTime == 0L) {
                responseTime
            } else {
                (averageResponseTime + responseTime) / 2
            }
        }

        fun reset() {
            totalCommands.set(0)
            successfulCommands.set(0)
            failedCommands.set(0)
            averageResponseTime = 0L
            lastResponseTime = 0L
            connectionUptime = 0L
            connectionStartTime = 0L
        }
    }

    private val heartbeatRunnable = object : Runnable {
        override fun run() {
            if (isConnected) {
                sendHeartbeat()
                mainHandler.postDelayed(this, heartbeatInterval)
            }
        }
    }

    fun connect(url: String, authToken: String) {
        serverUrl = url
        token = authToken
        establishConnection()
    }

    private fun establishConnection() {
        try {
            val request = Request.Builder()
                .url(serverUrl!!)
                .build()

            webSocket = client.newWebSocket(request, createWebSocketListener())
        } catch (e: Exception) {
            Log.e(TAG, "Failed to establish connection", e)
            onError?.invoke("CONNECTION_ERROR", e.message)
            scheduleReconnect()
        }
    }

    private fun createWebSocketListener(): WebSocketListener {
        return object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                isConnected = true
                reconnectAttempts.set(0)
                metrics.onConnected()
                authenticate()
                startHeartbeat()
                sendDeviceInfo()
                onConnectionStateChanged?.invoke(true)
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                try {
                    val json = JSONObject(text)
                    when (json.optString("type")) {
                        "authenticated" -> handleAuthentication(json)
                        "reconnect" -> handleReconnect()
                        "getDeviceInfo" -> sendDeviceInfo()
                        "commandTimeout" -> handleCommandTimeout(json)
                        "error" -> handleError(json)
                        else -> onMessageReceived?.invoke(text)
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Error parsing message", e)
                    onError?.invoke("MESSAGE_PARSE_ERROR", e.message)
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "WebSocket failure", t)
                handleDisconnect()
                onError?.invoke("WEBSOCKET_FAILURE", t.message)
                scheduleReconnect()
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                handleDisconnect()
                if (code != 1000) {
                    scheduleReconnect()
                }
            }
        }
    }

    private fun handleAuthentication(json: JSONObject) {
        val config = json.optJSONObject("config")
        config?.let {
            heartbeatInterval = it.optLong("heartbeatInterval", heartbeatInterval)
            commandTimeout = it.optLong("commandTimeout", commandTimeout)
            maxReconnectAttempts = it.optInt("maxReconnectAttempts", maxReconnectAttempts)
        }
    }

    private fun handleCommandTimeout(json: JSONObject) {
        val messageId = json.optString("messageId")
        val command = json.optString("command")
        pendingCommands.remove(messageId)?.let { request ->
            metrics.failedCommands.incrementAndGet()
            onCommandTimeout?.invoke(messageId, command)
        }
    }

    private fun handleError(json: JSONObject) {
        val type = json.optString("type")
        val message = json.optString("message")
        onError?.invoke(type, message)
    }

    private fun handleDisconnect() {
        isConnected = false
        stopHeartbeat()
        metrics.onDisconnected()
        onConnectionStateChanged?.invoke(false)
        cancelPendingCommands()
    }

    private fun authenticate() {
        val auth = JSONObject().apply {
            put("type", "authenticate")
            put("token", token)
            put("deviceInfo", getDeviceInfo())
        }
        sendMessage(auth.toString())
    }

    private fun getDeviceInfo(): JSONObject {
        return JSONObject().apply {
            put("model", Build.MODEL)
            put("manufacturer", Build.MANUFACTURER)
            put("androidVersion", Build.VERSION.RELEASE)
            put("sdkVersion", Build.VERSION.SDK_INT)
            put("uniqueId", Build.FINGERPRINT)
        }
    }

    private fun sendDeviceInfo() {
        val deviceInfo = JSONObject().apply {
            put("type", "deviceInfo")
            put("info", getDeviceInfo())
            put("metrics", JSONObject().apply {
                put("totalCommands", metrics.totalCommands.get())
                put("successfulCommands", metrics.successfulCommands.get())
                put("failedCommands", metrics.failedCommands.get())
                put("averageResponseTime", metrics.averageResponseTime)
                put("connectionUptime", metrics.connectionUptime)
            })
        }
        sendMessage(deviceInfo.toString())
    }

    private fun sendHeartbeat() {
        val heartbeat = JSONObject().apply {
            put("type", "heartbeat")
            put("timestamp", System.currentTimeMillis())
            put("metrics", JSONObject().apply {
                put("batteryLevel", getBatteryLevel())
                put("totalCommands", metrics.totalCommands.get())
                put("successfulCommands", metrics.successfulCommands.get())
                put("failedCommands", metrics.failedCommands.get())
                put("averageResponseTime", metrics.averageResponseTime)
            })
        }
        sendMessage(heartbeat.toString())
    }

    fun sendCommand(command: String, params: JSONObject): String {
        val messageId = UUID.randomUUID().toString()
        val timestamp = System.currentTimeMillis()

        val commandRequest = CommandRequest(
            command = command,
            params = params,
            timestamp = timestamp
        )

        commandRequest.timeoutJob = scope.launch {
            delay(commandTimeout)
            handleCommandTimeout(JSONObject().apply {
                put("messageId", messageId)
                put("command", command)
            })
        }

        pendingCommands[messageId] = commandRequest
        metrics.totalCommands.incrementAndGet()

        val message = JSONObject().apply {
            put("type", "command")
            put("token", token)
            put("command", command)
            put("params", params)
            put("messageId", messageId)
            put("timestamp", timestamp)
        }

        sendMessage(message.toString())
        return messageId
    }

    fun handleCommandResponse(messageId: String, result: JSONObject?, error: String?) {
        pendingCommands.remove(messageId)?.let { request ->
            request.timeoutJob?.cancel()
            val responseTime = System.currentTimeMillis() - request.timestamp
            metrics.updateResponseTime(responseTime)

            if (error == null) {
                metrics.successfulCommands.incrementAndGet()
            } else {
                metrics.failedCommands.incrementAndGet()
            }
        }
    }

    private fun handleReconnect() {
        handleDisconnect()
        webSocket?.close(1000, "Reconnecting")
        scheduleReconnect()
    }

    private fun scheduleReconnect() {
        if (reconnectAttempts.incrementAndGet() <= maxReconnectAttempts) {
            onReconnecting?.invoke()
            mainHandler.postDelayed({
                establishConnection()
            }, reconnectDelayMs * reconnectAttempts.get())
        }
    }

    private fun startHeartbeat() {
        mainHandler.post(heartbeatRunnable)
    }

    private fun stopHeartbeat() {
        mainHandler.removeCallbacks(heartbeatRunnable)
    }

    private fun cancelPendingCommands() {
        pendingCommands.forEach { (messageId, request) ->
            request.timeoutJob?.cancel()
            metrics.failedCommands.incrementAndGet()
            onCommandTimeout?.invoke(messageId, request.command)
        }
        pendingCommands.clear()
    }

    fun sendMessage(message: String): Boolean {
        return if (isConnected) {
            webSocket?.send(message) ?: false
        } else {
            Log.w(TAG, "Attempted to send message while disconnected")
            false
        }
    }

    private fun getBatteryLevel(): Int {
        // Implement battery level check
        return -1 // Return -1 if not available
    }

    fun disconnect() {
        handleDisconnect()
        scope.cancel()
        webSocket?.close(1000, "Normal closure")
    }

    fun resetMetrics() {
        metrics.reset()
    }

    companion object {
        private const val TAG = "WebSocketClient"
    }
} 