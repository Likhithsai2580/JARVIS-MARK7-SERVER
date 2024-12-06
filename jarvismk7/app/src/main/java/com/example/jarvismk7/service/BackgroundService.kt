package com.example.jarvismk7.service

import android.app.*
import android.content.Intent
import android.os.IBinder
import android.content.Context
import android.os.Build
import android.os.PowerManager
import android.content.BroadcastReceiver
import android.content.IntentFilter
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import androidx.core.app.NotificationCompat
import com.example.jarvismk7.MainActivity
import com.example.jarvismk7.R
import com.example.jarvismk7.network.WebSocketClient
import com.example.jarvismk7.executor.CommandExecutor
import com.example.jarvismk7.handlers.*
import kotlinx.coroutines.*
import org.json.JSONObject
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger

class BackgroundService : Service() {
    private lateinit var webSocketClient: WebSocketClient
    private lateinit var commandExecutor: CommandExecutor
    private lateinit var wakeLock: PowerManager.WakeLock
    private lateinit var connectivityManager: ConnectivityManager
    private lateinit var networkCallback: ConnectivityManager.NetworkCallback
    private val serviceScope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    
    private val CHANNEL_ID = "JarvisServiceChannel"
    private val NOTIFICATION_ID = 1
    private val WAKELOCK_TAG = "JarvisService:WakeLock"

    private var isRunning = AtomicBoolean(false)
    private var reconnectAttempts = AtomicInteger(0)
    private val maxReconnectAttempts = 5
    private var serverUrl: String? = null
    private var authToken: String? = null

    private val serviceMetrics = ServiceMetrics()

    inner class ServiceMetrics {
        var startTime: Long = 0
        var lastConnectedTime: Long = 0
        var totalUptime: Long = 0
        var disconnections: Int = 0
        var reconnections: Int = 0
        var lastError: String? = null
        
        fun onServiceStart() {
            startTime = System.currentTimeMillis()
        }

        fun onConnected() {
            lastConnectedTime = System.currentTimeMillis()
            reconnections++
        }

        fun onDisconnected() {
            if (lastConnectedTime > 0) {
                totalUptime += System.currentTimeMillis() - lastConnectedTime
            }
            disconnections++
        }

        fun getMetrics(): JSONObject = JSONObject().apply {
            put("uptime", totalUptime)
            put("disconnections", disconnections)
            put("reconnections", reconnections)
            put("lastError", lastError)
            put("runningTime", System.currentTimeMillis() - startTime)
        }
    }

    private val networkStateReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                ConnectivityManager.CONNECTIVITY_ACTION -> checkAndReconnect()
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        serviceMetrics.onServiceStart()
        createNotificationChannel()
        initializeWakeLock()
        initializeNetworkMonitoring()
        initializeHandlers()
        registerNetworkCallbacks()
    }

    private fun initializeWakeLock() {
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            WAKELOCK_TAG
        ).apply {
            setReferenceCounted(false)
        }
    }

    private fun initializeNetworkMonitoring() {
        connectivityManager = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        
        networkCallback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                checkAndReconnect()
            }

            override fun onLost(network: Network) {
                serviceMetrics.onDisconnected()
                updateNotification(false, "Network lost")
            }

            override fun onCapabilitiesChanged(
                network: Network,
                networkCapabilities: NetworkCapabilities
            ) {
                val unmetered = networkCapabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_METERED)
                val metrics = JSONObject().apply {
                    put("type", "networkChange")
                    put("unmetered", unmetered)
                }
                webSocketClient.sendMessage(metrics.toString())
            }
        }
    }

    private fun registerNetworkCallbacks() {
        val networkRequest = NetworkRequest.Builder()
            .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .build()
        connectivityManager.registerNetworkCallback(networkRequest, networkCallback)

        registerReceiver(
            networkStateReceiver,
            IntentFilter(ConnectivityManager.CONNECTIVITY_ACTION)
        )
    }

    private fun initializeHandlers() {
        val systemOperationsHandler = SystemOperationsHandler(this, this)
        val systemSettingsHandler = SystemSettingsHandler(this)
        val packageManagerHandler = PackageManagerHandler(this)
        
        webSocketClient = WebSocketClient().apply {
            onConnectionStateChanged = { isConnected ->
                if (isConnected) {
                    serviceMetrics.onConnected()
                    reconnectAttempts.set(0)
                } else {
                    serviceMetrics.onDisconnected()
                }
                updateNotification(isConnected)
            }
            onReconnecting = {
                updateNotification(false, "Reconnecting...")
            }
            onError = { type, message ->
                handleError(type, message)
            }
        }

        commandExecutor = CommandExecutor(
            this,
            systemOperationsHandler,
            systemSettingsHandler,
            packageManagerHandler,
            webSocketClient
        )

        startMetricsReporting()
    }

    private fun startMetricsReporting() {
        serviceScope.launch {
            while (isRunning.get()) {
                try {
                    val metrics = JSONObject().apply {
                        put("type", "serviceMetrics")
                        put("data", serviceMetrics.getMetrics())
                    }
                    webSocketClient.sendMessage(metrics.toString())
                } catch (e: Exception) {
                    handleError("METRICS_ERROR", e.message)
                }
                delay(30000) // Report every 30 seconds
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        wakeLock.acquire(10*60*1000L) // 10 minutes
        isRunning.set(true)
        
        val notification = createNotification()
        startForeground(NOTIFICATION_ID, notification)

        intent?.let {
            serverUrl = it.getStringExtra("serverUrl")
            authToken = it.getStringExtra("token")
            if (serverUrl != null && authToken != null) {
                connectToServer()
            }
        }

        return START_STICKY
    }

    private fun connectToServer() {
        if (!isNetworkAvailable()) {
            updateNotification(false, "Waiting for network...")
            return
        }

        serviceScope.launch {
            try {
                webSocketClient.connect(serverUrl!!, authToken!!)
            } catch (e: Exception) {
                handleError("CONNECTION_ERROR", e.message)
                scheduleReconnect()
            }
        }
    }

    private fun checkAndReconnect() {
        if (isRunning.get() && !webSocketClient.isConnected() && isNetworkAvailable()) {
            scheduleReconnect()
        }
    }

    private fun scheduleReconnect() {
        if (reconnectAttempts.incrementAndGet() <= maxReconnectAttempts) {
            serviceScope.launch {
                delay(getBackoffDelay())
                connectToServer()
            }
        } else {
            handleError("MAX_RECONNECT", "Maximum reconnection attempts reached")
        }
    }

    private fun getBackoffDelay(): Long {
        return (1000L * (1 shl reconnectAttempts.get().coerceAtMost(6))) // Exponential backoff capped at 64 seconds
    }

    private fun isNetworkAvailable(): Boolean {
        val networkCapabilities = connectivityManager.activeNetwork?.let {
            connectivityManager.getNetworkCapabilities(it)
        }
        return networkCapabilities?.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) == true
    }

    private fun handleError(type: String, message: String?) {
        serviceMetrics.lastError = "$type: $message"
        Log.e(TAG, "Service error: $type - $message")
        updateNotification(false, "Error: $type")
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = "JARVIS Service"
            val descriptionText = "Maintains connection with JARVIS server"
            val importance = NotificationManager.IMPORTANCE_LOW
            val channel = NotificationChannel(CHANNEL_ID, name, importance).apply {
                description = descriptionText
                setShowBadge(false)
            }
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(
        isConnected: Boolean = false,
        status: String = "Initializing..."
    ): Notification {
        val pendingIntent: PendingIntent =
            Intent(this, MainActivity::class.java).let { notificationIntent ->
                PendingIntent.getActivity(
                    this, 0, notificationIntent,
                    PendingIntent.FLAG_IMMUTABLE
                )
            }

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("JARVIS Service")
            .setContentText(status)
            .setSmallIcon(if (isConnected) R.drawable.ic_connected else R.drawable.ic_disconnected)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun updateNotification(isConnected: Boolean, status: String? = null) {
        val notification = createNotification(
            isConnected,
            status ?: if (isConnected) "Connected" else "Disconnected"
        )
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        notificationManager.notify(NOTIFICATION_ID, notification)
    }

    override fun onBind(intent: Intent): IBinder? = null

    override fun onDestroy() {
        super.onDestroy()
        isRunning.set(false)
        serviceScope.cancel()
        commandExecutor.cleanup()
        webSocketClient.disconnect()
        
        try {
            unregisterReceiver(networkStateReceiver)
            connectivityManager.unregisterNetworkCallback(networkCallback)
        } catch (e: Exception) {
            Log.e(TAG, "Error unregistering receivers", e)
        }

        if (wakeLock.isHeld) {
            wakeLock.release()
        }
    }

    companion object {
        private const val TAG = "BackgroundService"
    }
} 