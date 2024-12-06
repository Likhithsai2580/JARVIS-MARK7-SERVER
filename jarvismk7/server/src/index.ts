import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import { v4 as uuidv4 } from 'uuid';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import { DNSClient } from './services/DNSClient';

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, {
    cors: {
        origin: process.env.ALLOWED_ORIGINS?.split(',') || "*",
        methods: ["GET", "POST"]
    }
});

// Initialize DNS client
const dnsClient = new DNSClient(process.env.DNS_SERVER_URL);
const port = parseInt(process.env.PORT || '5000');

// Configure multer for file uploads
const storage = multer.diskStorage({
    destination: (_req: Express.Request, file, cb) => {
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

// Middleware
app.use(cors());
app.use(express.json());

const getAuthenticatedClientsCount = (): number => {
    return Array.from(io.sockets.sockets.values()).filter(
        socket => socket.data.authenticated
    ).length;
};

// Generate QR code content for new connections
app.get('/api/generate-connection-code', async (req, res) => {
    const connectionToken = uuidv4();
    const qrContent = JSON.stringify({
        server: process.env.SERVER_URL,
        token: connectionToken,
        timestamp: Date.now()
    });

    await dnsClient.updateStatus(true, {
        action: 'generate_qr',
        timestamp: new Date().toISOString()
    });

    res.json({ qrContent, token: connectionToken });

    await dnsClient.updateStatus(false, {
        last_qr_generated: new Date().toISOString()
    });
});

// WebSocket connection handling
io.on('connection', async (socket) => {
    console.log('New client connected');
    
    await dnsClient.updateStatus(true, {
        active_connections: io.engine.clientsCount,
        last_connection: new Date().toISOString()
    });

    socket.on('authenticate', async (data) => {
        try {
            // Handle authentication
            socket.emit('authenticated', { success: true });
            await dnsClient.updateStatus(false, {
                authenticated_clients: getAuthenticatedClientsCount()
            });
        } catch (error) {
            console.error('Authentication error:', error);
            socket.emit('error', { message: 'Authentication failed' });
            await dnsClient.updateStatus(false, {
                last_error: error instanceof Error ? error.message : 'Unknown error',
                timestamp: new Date().toISOString()
            });
        }
    });

    socket.on('command', async (data) => {
        try {
            await dnsClient.updateStatus(true, {
                processing_command: data.command,
                timestamp: new Date().toISOString()
            });
            // Process command
            socket.emit('commandResult', { success: true });
            await dnsClient.updateStatus(false, {
                last_command: data.command,
                success: true,
                timestamp: new Date().toISOString()
            });
        } catch (error) {
            console.error('Command error:', error);
            socket.emit('error', { message: 'Command execution failed' });
            await dnsClient.updateStatus(false, {
                last_error: error instanceof Error ? error.message : 'Unknown error',
                timestamp: new Date().toISOString()
            });
        }
    });

    socket.on('disconnect', async () => {
        console.log('Client disconnected');
        await dnsClient.updateStatus(false, {
            active_connections: io.engine.clientsCount,
            last_disconnect: new Date().toISOString()
        });
    });
});

// Start server
async function startServer() {
    try {
        // Register with DNS server
        const registered = await dnsClient.registerService({
            service_type: 'jarvis_mk7',
            instance_id: parseInt(process.env.INSTANCE_ID || '1'),
            port,
            metadata: {
                version: '7.0',
                start_time: new Date().toISOString(),
                features: ['qr_generation', 'websocket', 'file_upload']
            }
        });

        if (!registered) {
            console.warn('Failed to register with DNS server, continuing anyway...');
        }

        httpServer.listen(port, () => {
            console.log(`Server running on port ${port}`);
        });
    } catch (error) {
        console.error('Failed to start server:', error);
        process.exit(1);
    }
}

// Cleanup on shutdown
process.on('SIGTERM', async () => {
    console.log('Shutting down...');
    await dnsClient.close();
    httpServer.close();
    process.exit(0);
});

startServer(); 