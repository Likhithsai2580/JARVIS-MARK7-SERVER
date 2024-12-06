import { Server } from 'socket.io';
import { createServer } from 'http';
import { AndroidService } from './services/AndroidService';
import { CommandHandler } from './services/CommandHandler';
import { logger } from './utils/logger';
import { rateLimit } from './middleware/rateLimit';
import { authenticate } from './middleware/auth';
import { DNSClient } from './services/DNSClient';

export class AndroidBridgeServer {
    private io: Server;
    private androidService: AndroidService;
    private commandHandler: CommandHandler;
    private dnsClient: DNSClient;
    private port: number;

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
        this.dnsClient = new DNSClient(process.env.DNS_SERVER_URL);
        this.port = parseInt(process.env.PORT || '5005');

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
            this.dnsClient.updateStatus(true, {
                active_connections: this.io.engine.clientsCount,
                last_connection: new Date().toISOString()
            });

            socket.on('authenticate', async (data) => {
                try {
                    const { token } = data;
                    this.androidService.registerDevice(token, socket);
                    socket.emit('authenticated', { success: true });
                    await this.dnsClient.updateStatus(false, {
                        registered_devices: this.androidService.getDeviceCount()
                    });
                } catch (error) {
                    logger.error('Authentication error:', error);
                    socket.emit('error', { message: 'Authentication failed' });
                }
            });

            socket.on('command', async (data) => {
                try {
                    const { token, command, params } = data;
                    await this.dnsClient.updateStatus(true, {
                        processing_command: command,
                        timestamp: new Date().toISOString()
                    });
                    const result = await this.commandHandler.executeCommand(token, command, params);
                    socket.emit('commandResult', result);
                    await this.dnsClient.updateStatus(false, {
                        last_command: command,
                        success: true,
                        timestamp: new Date().toISOString()
                    });
                } catch (error) {
                    logger.error('Command error:', error);
                    socket.emit('error', { message: 'Command execution failed' });
                    await this.dnsClient.updateStatus(false, {
                        last_error: error instanceof Error ? error.message : 'Unknown error',
                        timestamp: new Date().toISOString()
                    });
                }
            });

            socket.on('disconnect', async () => {
                logger.info(`Disconnected: ${socket.id}`);
                await this.dnsClient.updateStatus(false, {
                    active_connections: this.io.engine.clientsCount,
                    last_disconnect: new Date().toISOString()
                });
            });
        });
    }

    public async start(port: number = this.port): Promise<void> {
        this.port = port;
        
        // Register with DNS server
        const registered = await this.dnsClient.registerService({
            service_type: 'android_bridge',
            instance_id: parseInt(process.env.INSTANCE_ID || '1'),
            port: this.port,
            metadata: {
                version: '1.0',
                start_time: new Date().toISOString(),
                supported_features: ['device_control', 'command_execution']
            }
        });

        if (!registered) {
            logger.warn('Failed to register with DNS server, continuing anyway...');
        }

        this.io.listen(port);
        logger.info(`Server started on port ${port}`);
    }

    public async stop(): Promise<void> {
        await this.dnsClient.close();
        this.io.close();
    }
} 