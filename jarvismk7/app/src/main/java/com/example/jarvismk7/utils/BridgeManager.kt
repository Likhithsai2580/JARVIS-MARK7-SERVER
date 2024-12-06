package com.example.jarvismk7.utils

import android.content.Context
import android.content.Intent
import com.example.jarvismk7.services.BridgeService
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

class BridgeManager private constructor(private val context: Context) {
    private val _connectionState = MutableStateFlow<ConnectionState>(ConnectionState.Disconnected)
    val connectionState: StateFlow<ConnectionState> = _connectionState

    fun connect(token: String) {
        _connectionState.value = ConnectionState.Connecting
        val intent = Intent(context, BridgeService::class.java).apply {
            putExtra(EXTRA_TOKEN, token)
        }
        context.startService(intent)
    }

    fun disconnect() {
        context.stopService(Intent(context, BridgeService::class.java))
        _connectionState.value = ConnectionState.Disconnected
    }

    sealed class ConnectionState {
        object Disconnected : ConnectionState()
        object Connecting : ConnectionState()
        object Connected : ConnectionState()
        data class Error(val message: String) : ConnectionState()
    }

    companion object {
        const val EXTRA_TOKEN = "connection_token"
        
        @Volatile
        private var instance: BridgeManager? = null

        fun getInstance(context: Context): BridgeManager {
            return instance ?: synchronized(this) {
                instance ?: BridgeManager(context.applicationContext).also { instance = it }
            }
        }
    }
} 