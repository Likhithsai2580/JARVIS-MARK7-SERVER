# JARVIS DNS Server

A distributed DNS (Domain Name System) service implementation for service discovery and health monitoring in a microservices architecture.

## Overview

This DNS server implementation provides service registration, discovery, and health monitoring capabilities for distributed systems. It helps manage and coordinate microservices by tracking their availability, status, and metadata. The system is designed to be resilient, scalable, and easy to integrate with existing microservices architectures.

## Features

- Service Registration: Register services with type, instance ID, port, and metadata
- Service Discovery: Find available service instances based on requirements
- Health Monitoring: Automatic health checks and status updates
- Heartbeat System: Periodic heartbeats to maintain service availability
- Busy Status Tracking: Track and update service busy status
- Automatic Dead Instance Detection
- Metadata-based Service Discovery
- Load Balancing Support through Instance Selection

## Installation

```bash
# Install required dependencies
pip install httpx asyncio

# Optional: Clone the repository
git clone https://github.com/Likhithsai2580/JARVIS-MARK7-SERVER.git
cd JARVIS-MARK7-SERVER/dns_server
```

## Comprehensive Usage Guide

### 1. Basic Service Registration

```python
import asyncio
from dns_client import DNSClient, ServiceConfig

async def main():
    # Initialize DNS client
    dns_client = DNSClient(
        dns_url="https://your-dns-server.com",
        base_port=5000
    )

    # Create service configuration
    config = ServiceConfig(
        service_type="authentication-service",
        instance_id=1,
        port=5001,
        metadata={
            "version": "1.0",
            "capabilities": ["oauth", "jwt"],
            "max_connections": 1000
        }
    )

    # Register service
    success = await dns_client.register_service(config)
    print(f"Service registration {'successful' if success else 'failed'}")

    # Keep the service running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await dns_client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

Sample Output:
```
Service registration successful
[INFO] Heartbeat sent successfully
[INFO] Health check passed - Service status: active
[INFO] Current load: 23%, Connections: 156
```

### 2. Advanced Service Discovery

```python
async def discover_services():
    dns_client = DNSClient()
    
    # Discover service with specific requirements
    auth_service = await dns_client.discover_service(
        service_type="authentication-service",
        requirements={
            "version": "1.0",
            "capabilities": ["oauth"],
            "busy": False
        }
    )
    
    if auth_service:
        print(f"Found service instance: {auth_service}")
        # Sample output:
        # {
        #     "service_type": "authentication-service",
        #     "instance_id": 1,
        #     "host": "localhost",
        #     "port": 5001,
        #     "metadata": {
        #         "version": "1.0",
        #         "capabilities": ["oauth", "jwt"],
        #         "max_connections": 1000
        #     },
        #     "status": "active",
        #     "busy": false
        # }
```

### 3. Managing Service Status

```python
async def service_status_management():
    dns_client = DNSClient()
    
    # Update service status based on load
    current_load = calculate_service_load()  # Your load calculation logic
    await dns_client.update_status(busy=(current_load > 80))
    
    # Handle cleanup on shutdown
    async def shutdown():
        print("Service shutting down...")
        await dns_client.close()
        print("Cleanup completed")
```

### 4. Health Check Implementation

```python
from fastapi import FastAPI
import psutil

app = FastAPI()

@app.get("/health")
async def health_check():
    # Example health check endpoint
    cpu_percent = psutil.cpu_percent()
    memory_percent = psutil.virtual_memory().percent
    
    return {
        "status": "healthy",
        "busy": cpu_percent > 80 or memory_percent > 90,
        "metrics": {
            "cpu_usage": cpu_percent,
            "memory_usage": memory_percent,
            "timestamp": time.time()
        }
    }
```

### 5. Complete Service Example

```python
import asyncio
from dns_client import DNSClient, ServiceConfig
from fastapi import FastAPI
import uvicorn

app = FastAPI()
dns_client = None

@app.on_event("startup")
async def startup_event():
    global dns_client
    dns_client = DNSClient()
    
    config = ServiceConfig(
        service_type="user-service",
        instance_id=1,
        port=5001,
        metadata={
            "version": "1.0",
            "database": "postgres",
            "cache": "redis"
        }
    )
    
    success = await dns_client.register_service(config)
    if not success:
        raise Exception("Failed to register with DNS server")

@app.on_event("shutdown")
async def shutdown_event():
    if dns_client:
        await dns_client.close()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    # Your API logic here
    return {"user_id": user_id, "name": "John Doe"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)
```

## Environment Variables

- `DNS_SERVER_URL`: URL of the DNS server (default: "https://jarvis-dns.netlify.app")
- `BASE_PORT`: Base port number for services (default: 5000)
- `HOST`: Host address for the service (default: "localhost")

## Features in Detail

### Health Monitoring
- Automatic health checks every 60 seconds
- Services marked as "dead" if health check fails
- Busy status updates based on service health
- Configurable health check endpoints
- Metrics collection and reporting

### Heartbeat System
- Sends heartbeats every 10 seconds
- Includes service metrics and status
- Maintains service availability tracking
- Automatic recovery from network issues
- Dead instance detection and cleanup

### Service Discovery Features
- Find services by type
- Filter by metadata requirements
- Exclude busy instances
- Support for multiple instance selection strategies
- Automatic failover to available instances

## Error Handling and Recovery

The client includes robust error handling for:
- Registration failures with automatic retry
- Discovery errors with fallback options
- Status update issues with local caching
- Health check problems with configurable thresholds
- Heartbeat failures with reconnection logic
- Network timeouts and connection issues

### Common Error Scenarios and Solutions

1. DNS Server Unavailable
```python
try:
    await dns_client.register_service(config)
except ConnectionError:
    # Implement retry logic or fallback to local cache
    pass
```

2. Service Instance Dead
```python
# Automatic detection and cleanup
if health_check_fails > 3:
    await dns_client.update_status(status="dead")
```

## Best Practices

1. Service Registration
   - Use meaningful service types
   - Include version information in metadata
   - Implement proper cleanup on shutdown

2. Service Discovery
   - Cache discovered services
   - Implement circuit breakers
   - Use appropriate timeouts

3. Health Checks
   - Keep checks lightweight
   - Include relevant metrics
   - Set appropriate thresholds

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

[MIT License](LICENSE)

## Support

For support, please open an issue in the GitHub repository or contact the maintainers. 