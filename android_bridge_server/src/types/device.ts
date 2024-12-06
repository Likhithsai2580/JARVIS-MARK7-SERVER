import { Socket } from 'socket.io';

export interface Device {
    socket: Socket;
    status: 'connected' | 'disconnected' | 'busy';
    lastSeen: Date;
    capabilities: string[];
    batteryLevel: number | null;
    deviceInfo: DeviceInfo | null;
}

export interface DeviceInfo {
    manufacturer: string;
    model: string;
    androidVersion: string;
    apiLevel: number;
    screenResolution: {
        width: number;
        height: number;
    };
    batteryLevel: number;
    isCharging: boolean;
    totalStorage: number;
    freeStorage: number;
    totalRAM: number;
    freeRAM: number;
}

export interface CommandResponse {
    success: boolean;
    data?: any;
    error?: string;
} 