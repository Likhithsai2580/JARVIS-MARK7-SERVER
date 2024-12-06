import { AndroidService } from './AndroidService';
import { CommandResponse } from '../types/device';

export class CommandHandler {
    private androidService: AndroidService;

    constructor(androidService: AndroidService) {
        this.androidService = androidService;
    }

    public async executeCommand(token: string, command: string, params: any): Promise<CommandResponse> {
        try {
            const device = await this.androidService.getDeviceStatus(token);
            if (!device) {
                return { success: false, error: 'Device not found' };
            }

            switch (command) {
                case 'screenshot':
                    return await this.handleScreenshot(token);
                case 'installApp':
                    return await this.handleAppInstall(token, params);
                case 'uninstallApp':
                    return await this.handleAppUninstall(token, params);
                case 'startApp':
                    return await this.handleAppStart(token, params);
                case 'stopApp':
                    return await this.handleAppStop(token, params);
                case 'pushFile':
                    return await this.handleFilePush(token, params);
                case 'pullFile':
                    return await this.handleFilePull(token, params);
                case 'shell':
                    return await this.handleShellCommand(token, params);
                case 'reboot':
                    return await this.handleReboot(token, params);
                default:
                    return await this.handleGenericCommand(token, command, params);
            }
        } catch (error) {
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Unknown error'
            };
        }
    }

    private async handleScreenshot(token: string): Promise<CommandResponse> {
        const result = await this.androidService.sendCommand(token, 'screenshot', {});
        return {
            success: true,
            data: result
        };
    }

    private async handleAppInstall(token: string, params: any): Promise<CommandResponse> {
        // Validate APK file
        if (!params.apkPath) {
            return { success: false, error: 'APK path is required' };
        }

        const result = await this.androidService.sendCommand(token, 'installApp', params);
        return {
            success: true,
            data: result
        };
    }

    // Add other command handlers...
} 