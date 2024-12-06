package com.example.jarvismk7.ui

import android.Manifest
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import com.example.jarvismk7.utils.BridgeManager
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.rememberPermissionState
import org.json.JSONObject

class QRScannerActivity : ComponentActivity() {
    private lateinit var bridgeManager: BridgeManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        bridgeManager = BridgeManager.getInstance(this)

        setContent {
            QRScannerScreen(
                onQRCodeScanned = { content ->
                    handleQRContent(content)
                }
            )
        }
    }

    private fun handleQRContent(content: String) {
        try {
            val data = JSONObject(content)
            val token = data.getString("token")
            bridgeManager.connect(token)
        } catch (e: Exception) {
            // Handle invalid QR code
        }
    }
}

@OptIn(ExperimentalPermissionsApi::class)
@Composable
fun QRScannerScreen(onQRCodeScanned: (String) -> Unit) {
    val cameraPermission = rememberPermissionState(Manifest.permission.CAMERA)
    
    LaunchedEffect(Unit) {
        cameraPermission.launchPermissionRequest()
    }

    // Implement camera preview and QR code scanning UI
} 