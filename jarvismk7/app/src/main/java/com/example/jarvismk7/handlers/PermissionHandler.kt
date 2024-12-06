package com.example.jarvismk7.handlers

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
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
        Manifest.permission.WRITE_EXTERNAL_STORAGE
    )

    fun checkAndRequestPermissions(callback: (Boolean) -> Unit) {
        val pendingPermissions = requiredPermissions.filter { permission: String ->
            ContextCompat.checkSelfPermission(activity, permission) != PackageManager.PERMISSION_GRANTED
        }

        if (pendingPermissions.isEmpty()) {
            callback(true)
            return
        }

        ActivityCompat.requestPermissions(
            activity,
            pendingPermissions.toTypedArray(),
            PERMISSION_REQUEST_CODE
        )
    }

    companion object {
        const val PERMISSION_REQUEST_CODE = 123
    }
} 