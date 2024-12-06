package com.example.jarvismk7.system

import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.app.Activity
import android.app.NotificationManager
import android.service.notification.StatusBarNotification
import android.view.WindowManager
import android.app.PendingIntent
import android.os.Handler
import android.os.Looper
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import android.media.projection.MediaProjectionManager

class SystemOperationsHandler(
    private val context: Context,
    private val activity: Activity
) {
    private val activityManager = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
    private val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    private val mediaProjectionManager = context.getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
    
    // Add callback properties
    var onNotificationsReceived: ((List<StatusBarNotification>) -> Unit)? = null
    var onScreenshotTaken: ((File?) -> Unit)? = null

    fun launchApp(packageName: String) {
        try {
            val intent = context.packageManager.getLaunchIntentForPackage(packageName)
            intent?.let {
                it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(it)
            }
        } catch (e: Exception) {
            // Handle exception
        }
    }

    fun closeApp(packageName: String) {
        try {
            activityManager.killBackgroundProcesses(packageName)
            // For newer Android versions, guide user to manually force stop
            val intent = Intent(android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                data = android.net.Uri.parse("package:$packageName")
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
        } catch (e: Exception) {
            // Handle exception
        }
    }

    // Screenshot functionality
    private var screenshotCallback: ((File?) -> Unit)? = null
    private val SCREENSHOT_REQUEST_CODE = 100

    fun takeScreenshot(onScreenshotTaken: (File?) -> Unit) {
        screenshotCallback = onScreenshotTaken
        this.onScreenshotTaken = onScreenshotTaken
        val mediaProjectionManager = context.getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        activity.startActivityForResult(
            mediaProjectionManager.createScreenCaptureIntent(),
            SCREENSHOT_REQUEST_CODE
        )
    }

    fun handleScreenshotResult(resultCode: Int, data: Intent?) {
        if (resultCode == Activity.RESULT_OK && data != null) {
            // Implement screenshot capture using MediaProjection
            captureScreen(data)
        } else {
            screenshotCallback?.invoke(null)
        }
    }

    private fun captureScreen(data: Intent) {
        // Implementation of screen capture using MediaProjection
        // This is a simplified version - you'll need to implement the actual screen capture logic
        val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
        val screenshotFile = File(context.getExternalFilesDir(null), "Screenshot_$timestamp.png")
        
        // Actual implementation would use MediaProjection to capture the screen
        // For now, we'll just create an empty file
        screenshotFile.createNewFile()
        screenshotCallback?.invoke(screenshotFile)
    }

    // Notification handling
    fun getActiveNotifications(): List<StatusBarNotification> {
        val notifications = if (notificationManager.isNotificationPolicyAccessGranted) {
            notificationManager.activeNotifications.toList()
        } else {
            // Request notification access
            val intent = Intent(android.provider.Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
            context.startActivity(intent)
            emptyList()
        }
        onNotificationsReceived?.invoke(notifications)
        return notifications
    }

    fun clearNotification(key: String) {
        try {
            notificationManager.cancelNotification(key)
        } catch (e: Exception) {
            // Handle exception
        }
    }

    fun clearAllNotifications() {
        notificationManager.cancelAll()
    }

    private fun NotificationManager.cancelNotification(key: String) {
        val parts = key.split("|")
        if (parts.size == 2) {
            cancel(parts[0], parts[1].toInt())
        }
    }
} 