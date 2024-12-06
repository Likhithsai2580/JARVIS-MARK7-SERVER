import axios from 'axios';

interface ServiceConfig {
    service_type: string;
    instance_id: number;
    port: number;
    metadata?: Record<string, any>;
    host?: string;
    busy?: boolean;
}

export class DNSClient {
    private dns_url: string;
    private service_config?: ServiceConfig;
    private heartbeatInterval?: NodeJS.Timeout;

    constructor(dns_url: string = process.env.DNS_SERVER_URL || 'http://localhost:9000') {
        this.dns_url = dns_url;
    }

    async registerService(config: ServiceConfig): Promise<boolean> {
        try {
            this.service_config = config;
            const response = await axios.post(`${this.dns_url}/register`, {
                server: config.service_type,
                instance_id: config.instance_id,
                port: config.port,
                host: config.host || 'localhost',
                metadata: config.metadata || {}
            });

            if (response.status === 200) {
                // Start heartbeat
                this.startHeartbeat();
                return true;
            }
            return false;
        } catch (error) {
            console.error('Registration error:', error);
            return false;
        }
    }

    async updateStatus(busy: boolean = false, metadata: Record<string, any> = {}): Promise<void> {
        if (!this.service_config) return;

        try {
            await axios.post(`${this.dns_url}/status`, {
                server: this.service_config.service_type,
                instance_id: this.service_config.instance_id,
                status: 'active',
                busy,
                metadata
            });
        } catch (error) {
            console.error('Status update error:', error);
        }
    }

    private startHeartbeat(): void {
        // Send heartbeat every 30 seconds
        this.heartbeatInterval = setInterval(async () => {
            await this.updateStatus(false);
        }, 30000);
    }

    async close(): Promise<void> {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }
    }
} 