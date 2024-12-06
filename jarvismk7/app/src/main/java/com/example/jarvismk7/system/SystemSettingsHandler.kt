package com.example.jarvismk7.system

import android.content.Context
import android.content.Intent
import android.provider.Settings
import android.widget.Toast

class SystemSettingsHandler(private val context: Context) {
    
    fun modifySystemSetting(setting: String, value: Int): Boolean {
        return try {
            if (Settings.System.canWrite(context)) {
                Settings.System.putInt(context.contentResolver, setting, value)
                true
            } else {
                requestWriteSettingsPermission()
                false
            }
        } catch (e: Exception) {
            Toast.makeText(context, "Failed to modify system setting: ${e.message}", Toast.LENGTH_SHORT).show()
            false
        }
    }

    fun modifySecureSettings(setting: String, value: String): Boolean {
        return try {
            // Try normal way first
            Settings.Secure.putString(context.contentResolver, setting, value)
            true
        } catch (e: SecurityException) {
            // If device is not rooted, show alternative method
            showAlternativeMethodForSecureSettings(setting)
            false
        }
    }

    private fun requestWriteSettingsPermission() {
        val intent = Intent(Settings.ACTION_MANAGE_WRITE_SETTINGS).apply {
            data = android.net.Uri.parse("package:${context.packageName}")
        }
        context.startActivity(intent)
    }

    private fun showAlternativeMethodForSecureSettings(setting: String) {
        // Open relevant system settings page for manual modification
        val intent = Intent(Settings.ACTION_SETTINGS)
        context.startActivity(intent)
        Toast.makeText(
            context,
            "Please modify $setting manually in Settings",
            Toast.LENGTH_LONG
        ).show()
    }
} 