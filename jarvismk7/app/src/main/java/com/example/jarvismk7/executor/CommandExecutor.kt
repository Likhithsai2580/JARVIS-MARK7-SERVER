package com.example.jarvismk7.executor

import android.content.Context
import android.util.Log
import com.example.jarvismk7.handlers.*
import com.example.jarvismk7.network.WebSocketClient
import org.json.JSONObject
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.LinkedBlockingQueue
import kotlinx.coroutines.*
import java.util.UUID
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import androidx.collection.LruCache

class CommandExecutor(
    private val context: Context,
    private val systemOperations: SystemOperationsHandler,
    private val systemSettings: SystemSettingsHandler,
    private val packageManager: PackageManagerHandler,
    private val webSocketClient: WebSocketClient
) {
    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    private val commandQueue = LinkedBlockingQueue<Command>()
    private val pendingCommands = ConcurrentHashMap<String, Command>()
    private var isProcessing = false
    private val commandMetrics = CommandMetrics()
    private val resultCache = CommandResultCache(50) // Cache last 50 results

    init {
        startCommandProcessor()
        startMetricsReporter()
    }

    data class Command(
        val messageId: String,
        val name: String,
        val params: JSONObject,
        val timestamp: Long = System.currentTimeMillis(),
        var retryCount: Int = 0,
        var lastError: String? = null
    )

    inner class CommandMetrics {
        val totalCommands = AtomicInteger(0)
        val successfulCommands = AtomicInteger(0)
        val failedCommands = AtomicInteger(0)
        val averageExecutionTime = AtomicInteger(0)
        val commandsPerSecond = AtomicInteger(0)
        private var lastResetTime = System.currentTimeMillis()

        fun recordExecution(executionTime: Long, success: Boolean) {
            if (success) {
                successfulCommands.incrementAndGet()
            } else {
                failedCommands.incrementAndGet()
            }
            
            val currentAvg = averageExecutionTime.get()
            val newAvg = if (currentAvg == 0) {
                executionTime.toInt()
            } else {
                ((currentAvg + executionTime) / 2).toInt()
            }
            averageExecutionTime.set(newAvg)

            val now = System.currentTimeMillis()
            if (now - lastResetTime >= 1000) {
                commandsPerSecond.set(0)
                lastResetTime = now
            }
            commandsPerSecond.incrementAndGet()
        }

        fun reset() {
            totalCommands.set(0)
            successfulCommands.set(0)
            failedCommands.set(0)
            averageExecutionTime.set(0)
            commandsPerSecond.set(0)
        }
    }

    inner class CommandResultCache(maxSize: Int) : LruCache<String, JSONObject>(maxSize) {
        fun getCacheKey(command: String, params: JSONObject): String {
            return "$command:${params.toString()}"
        }
    }

    private fun startCommandProcessor() {
        scope.launch {
            while (true) {
                try {
                    if (!isProcessing) {
                        val command = commandQueue.poll()
                        if (command != null) {
                            isProcessing = true
                            val startTime = System.currentTimeMillis()
                            try {
                                executeCommandInternal(command)
                                val executionTime = System.currentTimeMillis() - startTime
                                commandMetrics.recordExecution(executionTime, true)
                            } catch (e: Exception) {
                                val executionTime = System.currentTimeMillis() - startTime
                                commandMetrics.recordExecution(executionTime, false)
                                handleCommandError(command, e)
                            } finally {
                                isProcessing = false
                            }
                        }
                    }
                    delay(50) // Reduced from 100ms to improve responsiveness
                } catch (e: Exception) {
                    Log.e(TAG, "Error in command processor", e)
                    isProcessing = false
                }
            }
        }
    }

    private fun startMetricsReporter() {
        scope.launch {
            while (true) {
                try {
                    val metrics = JSONObject().apply {
                        put("totalCommands", commandMetrics.totalCommands.get())
                        put("successfulCommands", commandMetrics.successfulCommands.get())
                        put("failedCommands", commandMetrics.failedCommands.get())
                        put("averageExecutionTime", commandMetrics.averageExecutionTime.get())
                        put("commandsPerSecond", commandMetrics.commandsPerSecond.get())
                        put("queueSize", commandQueue.size)
                        put("pendingCommands", pendingCommands.size)
                    }
                    webSocketClient.sendMessage(JSONObject().apply {
                        put("type", "metrics")
                        put("data", metrics)
                    }.toString())
                } catch (e: Exception) {
                    Log.e(TAG, "Error reporting metrics", e)
                }
                delay(5000) // Report every 5 seconds
            }
        }
    }

    fun executeCommand(command: String, params: JSONObject): Boolean {
        val messageId = UUID.randomUUID().toString()
        val cmd = Command(messageId, command, params)
        
        // Check cache first
        val cacheKey = resultCache.getCacheKey(command, params)
        val cachedResult = resultCache.get(cacheKey)
        if (cachedResult != null && isCacheableCommand(command)) {
            sendCommandResponse(messageId, cachedResult)
            return true
        }

        pendingCommands[messageId] = cmd
        commandMetrics.totalCommands.incrementAndGet()
        return commandQueue.offer(cmd)
    }

    private fun isCacheableCommand(command: String): Boolean {
        return when (command.uppercase()) {
            "GET_INSTALLED_APPS", "GET_DEVICE_INFO", "GET_SYSTEM_INFO" -> true
            else -> false
        }
    }

    private suspend fun executeCommandInternal(command: Command) = withContext(Dispatchers.IO) {
        try {
            val result = when (command.name.uppercase()) {
                "LAUNCH_APP" -> launchApp(command.params)
                "TAKE_SCREENSHOT" -> takeScreenshot()
                "GET_NOTIFICATIONS" -> getNotifications()
                "CLEAR_NOTIFICATION" -> clearNotification(command.params)
                "TOGGLE_SETTING" -> toggleSetting(command.params)
                "GET_INSTALLED_APPS" -> getInstalledApps()
                "GET_RUNNING_APPS" -> getRunningApps()
                "STOP_APP" -> stopApp(command.params)
                "SET_VOLUME" -> setVolume(command.params)
                "GET_BATTERY_INFO" -> getBatteryInfo()
                "EXECUTE_SHELL_COMMAND" -> executeShellCommand(command.params)
                else -> throw IllegalArgumentException("Unknown command: ${command.name}")
            }

            // Cache result if applicable
            if (isCacheableCommand(command.name)) {
                val cacheKey = resultCache.getCacheKey(command.name, command.params)
                resultCache.put(cacheKey, result)
            }

            sendCommandResponse(command.messageId, result)
        } catch (e: Exception) {
            Log.e(TAG, "Error executing command: ${command.name}", e)
            handleCommandError(command, e)
        } finally {
            pendingCommands.remove(command.messageId)
        }
    }

    private fun handleCommandError(command: Command, error: Exception) {
        val shouldRetry = shouldRetryCommand(command, error)
        if (shouldRetry) {
            retryCommand(command)
        } else {
            val errorResponse = JSONObject().apply {
                put("error", error.message)
                put("command", command.name)
                put("retries", command.retryCount)
            }
            sendCommandResponse(command.messageId, errorResponse)
        }
    }

    private fun shouldRetryCommand(command: Command, error: Exception): Boolean {
        return when {
            command.retryCount >= MAX_RETRIES -> false
            error is SecurityException -> false
            error is IllegalArgumentException -> false
            else -> true
        }
    }

    private fun retryCommand(command: Command) {
        command.retryCount++
        scope.launch {
            delay(RETRY_DELAY_MS * command.retryCount)
            commandQueue.offer(command)
        }
    }

    private fun sendCommandResponse(messageId: String, result: JSONObject) {
        val response = JSONObject().apply {
            put("type", "commandResponse")
            put("messageId", messageId)
            put("result", result)
            put("timestamp", System.currentTimeMillis())
        }
        webSocketClient.sendMessage(response.toString())
    }

    private suspend fun launchApp(params: JSONObject): JSONObject = withContext(Dispatchers.IO) {
        val packageName = params.getString("packageName")
        val success = packageManager.launchApp(packageName)
        JSONObject().put("success", success)
    }

    private suspend fun takeScreenshot(): JSONObject = withContext(Dispatchers.IO) {
        val screenshotData = systemOperations.takeScreenshot()
        JSONObject().put("data", screenshotData)
    }

    private fun getNotifications(): JSONObject {
        val notifications = systemOperations.getActiveNotifications()
        return JSONObject().put("notifications", notifications)
    }

    private fun clearNotification(params: JSONObject): JSONObject {
        val notificationId = params.getInt("notificationId")
        val success = systemOperations.clearNotification(notificationId)
        return JSONObject().put("success", success)
    }

    private fun toggleSetting(params: JSONObject): JSONObject {
        val setting = params.getString("setting")
        val value = params.getBoolean("value")
        val success = systemSettings.toggleSetting(setting, value)
        return JSONObject().put("success", success)
    }

    private fun getInstalledApps(): JSONObject {
        val apps = packageManager.getInstalledApps()
        return JSONObject().put("apps", apps)
    }

    private fun getRunningApps(): JSONObject {
        val apps = systemOperations.getRunningApps()
        return JSONObject().put("apps", apps)
    }

    private suspend fun stopApp(params: JSONObject): JSONObject = withContext(Dispatchers.IO) {
        val packageName = params.getString("packageName")
        val success = systemOperations.stopApp(packageName)
        JSONObject().put("success", success)
    }

    private fun setVolume(params: JSONObject): JSONObject {
        val streamType = params.getInt("streamType")
        val volume = params.getInt("volume")
        val success = systemSettings.setVolume(streamType, volume)
        return JSONObject().put("success", success)
    }

    private fun getBatteryInfo(): JSONObject {
        val batteryInfo = systemOperations.getBatteryInfo()
        return JSONObject().put("batteryInfo", batteryInfo)
    }

    private suspend fun executeShellCommand(params: JSONObject): JSONObject = withContext(Dispatchers.IO) {
        val command = params.getString("command")
        val output = systemOperations.executeShellCommand(command)
        JSONObject().put("output", output)
    }

    fun cleanup() {
        scope.cancel()
        commandQueue.clear()
        pendingCommands.clear()
        resultCache.evictAll()
        commandMetrics.reset()
    }

    companion object {
        private const val TAG = "CommandExecutor"
        private const val MAX_RETRIES = 3
        private const val RETRY_DELAY_MS = 1000L
    }
} 