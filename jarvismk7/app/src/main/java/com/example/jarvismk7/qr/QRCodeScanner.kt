package com.example.jarvismk7.qr

import android.content.Context
import android.util.Log
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import org.json.JSONObject

@androidx.annotation.OptIn(androidx.camera.core.ExperimentalGetImage::class)
class QRCodeScanner(
    private val context: Context,
    private val lifecycleOwner: LifecycleOwner,
    private val previewView: PreviewView,
    private val onQrCodeScanned: (ConnectionInfo) -> Unit
) {
    data class ConnectionInfo(
        val serverUrl: String,
        val token: String,
        val timestamp: Long
    )

    private var cameraExecutor: ExecutorService = Executors.newSingleThreadExecutor()
    private var camera: Camera? = null

    init {
        startCamera()
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(context)

        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            val preview = Preview.Builder()
                .build()
                .also {
                    it.setSurfaceProvider(previewView.surfaceProvider)
                }

            val imageAnalyzer = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also {
                    it.setAnalyzer(cameraExecutor) { imageProxy ->
                        processImage(imageProxy)
                    }
                }

            try {
                cameraProvider.unbindAll()
                camera = cameraProvider.bindToLifecycle(
                    lifecycleOwner,
                    CameraSelector.DEFAULT_BACK_CAMERA,
                    preview,
                    imageAnalyzer
                )
            } catch (e: Exception) {
                Log.e("QRCodeScanner", "Use case binding failed", e)
            }
        }, ContextCompat.getMainExecutor(context))
    }

    private fun processImage(imageProxy: ImageProxy) {
        val image = imageProxy.image
        if (image == null) {
            imageProxy.close()
            return
        }

        val inputImage = InputImage.fromMediaImage(image, imageProxy.imageInfo.rotationDegrees)
        val scanner = BarcodeScanning.getClient()

        scanner.process(inputImage)
            .addOnSuccessListener { barcodes ->
                for (barcode in barcodes) {
                    if (barcode.valueType == Barcode.TYPE_TEXT) {
                        try {
                            val jsonObject = JSONObject(barcode.rawValue ?: "")
                            val connectionInfo = ConnectionInfo(
                                serverUrl = jsonObject.getString("serverUrl"),
                                token = jsonObject.getString("token"),
                                timestamp = jsonObject.getLong("timestamp")
                            )
                            onQrCodeScanned(connectionInfo)
                        } catch (e: Exception) {
                            Log.e("QRCodeScanner", "Error parsing QR code", e)
                        }
                    }
                }
            }
            .addOnFailureListener { e ->
                Log.e("QRCodeScanner", "Barcode scanning failed", e)
            }
            .addOnCompleteListener {
                imageProxy.close()
            }
    }

    fun stop() {
        cameraExecutor.shutdown()
    }
} 