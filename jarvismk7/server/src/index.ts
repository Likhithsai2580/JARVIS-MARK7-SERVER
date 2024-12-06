import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import { v4 as uuidv4 } from 'uuid';
import multer from 'multer';
import path from 'path';
import fs from 'fs';

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

app.use(cors());
app.use(express.json());

// Store device connections with their secure tokens
const connectedDevices = new Map<string, {
    socket: any,
    token: string
}>();

// Generate QR code content for new connections
app.get('/api/generate-connection-code', (req, res) => {
    const connectionToken = uuidv4();
    const qrContent = JSON.stringify({
        server: process.env.SERVER_URL,
        token: connectionToken,
        timestamp: Date.now()
    });
    
    res.json({ qrCode: qrContent });
});

// Configure multer for file uploads
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        const uploadDir = path.join(__dirname, '../uploads');
        if (!fs.existsSync(uploadDir)) {
            fs.mkdirSync(uploadDir, { recursive: true });
        }
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        cb(null, `${Date.now()}-${file.originalname}`);
    }
});

const upload = multer({ storage });

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
    const filePath = path.join(__dirname, '../uploads', filename);
    
    if (!fs.existsSync(filePath)) {
        return res.status(404).json({ error: 'File not found' });
    }
    
    res.download(filePath);
});

io.on('connection', (socket) => {
    socket.on('authenticate', (data) => {
        const { token } = data;
        if (token) {
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
                const filePath = path.join(__dirname, '../uploads', fileName);
                await fs.promises.writeFile(filePath, Buffer.from(fileData, 'base64'));
                device.socket.emit('file-uploaded', { success: true, fileName });
            } else if (type === 'download') {
                try {
                    const filePath = path.join(__dirname, '../uploads', fileName);
                    const fileData = await fs.promises.readFile(filePath, { encoding: 'base64' });
                    device.socket.emit('file-download', { fileData, fileName });
                } catch (error) {
                    device.socket.emit('file-error', { error: 'File not found' });
                }
            }
        }
    });
});

// REST API endpoints
app.post('/api/send-command', (req, res) => {
  const { targetDevice, command, params } = req.body;
  const targetSocket = connectedClients.get(targetDevice);

  if (targetSocket) {
    targetSocket.emit('execute', { command, params });
    res.json({ success: true });
  } else {
    res.status(404).json({ success: false, error: 'Device not found' });
  }
});

const PORT = process.env.PORT || 3000;
httpServer.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
}); 