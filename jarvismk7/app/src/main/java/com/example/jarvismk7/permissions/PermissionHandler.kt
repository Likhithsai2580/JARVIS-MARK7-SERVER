package com.example.jarvismk7.permissions

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.PowerManager
import android.provider.Settings
import android.app.NotificationManager
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class PermissionHandler(private val activity: Activity) {
    
    private val requiredPermissions = arrayOf(
        Manifest.permission.READ_CONTACTS,
        Manifest.permission.WRITE_CONTACTS,
        Manifest.permission.READ_CALL_LOG,
        Manifest.permission.WRITE_CALL_LOG,
        Manifest.permission.CALL_PHONE,
        Manifest.permission.SEND_SMS,
        Manifest.permission.READ_SMS,
        Manifest.permission.READ_PHONE_STATE,
        Manifest.permission.READ_EXTERNAL_STORAGE,
        Manifest.permission.WRITE_EXTERNAL_STORAGE,
        Manifest.permission.CAMERA
    )

    private val specialPermissions = arrayOf(
        Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
        Settings.ACTION_MANAGE_WRITE_SETTINGS,
        Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES
    )

    fun checkAndRequestPermissions(onResult: (Boolean) -> Unit) {
        // First check system permissions
        if (!Settings.System.canWrite(activity)) {
            requestWriteSettingsPermission()
            return
        }

        // Check notification access
        val notificationManager = activity.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (!notificationManager.isNotificationPolicyAccessGranted) {
            requestNotificationAccess()
            return
        }

        // Check battery optimization
        val powerManager = activity.getSystemService(Context.POWER_SERVICE) as PowerManager
        if (!powerManager.isIgnoringBatteryOptimizations(activity.packageName)) {
            requestBatteryOptimizationExemption()
            return
        }

        // Then check regular permissions
        val missingPermissions = requiredPermissions.filter {
            ContextCompat.checkSelfPermission(activity, it) != PackageManager.PERMISSION_GRANTED
        }.toTypedArray()

        if (missingPermissions.isEmpty()) {
            onResult(true)
        } else {
            ActivityCompat.requestPermissions(activity, missingPermissions, PERMISSION_REQUEST_CODE)
        }
    }

    private fun requestOverlayPermission() {
        val intent = Intent(
            Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
            Uri.parse("package:${activity.packageName}")
        )
        activity.startActivity(intent)
    }

    private fun requestWriteSettingsPermission() {
        val intent = Intent(
            Settings.ACTION_MANAGE_WRITE_SETTINGS,
            Uri.parse("package:${activity.packageName}")
        )
        activity.startActivity(intent)
    }

    private fun requestBatteryOptimizationExemption() {
        val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
            data = Uri.parse("package:${activity.packageName}")
        }
        activity.startActivity(intent)
    }

    private fun requestNotificationAccess() {
        val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
        activity.startActivity(intent)
    }

    companion object {
        const val PERMISSION_REQUEST_CODE = 123
    }
} 