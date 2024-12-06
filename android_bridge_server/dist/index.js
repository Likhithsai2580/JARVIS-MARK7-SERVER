"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const http_1 = require("http");
const socket_io_1 = require("socket.io");
const cors_1 = __importDefault(require("cors"));
const uuid_1 = require("uuid");
const multer_1 = __importDefault(require("multer"));
const path_1 = __importDefault(require("path"));
const fs_1 = __importDefault(require("fs"));
const app = (0, express_1.default)();
const httpServer = (0, http_1.createServer)(app);
const io = new socket_io_1.Server(httpServer, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});
app.use((0, cors_1.default)());
app.use(express_1.default.json());
// Store device connections with their secure tokens
const connectedDevices = new Map();
// Generate QR code content for new connections
app.get('/api/generate-connection-code', (req, res) => {
    const connectionToken = (0, uuid_1.v4)();
    const qrContent = JSON.stringify({
        server: process.env.SERVER_URL,
        token: connectionToken,
        timestamp: Date.now()
    });
    res.json({ qrCode: qrContent });
});
// Configure multer for file uploads
const storage = multer_1.default.diskStorage({
    destination: (req, file, cb) => {
        const uploadDir = path_1.default.join(__dirname, '../uploads');
        if (!fs_1.default.existsSync(uploadDir)) {
            fs_1.default.mkdirSync(uploadDir, { recursive: true });
        }
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        cb(null, `${Date.now()}-${file.originalname}`);
    }
});
const upload = (0, multer_1.default)({ storage });
// File transfer endpoints
app.post('/api/upload', upload.single('file'), (req, res) => {
    if (!req.file) {
        return res.status(400).json({ error: 'No file uploaded' });
    }
    const fileInfo = {
        filename: req.file.filename,
        originalName: req.file.originalname,
        path: req.file.path,
        size: req.file.size
    };
    res.json({ success: true, file: fileInfo });
});
app.get('/api/download/:filename', (req, res) => {
    const filename = req.params.filename;
    const filePath = path_1.default.join(__dirname, '../uploads', filename);
    if (!fs_1.default.existsSync(filePath)) {
        return res.status(404).json({ error: 'File not found' });
    }
    res.download(filePath);
});
io.on('connection', (socket) => {
    let deviceToken = null;
    socket.on('authenticate', (data) => {
        const { token } = data;
        if (token) {
            deviceToken = token;
            connectedDevices.set(token, {
                socket: socket,
                token: token
            });
            socket.emit('authenticated', { success: true });
        }
    });
    socket.on('command', (data) => {
        const { token, command, params } = data;
        const device = connectedDevices.get(token);
        if (device) {
            device.socket.emit('execute', { command, params });
        }
    });
    socket.on('file-transfer', async (data) => {
        const { token, fileData, fileName, type } = data;
        const device = connectedDevices.get(token);
        if (device) {
            if (type === 'upload') {
                const filePath = path_1.default.join(__dirname, '../uploads', fileName);
                await fs_1.default.promises.writeFile(filePath, Buffer.from(fileData, 'base64'));
                device.socket.emit('file-uploaded', { success: true, fileName });
            }
            else if (type === 'download') {
                try {
                    const filePath = path_1.default.join(__dirname, '../uploads', fileName);
                    const fileData = await fs_1.default.promises.readFile(filePath, { encoding: 'base64' });
                    device.socket.emit('file-download', { fileData, fileName });
                }
                catch (error) {
                    device.socket.emit('file-error', { error: 'File not found' });
                }
            }
        }
    });
    // Add heartbeat mechanism
    const heartbeatInterval = setInterval(() => {
        socket.emit('ping');
    }, 30000);
    socket.on('pong', () => {
        const device = Array.from(connectedDevices.values())
            .find(d => d.socket.id === socket.id);
        if (device) {
            device.lastHeartbeat = Date.now();
        }
    });
    // Add connection monitoring
    socket.on('status', (data) => {
        const device = connectedDevices.get(data.token);
        if (device) {
            device.status = data.status;
            device.batteryLevel = data.batteryLevel;
            device.lastUpdate = Date.now();
        }
    });
    // Add disconnect handler
    socket.on('disconnect', () => {
        clearInterval(heartbeatInterval);
        if (deviceToken) {
            connectedDevices.delete(deviceToken);
        }
    });
});
// REST API endpoints
app.post('/api/send-command', (req, res) => {
    const { targetDevice, command, params } = req.body;
    const device = connectedDevices.get(targetDevice);
    if (device) {
        device.socket.emit('execute', { command, params });
        res.json({ success: true });
    }
    else {
        res.status(404).json({ success: false, error: 'Device not found' });
    }
});
// Add error handling middleware
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({
        success: false,
        error: 'Internal server error'
    });
});
const PORT = process.env.PORT || 3000;
httpServer.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
