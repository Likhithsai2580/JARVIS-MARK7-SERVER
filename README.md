# JARVIS MK7 - Advanced AI Control System

A powerful, modular system that combines a Python-based code execution engine (CodeBrew), an Android bridge server, and LLM integration for advanced AI control and automation.

## 🌟 Features

### CodeBrew Engine
- Asynchronous code execution with timeout handling
- Real-time output capture and streaming
- Memory-safe execution environment
- Automatic dependency management
- Command history and caching
- Comprehensive error handling

### Android Bridge Server
- WebSocket-based real-time communication
- Secure device authentication
- Command queueing and rate limiting
- Automatic resource cleanup
- Response caching
- Compression support

### LLM Integration
- Support for multiple LLM providers (OpenAI, Groq, Cohere, etc.)
- Streaming responses
- Message history management
- Retry mechanism with exponential backoff
- Concurrent request handling

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Node.js 18+
- Android Studio (for mobile app development)
- Docker (optional, for containerized deployment)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Likhithsai2580/JARVIS-MARK7-SERVER.git
cd JARVIS-MARK7-SERVER
```

2. Set up the Python environment:
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r codebrew/requirements.txt
```

3. Set up the Android Bridge Server:
```bash
cd android_bridge_server
npm install
```

4. Configure environment variables:
```bash
# Copy example env files
cp .env.example .env
cp android_bridge_server/.env.example android_bridge_server/.env

# Edit the .env files with your configuration
```

### Running the Services

#### CodeBrew Engine
```bash
cd codebrew
python main.py
```

#### Android Bridge Server
```bash
# Development
cd android_bridge_server
npm run dev

# Production
npm run build
npm start
```

#### Docker Deployment
```bash
# Build and run all services
docker-compose up -d

# Development environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## 🧪 Testing

The codebase includes comprehensive test suites for all components:

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m api
pytest -m llm

# Run with coverage report
pytest --cov

# Run including slow tests
pytest --run-slow
```

## 📚 API Documentation

### CodeBrew API

#### Execute Code
```python
from main import CodeBrew, CodeBrewConfig
from llm._llmserver import LLMServer, GPT35_TURBO

# Initialize
config = CodeBrewConfig(
    max_retries=3,
    keep_history=True,
    verbose=True
)
llm = LLMServer(model=GPT35_TURBO, server_url="your-server-url")
codebrew = CodeBrew(llm=llm, config=config)

# Execute code
result = await codebrew.run("Write a Python function to calculate fibonacci")
```

### Android Bridge Server API

#### REST Endpoints

- `GET /health` - Server health check
- `GET /api/generate-connection-code` - Generate device connection code
- `POST /api/query` - Execute command
- `DELETE /cache` - Clear response cache
- `DELETE /instances/{api_key}` - Remove device instance

#### WebSocket Events

- `authenticate` - Device authentication
- `command` - Command execution
- `commandResponse` - Command result
- `heartbeat` - Connection monitoring

## 🔧 Configuration

### CodeBrew Configuration
```python
CodeBrewConfig(
    max_retries=3,          # Maximum retry attempts
    keep_history=True,      # Keep conversation history
    verbose=False,          # Verbose output
    timeout=30.0,          # Execution timeout
    max_output_length=10000, # Maximum output buffer size
    cache_size=100         # Result cache size
)
```

### Server Configuration
```env
HOST=0.0.0.0
PORT=3000
INSTANCE_ID=0
MAX_INSTANCES=10
CACHE_TTL=3600
MAX_CACHE_SIZE=1000
ALLOWED_ORIGINS=*
```

## 🔐 Security

- API key authentication
- Rate limiting
- Request validation
- Secure WebSocket connections
- Resource isolation
- Input sanitization

## 🛠️ Development

### Project Structure
```
.
├── android_bridge_server/   # Node.js WebSocket server
├── codebrew/               # Python code execution engine
│   ├── llm/               # LLM integration
│   ├── tests/             # Test suites
│   └── main.py           # Core engine
├── jarvismk7/             # Android app
└── docker/                # Docker configurations
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

### Coding Standards
- Python: PEP 8
- TypeScript: ESLint configuration
- Test coverage: Minimum 80%

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

For support, please:
1. Check the [Issues](https://github.com/yourusername/jarvis-mk7/issues) page
2. Join our [Discord community](https://discord.gg/your-server)
3. Email support at support@your-domain.com

## 🙏 Acknowledgments

- OpenAI for GPT models
- Groq for LLM hosting
- The FastAPI team
- Socket.IO contributors
- Android development community

## Getting Started with Create React App

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

### Available Scripts

In the project directory, you can run:

#### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

The page will reload if you make edits.\
You will also see any lint errors in the console.

#### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

#### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

#### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can’t go back!**

If you aren’t satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you’re on your own.

You don’t have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn’t feel obligated to use this feature. However we understand that this tool wouldn’t be useful if you couldn’t customize it when you are ready for it.

### Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

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
```
