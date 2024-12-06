import { Server } from 'socket.io';
import { createServer } from 'http';
import { AndroidService } from './services/AndroidService';
import { CommandHandler } from './services/CommandHandler';
import { logger } from './utils/logger';
import { rateLimit } from './middleware/rateLimit';
import { authenticate } from './middleware/auth';

export class AndroidBridgeServer {
    private io: Server;
    private androidService: AndroidService;
    private commandHandler: CommandHandler;

    constructor() {
        const httpServer = createServer();
        this.io = new Server(httpServer, {
            cors: {
                origin: process.env.ALLOWED_ORIGINS?.split(',') || "*",
                methods: ["GET", "POST"]
            }
        });

        this.androidService = new AndroidService();
        this.commandHandler = new CommandHandler(this.androidService);

        this.setupMiddleware();
        this.setupEventHandlers();
    }

    private setupMiddleware(): void {
        this.io.use(authenticate);
        this.io.use(rateLimit);
    }

    private setupEventHandlers(): void {
        this.io.on('connection', (socket) => {
            logger.info(`New connection: ${socket.id}`);

            socket.on('authenticate', async (data) => {
                try {
                    const { token } = data;
                    this.androidService.registerDevice(token, socket);
                    socket.emit('authenticated', { success: true });
                } catch (error) {
                    logger.error('Authentication error:', error);
                    socket.emit('error', { message: 'Authentication failed' });
                }
            });

            socket.on('command', async (data) => {
                try {
                    const { token, command, params } = data;
                    const result = await this.commandHandler.executeCommand(token, command, params);
                    socket.emit('commandResult', result);
                } catch (error) {
                    logger.error('Command error:', error);
                    socket.emit('error', { message: 'Command execution failed' });
                }
            });

            socket.on('disconnect', () => {
                logger.info(`Disconnected: ${socket.id}`);
                // Handle cleanup
            });
        });
    }

    public start(port: number): void {
        this.io.listen(port);
        logger.info(`Server started on port ${port}`);
    }
} 