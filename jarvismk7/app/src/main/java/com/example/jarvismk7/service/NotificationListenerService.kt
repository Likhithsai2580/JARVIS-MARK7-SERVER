package com.example.jarvismk7.service

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import org.json.JSONObject
import com.example.jarvismk7.network.WebSocketClient

class NotificationListenerService : NotificationListenerService() {
    private var webSocketClient: WebSocketClient? = null

    override fun onCreate() {
        super.onCreate()
        webSocketClient = WebSocketClient()
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val notification = sbn.notification
        val extras = notification.extras
        
        val notificationData = JSONObject().apply {
            put("type", "notification_posted")
            put("packageName", sbn.packageName)
            put("title", extras.getString("android.title"))
            put("text", extras.getString("android.text"))
            put("postTime", sbn.postTime)
            put("key", sbn.key)
        }
        
        webSocketClient?.sendMessage(notificationData.toString())
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {
        val notificationData = JSONObject().apply {
            put("type", "notification_removed")
            put("packageName", sbn.packageName)
            put("key", sbn.key)
        }
        
        webSocketClient?.sendMessage(notificationData.toString())
    }

    override fun onDestroy() {
        super.onDestroy()
        webSocketClient?.disconnect()
        webSocketClient = null
    }
} 