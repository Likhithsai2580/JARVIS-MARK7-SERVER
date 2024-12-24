import express, { Request, Response, NextFunction } from 'express';
import { createServer } from 'http';
import { Server, Socket } from 'socket.io';
import cors from 'cors';
import { v4 as uuidv4 } from 'uuid';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import rateLimit from 'express-rate-limit';
import helmet from 'helmet';
import { createLogger, format, transports } from 'winston';

// Configure logger
const logger = createLogger({
    format: format.combine(
        format.timestamp(),
        format.json()
    ),
    transports: [
        new transports.File({ filename: 'error.log', level: 'error' }),
        new transports.File({ filename: 'combined.log' }),
        new transports.Console({
            format: format.combine(
                format.colorize(),
                format.simple()
            )
        })
    ]
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

// Error types
class AuthenticationError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'AuthenticationError';
    }
}

class CommandError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'CommandError';
    }
}

// Enhanced interfaces
interface DeviceConnection {
    socket: Socket;
    token: string;
    lastHeartbeat: number;
    status: 'connected' | 'disconnected' | 'idle';
    batteryLevel?: number;
    deviceInfo?: {
        model: string;
        androidVersion: string;
        capabilities: string[];
        uniqueId: string;
    };
    reconnectAttempts: number;
    commandHistory: Array<{
        command: string;
        timestamp: number;
        status: 'success' | 'failed' | 'pending';
    }>;
    metrics: {
        totalCommands: number;
        successfulCommands: number;
        failedCommands: number;
        lastResponseTime: number;
    };
}

interface CommandData {
    token: string;
    command: string;
    params: Record<string, any>;
    messageId?: string;
    timestamp?: number;
}

interface ErrorResponse {
    type: string;
    message: string;
    command?: string;
    timestamp?: number;
}

// Initialize Express app with security middleware
const app = express();
app.use(helmet());
app.use(cors({
    origin: process.env.ALLOWED_ORIGINS?.split(',') || "*",
    methods: ['GET', 'POST'],
    credentials: true
}));
app.use(express.json({ limit: '10mb' }));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100 // limit each IP to 100 requests per windowMs
});
app.use('/api/', limiter);

// Create HTTP server and Socket.IO instance
const httpServer = createServer(app);
const io = new Server(httpServer, {
    cors: {
        origin: process.env.ALLOWED_ORIGINS?.split(',') || "*",
        methods: ["GET", "POST"],
        credentials: true
    },
    pingTimeout: 30000,
    pingInterval: 15000
});

// Store device connections
const connectedDevices = new Map<string, DeviceConnection>();

// Connection monitoring
const MAX_RECONNECT_ATTEMPTS = 5;
const HEARTBEAT_INTERVAL = 15000;
const CONNECTION_TIMEOUT = 45000;
const COMMAND_TIMEOUT = 30000;

// Command rate limiting
const commandRateLimiter = new Map<string, number>();
const MAX_COMMANDS_PER_MINUTE = 60;

function monitorConnections() {
    setInterval(() => {
        const currentTime = Date.now();
        connectedDevices.forEach((device, token) => {
            if (currentTime - device.lastHeartbeat > CONNECTION_TIMEOUT) {
                if (device.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                    device.status = 'disconnected';
                    device.reconnectAttempts++;
                    device.socket.emit('reconnect');
                    logger.warn(`Device ${token} disconnected, attempt ${device.reconnectAttempts}`);
                } else {
                    connectedDevices.delete(token);
                    logger.error(`Device ${token} removed after max reconnection attempts`);
                }
            }
        });
    }, HEARTBEAT_INTERVAL);
}

function checkCommandRate(token: string): boolean {
    const currentTime = Date.now();
    const commandCount = commandRateLimiter.get(token) || 0;
    if (commandCount >= MAX_COMMANDS_PER_MINUTE) {
        return false;
    }
    commandRateLimiter.set(token, commandCount + 1);
    setTimeout(() => {
        const currentCount = commandRateLimiter.get(token) || 0;
        commandRateLimiter.set(token, currentCount - 1);
    }, 60000);
    return true;
}

// Initialize monitoring
monitorConnections();

// Clean up command rate limiter
setInterval(() => {
    commandRateLimiter.clear();
}, 60000);

// Socket.IO connection handling
io.on('connection', (socket: Socket) => {
    let deviceToken: string | null = null;
    logger.info(`New connection attempt: ${socket.id}`);

    socket.on('authenticate', async (data: { token: string; deviceInfo?: any }) => {
        try {
            const { token, deviceInfo } = data;
            if (!token) {
                throw new AuthenticationError('No token provided');
            }

            deviceToken = token;
            const device: DeviceConnection = {
                socket,
                token,
                lastHeartbeat: Date.now(),
                status: 'connected',
                reconnectAttempts: 0,
                deviceInfo: deviceInfo || undefined,
                commandHistory: [],
                metrics: {
                    totalCommands: 0,
                    successfulCommands: 0,
                    failedCommands: 0,
                    lastResponseTime: 0
                }
            };

            connectedDevices.set(token, device);
            socket.emit('authenticated', { 
                success: true,
                serverTime: Date.now(),
                config: {
                    heartbeatInterval: HEARTBEAT_INTERVAL,
                    commandTimeout: COMMAND_TIMEOUT,
                    maxCommandsPerMinute: MAX_COMMANDS_PER_MINUTE
                }
            });
            
            logger.info(`Device authenticated: ${token}`);
        } catch (error) {
            const err = error as Error;
            logger.error('Authentication error:', err);
            const response: ErrorResponse = {
                type: 'AUTH_ERROR',
                message: err.message,
                timestamp: Date.now()
            };
            socket.emit('error', response);
        }
    });

    socket.on('command', async (data: CommandData) => {
        try {
            const { token, command, params, messageId } = data;
            const device = connectedDevices.get(token);
            
            if (!device || device.status !== 'connected') {
                throw new CommandError('Device not connected or unavailable');
            }

            if (!checkCommandRate(token)) {
                throw new CommandError('Command rate limit exceeded');
            }

            const commandStartTime = Date.now();
            device.metrics.totalCommands++;
            device.commandHistory.push({
                command,
                timestamp: commandStartTime,
                status: 'pending'
            });

            const commandTimeout = setTimeout(() => {
                device.metrics.failedCommands++;
                socket.emit('commandTimeout', { messageId, command });
            }, COMMAND_TIMEOUT);

            device.socket.emit('execute', { command, params, messageId });

            // Handle command response
            socket.once(`commandResponse:${messageId}`, (response: any) => {
                clearTimeout(commandTimeout);
                device.metrics.lastResponseTime = Date.now() - commandStartTime;
                
                if (response.success) {
                    device.metrics.successfulCommands++;
                    return { success: true, data: response.data };
                } else {
                    device.metrics.failedCommands++;
                    return { success: false, error: response.error };
                }
            });

        } catch (error) {
            const err = error as Error;
            logger.error('Command error:', err);
            socket.emit('commandError', {
                type: 'COMMAND_ERROR',
                message: err.message,
                command: data.command,
                timestamp: Date.now()
            });
            return { success: false, error: err.message };
        }
    });

    // Handle disconnection
    socket.on('disconnect', () => {
        if (deviceToken) {
            const device = connectedDevices.get(deviceToken);
            if (device) {
                device.status = 'disconnected';
                logger.info(`Device disconnected: ${deviceToken}`);
            }
        }
    });
});

// Error handling middleware
app.use((err: Error, req: Request, res: Response, _next: NextFunction) => {
    logger.error('Server error:', err);
    res.status(500).json({ 
        success: false, 
        error: 'Internal server error' 
    });
});

// Start server
const PORT = process.env.PORT || 3000;
httpServer.listen(PORT, () => {
    logger.info(`Server running on port ${PORT}`);
}); 