# JARVIS Control Server Documentation

## Device Connection Process

1. Generate QR Code:
```http
GET /api/generate-connection-code
```

Response:
```json
{
    "qrCode": {
        "server": "wss://your-server.com",
        "token": "unique-secure-token",
        "timestamp": 1648372847000
    }
}
```

2. Scan QR Code with Android App
The Android app scans this QR code and establishes a WebSocket connection using the provided token.

3. Authenticate Connection:
```json
{
    "type": "authenticate",
    "token": "unique-secure-token"
}
```

4. Send Commands:
```json
{
    "type": "command",
    "token": "unique-secure-token",
    "command": "COMMAND_NAME",
    "params": {
        // command specific parameters
    }
}
```

## Security Notes
- QR codes are valid for 5 minutes only
- Each token is unique and can only be used by one device
- Tokens are invalidated after disconnection

## Available Commands

### App Management

#### LAUNCH_APP
Launches an application by package name.
```json
{
    "command": "LAUNCH_APP",
    "params": {
        "packageName": "com.example.app"
    }
}
```

#### CLOSE_APP
Closes/force stops an application.
```json
{
    "command": "CLOSE_APP",
    "params": {
        "packageName": "com.example.app"
    }
}
```

### System Operations

#### TAKE_SCREENSHOT
Takes a screenshot of the current screen.
```json
{
    "command": "TAKE_SCREENSHOT",
    "params": {}
}
```

#### CLEAR_NOTIFICATIONS
Clears all notifications.
```json
{
    "command": "CLEAR_NOTIFICATIONS",
    "params": {}
}
```

### Package Management

#### INSTALL_APK
Installs an APK from a specified path.
```json
{
    "command": "INSTALL_APK",
    "params": {
        "path": "/storage/emulated/0/Download/app.apk"
    }
}
```

#### UNINSTALL_APP
Uninstalls an application by package name.
```json
{
    "command": "UNINSTALL_APP",
    "params": {
        "packageName": "com.example.app"
    }
}
```

### System Settings

#### MODIFY_SYSTEM_SETTING
Modifies a system setting.
```json
{
    "command": "MODIFY_SYSTEM_SETTING",
    "params": {
        "setting": "screen_brightness",
        "value": 255
    }
}
```

### File Operations

#### UPLOAD_FILE
Uploads a file to the server.

## Response Format

### Success Response
```json
{
    "success": true,
    "command": "COMMAND_NAME",
    "deviceId": "device_id"
}
```

### Error Response
```json
{
    "success": false,
    "error": "Error message",
    "command": "COMMAND_NAME",
    "deviceId": "device_id"
}
```

## Examples

### Example 1: Launch YouTube
```json
{
    "type": "command",
    "targetDevice": "pixel_6_pro",
    "command": "LAUNCH_APP",
    "params": {
        "packageName": "com.google.android.youtube"
    }
}
```

### Example 2: Take Screenshot
```json
{
    "type": "command",
    "targetDevice": "pixel_6_pro",
    "command": "TAKE_SCREENSHOT",
    "params": {}
}
```

## Error Codes

- `DEVICE_NOT_FOUND`: Target device is not connected
- `INVALID_COMMAND`: Command not recognized
- `PERMISSION_DENIED`: App doesn't have required permissions
- `EXECUTION_FAILED`: Command execution failed

## Notes

1. Some commands require specific Android permissions
2. Some operations may require root access on non-rooted devices
3. Device must be registered before receiving commands
4. WebSocket connection must be maintained for real-time command execution

## Testing

You can test commands using any WebSocket client:

```javascript
const ws = new WebSocket('wss://your-netlify-domain.netlify.app');

ws.onopen = () => {
    // Register device
    ws.send(JSON.stringify({
        type: "register",
        deviceId: "test_device"
    }));

    // Send test command
    ws.send(JSON.stringify({
        type: "command",
        targetDevice: "test_device",
        command: "TAKE_SCREENSHOT",
        params: {}
    }));
};
```


Now update the MainActivity to handle incoming commands:

```kotlin:app/src/main/java/com/example/jarvismk7/MainActivity.kt
// Add to class properties
private lateinit var commandExecutor: CommandExecutor

// In onCreate
commandExecutor = CommandExecutor(
    this,
    systemOperationsHandler,
    systemSettingsHandler,
    packageManagerHandler
)

webSocketClient.onMessageReceived = { message ->
    try {
        val json = JSONObject(message)
        val command = json.getString("command")
        val params = json.getJSONObject("params")
        commandExecutor.executeCommand(command, params)
    } catch (e: Exception) {
        Log.e("MainActivity", "Error executing command", e)
    }
}

