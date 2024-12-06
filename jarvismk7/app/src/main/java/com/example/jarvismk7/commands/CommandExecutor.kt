package com.example.jarvismk7.commands

import android.content.Context
import com.example.jarvismk7.system.SystemOperationsHandler
import com.example.jarvismk7.system.SystemSettingsHandler
import com.example.jarvismk7.package_manager.PackageManagerHandler
import org.json.JSONObject
import java.io.File
import android.util.Log
import com.example.jarvismk7.network.WebSocketClient

class CommandExecutor(
    private val context: Context,
    private val systemOperations: SystemOperationsHandler,
    private val systemSettings: SystemSettingsHandler,
    private val packageManager: PackageManagerHandler,
    private val webSocketClient: WebSocketClient
) {
    fun executeCommand(command: String, params: JSONObject): Boolean {
        return when (command) {
            "LAUNCH_APP" -> {
                val packageName = params.getString("packageName")
                systemOperations.launchApp(packageName)
                true
            }
            "CLOSE_APP" -> {
                val packageName = params.getString("packageName")
                systemOperations.closeApp(packageName)
                true
            }
            "TAKE_SCREENSHOT" -> {
                systemOperations.takeScreenshot { file ->
                    // Handle screenshot file
                }
                true
            }
            "CLEAR_NOTIFICATIONS" -> {
                systemOperations.clearAllNotifications()
                true
            }
            "INSTALL_APK" -> {
                val apkPath = params.getString("path")
                packageManager.installAPK(java.io.File(apkPath))
                true
            }
            "UNINSTALL_APP" -> {
                val packageName = params.getString("packageName")
                packageManager.uninstallApp(packageName)
                true
            }
            "MODIFY_SYSTEM_SETTING" -> {
                val setting = params.getString("setting")
                val value = params.getInt("value")
                systemSettings.modifySystemSetting(setting, value)
            }
            "UPLOAD_FILE" -> {
                val filePath = params.getString("path")
                uploadFile(File(filePath))
                true
            }
            "DOWNLOAD_FILE" -> {
                val fileName = params.getString("fileName")
                downloadFile(fileName)
                true
            }
            else -> false
        }
    }

    fun handleFileUpload(file: File) {
        try {
            if (!file.exists()) return
            
            val fileData = file.readBytes().toBase64()
            val message = JSONObject().apply {
                put("type", "file-transfer")
                put("fileData", fileData)
                put("fileName", file.name)
                put("type", "upload")
            }
            webSocketClient.sendMessage(message.toString())
            
            // Send upload started response
            val startResponse = JSONObject().apply {
                put("type", "file_upload_started")
                put("fileName", file.name)
            }
            webSocketClient.sendMessage(startResponse.toString())
            
            // After successful upload
            val successResponse = JSONObject().apply {
                put("type", "file_upload_complete")
                put("fileName", file.name)
                put("success", true)
            }
            webSocketClient.sendMessage(successResponse.toString())
        } catch (e: Exception) {
            // Send error response
            val errorResponse = JSONObject().apply {
                put("type", "file_upload_error")
                put("fileName", file.name)
                put("error", e.message)
            }
            webSocketClient.sendMessage(errorResponse.toString())
        }
    }

    private fun uploadFile(file: File) {
        handleFileUpload(file)
    }

    private fun downloadFile(fileName: String) {
        val message = JSONObject().apply {
            put("type", "file-transfer")
            put("fileName", fileName)
            put("type", "download")
        }
        webSocketClient.sendMessage(message.toString())
    }

    private fun ByteArray.toBase64(): String {
        return android.util.Base64.encodeToString(this, android.util.Base64.DEFAULT)
    }
} 