# Android Bridge Protocol Specification

This document describes the WebSocket protocol used for communication between the Android Bridge Server and Android client devices.

## Connection

1. Connect to WebSocket endpoint: `ws://<server>/ws/<device_id>`
2. After connection, server will request device capabilities
3. Client should start sending heartbeats every 30 seconds

## Message Format

All messages are JSON objects with the following base structure:
```json
{
    "type": "message_type",
    "data": {
        // Message specific data
    }
}
```

## Client -> Server Messages

### Heartbeat
```json
{
    "type": "heartbeat",
    "data": {
        "battery_level": 85,
        "running_apps": ["com.example.app1", "com.example.app2"],
        "system_stats": {
            "cpu_usage": 45,
            "memory_available": 1024,
            "storage_free": 5000
        }
    }
}
```

### Capabilities Response
```json
{
    "type": "capabilities",
    "data": {
        "capabilities": [
            "app_launch",
            "app_stop",
            "screenshot",
            "input_text",
            "tap",
            "swipe",
            "back",
            "home",
            "recent",
            "volume",
            "brightness",
            "notification"
        ],
        "screen_size": {
            "width": 1080,
            "height": 1920
        },
        "android_version": "12",
        "device_model": "Pixel 6"
    }
}
```

### Command Response
```json
{
    "type": "response",
    "data": {
        "status": "success",
        "command_type": "original_command_type",
        "result": {
            // Command specific result data
        }
    }
}
```

### Error Response
```json
{
    "type": "error",
    "data": {
        "error": "Error message",
        "command_type": "original_command_type"
    }
}
```

## Server -> Client Commands

### App Launch
```json
{
    "type": "app_launch",
    "data": {
        "package_name": "com.example.app",
        "activity": "MainActivity",
        "extras": {
            "key1": "value1"
        }
    }
}
```

### App Stop
```json
{
    "type": "app_stop",
    "data": {
        "package_name": "com.example.app"
    }
}
```

### Get Screenshot
```json
{
    "type": "get_screenshot",
    "data": {
        "format": "png",
        "quality": 80
    }
}
```

### Input Text
```json
{
    "type": "input_text",
    "data": {
        "text": "Hello World"
    }
}
```

### Tap
```json
{
    "type": "tap",
    "data": {
        "x": 500,
        "y": 800
    }
}
```

### Swipe
```json
{
    "type": "swipe",
    "data": {
        "start_x": 100,
        "start_y": 500,
        "end_x": 600,
        "end_y": 500,
        "duration": 300
    }
}
```

### Navigation Commands
```json
{
    "type": "back",
    "data": {}
}
```
```json
{
    "type": "home",
    "data": {}
}
```
```json
{
    "type": "recent",
    "data": {}
}
```

### Volume Control
```json
{
    "type": "volume",
    "data": {
        "stream": "music",
        "level": 7
    }
}
```

### Brightness Control
```json
{
    "type": "brightness",
    "data": {
        "level": 80,
        "auto": false
    }
}
```

### Notification
```json
{
    "type": "notification",
    "data": {
        "title": "Title",
        "message": "Message content",
        "priority": "normal",
        "actions": [
            {
                "title": "Action 1",
                "id": "action1"
            }
        ]
    }
}
```

## Error Handling

1. If a command fails, respond with an error message
2. If WebSocket connection is lost, client should attempt to reconnect
3. If device becomes busy, it should complete current command before accepting new ones

## Security Considerations

1. Use HTTPS/WSS in production
2. Implement authentication for device registration
3. Validate all command parameters
4. Rate limit commands per device
5. Sanitize all input data 