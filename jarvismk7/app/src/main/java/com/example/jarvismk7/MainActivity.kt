package com.example.jarvismk7

import android.content.Intent
import android.os.Bundle
import android.widget.FrameLayout
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.PhotoCamera
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Warning
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import android.app.NotificationManager as AndroidNotificationManager
import android.os.PowerManager as AndroidPowerManager
import android.content.Context as AndroidContext
import androidx.compose.ui.graphics.Color as ComposeColor
import androidx.compose.foundation.background
import com.example.jarvismk7.ui.theme.AppTheme
import org.json.JSONArray
import org.json.JSONObject
import android.util.Log
import com.example.jarvismk7.commands.CommandExecutor
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import android.app.Activity
import android.os.Build
import com.example.jarvismk7.service.BackgroundService
import com.example.jarvismk7.permissions.PermissionHandler
import com.example.jarvismk7.system.SystemSettingsHandler
import com.example.jarvismk7.system.SystemOperationsHandler
import com.example.jarvismk7.package_manager.PackageManagerHandler
import com.example.jarvismk7.network.WebSocketClient
import com.example.jarvismk7.qr.QRCodeScanner
import java.io.File
import android.content.pm.ApplicationInfo
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import android.provider.Settings

class MainActivity : ComponentActivity() {
    private lateinit var permissionHandler: PermissionHandler
    private lateinit var systemSettingsHandler: SystemSettingsHandler
    private lateinit var packageManagerHandler: PackageManagerHandler
    private lateinit var systemOperationsHandler: SystemOperationsHandler
    private lateinit var qrCodeScanner: QRCodeScanner
    private lateinit var webSocketClient: WebSocketClient
    private lateinit var commandExecutor: CommandExecutor
    private lateinit var screenshotLauncher: ActivityResultLauncher<Intent>

    // Add default server configuration
    private val defaultServerUrl = "ws://10.0.2.2:3000"  // 10.0.2.2 is localhost from Android emulator
    private val defaultToken = "development"  // Default token for development

    @OptIn(ExperimentalMaterial3Api::class)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        permissionHandler = PermissionHandler(this)
        systemSettingsHandler = SystemSettingsHandler(this)
        packageManagerHandler = PackageManagerHandler(this)
        systemOperationsHandler = SystemOperationsHandler(this, this)
        webSocketClient = WebSocketClient()

        // Initialize CommandExecutor
        commandExecutor = CommandExecutor(
            context = this,
            systemOperations = systemOperationsHandler,
            systemSettings = systemSettingsHandler,
            packageManager = packageManagerHandler,
            webSocketClient = webSocketClient
        )

        // Connect to WebSocket server with default values
        startBackgroundService(defaultServerUrl, defaultToken)
        webSocketClient.connect(defaultServerUrl, defaultToken)

        // Set up WebSocket message handling
        webSocketClient.onMessageReceived = { message: String ->
            try {
                val json = JSONObject(message.toString())
                val messageId = json.optString("messageId", "")
                
                when (json.optString("type")) {
                    "execute" -> {
                        val command = json.getString("command")
                        val params = json.getJSONObject("params")
                        val success = commandExecutor.executeCommand(command, params)
                        
                        val response = JSONObject().apply {
                            put("type", "command_response")
                            put("messageId", messageId)
                            put("command", command)
                            put("success", success as Any)
                        }
                        webSocketClient.sendMessage(response.toString())
                    }
                    "get_notifications" -> {
                        val notifications = systemOperationsHandler.getActiveNotifications()
                        val response = JSONObject().apply {
                            put("type", "notifications_response")
                            put("messageId", messageId)
                            put("success", true)
                            put("notifications", notifications.map { notification ->
                                JSONObject().apply {
                                    put("id", notification.id)
                                    put("key", notification.key)
                                    put("packageName", notification.packageName)
                                    put("title", notification.notification.extras.getString("android.title"))
                                    put("text", notification.notification.extras.getString("android.text"))
                                }
                            })
                        }
                        webSocketClient.sendMessage(response.toString())
                    }
                    "get_installed_apps" -> {
                        val apps = packageManagerHandler.getInstalledApps()
                        val response = JSONObject().apply {
                            put("type", "installed_apps_response")
                            put("messageId", messageId)
                            put("success", true)
                            put("apps", JSONArray().apply {
                                apps.forEach { app: ApplicationInfo ->
                                    put(JSONObject().apply {
                                        put("packageName", app.packageName)
                                        put("appName", app.loadLabel(packageManagerHandler.context.packageManager).toString())
                                    })
                                }
                            })
                        }
                        webSocketClient.sendMessage(response.toString())
                    }
                    "take_screenshot" -> {
                        systemOperationsHandler.takeScreenshot { file: File? ->
                            val response = JSONObject().apply {
                                put("type", "screenshot_response")
                                put("messageId", messageId)
                                put("success", file != null)
                                put("message", if (file != null) "Screenshot taken successfully" else "Failed to take screenshot")
                            }
                            webSocketClient.sendMessage(response.toString())
                            
                            // If screenshot was successful, send it through command executor
                            file?.let { 
                                commandExecutor.handleFileUpload(it)
                            }
                        }
                    }
                    else -> {
                        // Send error response for unknown command
                        val response = JSONObject().apply {
                            put("type", "error_response")
                            put("messageId", messageId)
                            put("error", "Unknown command type: ${json.optString("type")}")
                        }
                        webSocketClient.sendMessage(response.toString())
                    }
                }
            } catch (e: Exception) {
                Log.e("MainActivity", "Error processing message", e)
                val response = JSONObject().apply {
                    put("type", "error_response")
                    put("error", "Error processing message: ${e.message}" as Any)
                }
                webSocketClient.sendMessage(response.toString())
            }
        }

        setContent {
            AppTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    Scaffold { innerPadding ->
                        MainContent(
                            modifier = Modifier.padding(innerPadding),
                            onRequestPermissions = { permissionHandler.checkAndRequestPermissions { granted: Boolean ->
                                if (granted) {
                                    // All permissions granted, initialize your services
                                }
                            } },
                            onTakeScreenshot = { 
                                systemOperationsHandler.takeScreenshot { file: File? -> 
                                    // Handle screenshot file
                                }
                            },
                            onShowNotifications = { 
                                val notifications = systemOperationsHandler.getActiveNotifications()
                                // Handle notifications
                            },
                            onStartQrScanner = { previewView ->
                                qrCodeScanner = QRCodeScanner(
                                    context = this,
                                    lifecycleOwner = this,
                                    previewView = previewView
                                ) { connectionInfo ->
                                    // Use scanned values or fall back to defaults
                                    val serverUrl = connectionInfo?.serverUrl ?: defaultServerUrl
                                    val token = connectionInfo?.token ?: defaultToken
                                    
                                    startBackgroundService(serverUrl, token)
                                    webSocketClient.connect(serverUrl, token)
                                }
                            }
                        )
                    }
                }
            }
        }

        // Initialize screenshot launcher
        initializeScreenshotLauncher()
    }

    private fun initializeScreenshotLauncher() {
        screenshotLauncher = registerForActivityResult(
            ActivityResultContracts.StartActivityForResult()
        ) { result ->
            if (result.resultCode == Activity.RESULT_OK) {
                systemOperationsHandler.handleScreenshotResult(result.resultCode, result.data)
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // Check permissions when activity resumes
        permissionHandler.checkAndRequestPermissions { granted: Boolean ->
            if (granted) {
                // All permissions granted, initialize your services
            }
        }
    }

    private fun startBackgroundService(serverUrl: String, token: String) {
        val serviceIntent = Intent(this, BackgroundService::class.java).apply {
            putExtra("serverUrl", serverUrl)
            putExtra("token", token)
        }
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent)
        } else {
            startService(serviceIntent)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainContent(
    modifier: Modifier = Modifier,
    onRequestPermissions: () -> Unit,
    onTakeScreenshot: () -> Unit,
    onShowNotifications: () -> Unit,
    onStartQrScanner: (PreviewView) -> Unit
) {
    var showPermissionDialog by remember { mutableStateOf(false) }
    val context = LocalContext.current
    
    // Get system services
    val notificationManager = context.getSystemService(AndroidContext.NOTIFICATION_SERVICE) as AndroidNotificationManager
    val powerManager = context.getSystemService(AndroidContext.POWER_SERVICE) as AndroidPowerManager

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        // Header section with settings button
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "JARVIS Control",
                style = MaterialTheme.typography.headlineMedium,
                color = MaterialTheme.colorScheme.onSurface
            )
            
            IconButton(onClick = { showPermissionDialog = true }) {
                Icon(
                    imageVector = Icons.Default.Settings,
                    contentDescription = "Settings",
                    tint = MaterialTheme.colorScheme.primary
                )
            }
        }

        // System Permissions Card
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 16.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.1f)
            )
        ) {
            Column(
                modifier = Modifier
                    .padding(16.dp)
                    .fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Warning,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.error
                    )
                    Text(
                        text = "Required System Permissions",
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.error
                    )
                }
                
                Button(
                    onClick = onRequestPermissions,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.error
                    )
                ) {
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.Lock,
                            contentDescription = null
                        )
                        Text("Grant Required Permissions")
                    }
                }
            }
        }

        // Actions section
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 16.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.primaryContainer
            )
        ) {
            Column(
                modifier = Modifier
                    .padding(16.dp)
                    .fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text(
                    text = "Quick Actions",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )
                
                Button(
                    onClick = onTakeScreenshot,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary
                    )
                ) {
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.PhotoCamera,
                            contentDescription = null
                        )
                        Text("Take Screenshot")
                    }
                }

                Button(
                    onClick = onShowNotifications,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary
                    )
                ) {
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.Notifications,
                            contentDescription = null
                        )
                        Text("Show Notifications")
                    }
                }
            }
        }

        // QR Scanner section
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surface
            )
        ) {
            Column(
                modifier = Modifier.padding(16.dp)
            ) {
                Text(
                    text = "QR Scanner",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.padding(bottom = 8.dp)
                )
                
                AndroidView(
                    modifier = Modifier
                        .fillMaxSize()
                        .clip(RoundedCornerShape(12.dp)),
                    factory = { context ->
                        PreviewView(context).apply {
                            layoutParams = FrameLayout.LayoutParams(
                                FrameLayout.LayoutParams.MATCH_PARENT,
                                FrameLayout.LayoutParams.MATCH_PARENT
                            )
                            scaleType = PreviewView.ScaleType.FILL_CENTER
                        }
                    }
                ) { previewView ->
                    onStartQrScanner(previewView)
                }
            }
        }
    }

    // Permission Dialog
    if (showPermissionDialog) {
        AlertDialog(
            onDismissRequest = { showPermissionDialog = false },
            title = {
                Text("System Permissions Required")
            },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    PermissionItem(
                        title = "Modify System Settings",
                        description = "Required to control system settings like brightness",
                        isGranted = Settings.System.canWrite(context)
                    )
                    PermissionItem(
                        title = "Background Apps",
                        description = "Required to run in background",
                        isGranted = !powerManager.isIgnoringBatteryOptimizations(context.packageName)
                    )
                    PermissionItem(
                        title = "Notification Access",
                        description = "Required to manage notifications",
                        isGranted = notificationManager.isNotificationPolicyAccessGranted
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = { showPermissionDialog = false }) {
                    Text("Close")
                }
            }
        )
    }
}

@Composable
private fun PermissionItem(
    title: String,
    description: String,
    isGranted: Boolean
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleSmall
            )
            Text(
                text = description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
            )
        }
        Icon(
            imageVector = if (isGranted) Icons.Default.Lock else Icons.Default.Warning,
            contentDescription = if (isGranted) "Granted" else "Not Granted",
            tint = if (isGranted) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
            modifier = Modifier.padding(start = 8.dp)
        )
    }
}