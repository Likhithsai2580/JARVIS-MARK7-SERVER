import { Device } from '../types/device';
import { Socket } from 'socket.io';
import { EventEmitter } from 'events';

export class AndroidService extends EventEmitter {
    private devices: Map<string, Device>;
    private commandQueue: Map<string, Array<{command: string, params: any}>>;
    private commandTimeouts: Map<string, NodeJS.Timeout>;

    constructor() {
        super();
        this.devices = new Map();
        this.commandQueue = new Map();
        this.commandTimeouts = new Map();
    }

    public registerDevice(token: string, socket: Socket): void {
        this.devices.set(token, {
            socket,
            status: 'connected',
            lastSeen: new Date(),
            capabilities: [],
            batteryLevel: null,
            deviceInfo: null
        });

        // Initialize command queue for device
        this.commandQueue.set(token, []);

        // Request device info
        this.sendCommand(token, 'getDeviceInfo', {});
        this.sendCommand(token, 'getCapabilities', {});
    }

    public async sendCommand(token: string, command: string, params: any): Promise<any> {
        const device = this.devices.get(token);
        if (!device) {
            throw new Error('Device not found');
        }

        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Command timeout'));
            }, 30000); // 30 second timeout

            this.commandTimeouts.set(token, timeout);

            device.socket.emit('execute', { command, params }, (response: any) => {
                clearTimeout(timeout);
                this.commandTimeouts.delete(token);
                
                if (response.error) {
                    reject(new Error(response.error));
                } else {
                    resolve(response.data);
                }
            });
        });
    }

    public async getDeviceStatus(token: string): Promise<Device | null> {
        return this.devices.get(token) || null;
    }

    public async updateDeviceInfo(token: string, info: any): void {
        const device = this.devices.get(token);
        if (device) {
            device.deviceInfo = info;
            this.devices.set(token, device);
            this.emit('deviceUpdated', token, device);
        }
    }

    public async updateDeviceCapabilities(token: string, capabilities: string[]): void {
        const device = this.devices.get(token);
        if (device) {
            device.capabilities = capabilities;
            this.devices.set(token, device);
            this.emit('deviceUpdated', token, device);
        }
    }

    public disconnectDevice(token: string): void {
        const device = this.devices.get(token);
        if (device) {
            device.socket.disconnect();
            this.devices.delete(token);
            this.commandQueue.delete(token);
            
            const timeout = this.commandTimeouts.get(token);
            if (timeout) {
                clearTimeout(timeout);
                this.commandTimeouts.delete(token);
            }
            
            this.emit('deviceDisconnected', token);
        }
    }

    public getConnectedDevices(): Device[] {
        return Array.from(this.devices.values());
    }
} 