# Google Auth Service

A comprehensive Google OAuth2 integration service that handles authentication and authorization for various Google services including YouTube, Drive, Photos, and Contacts.

## Features

### Core Authentication
- Google OAuth2 authentication flow
- Token management (access tokens, refresh tokens)
- Support for multiple Google services (YouTube, Drive, Photos, Contacts)
- Secure token handling and storage
- Automatic token refresh
- Error handling and user session management

### Security Enhancements
- Rate limiting with burst protection
- IP-based access control
- Host validation
- Path validation
- Request size limits
- Enhanced security headers:
  - Content Security Policy (CSP)
  - HTTP Strict Transport Security (HSTS)
  - X-Frame-Options
  - X-Content-Type-Options
  - X-XSS-Protection
  - Referrer-Policy
  - Permissions-Policy

### Performance Optimizations
- Redis-based caching system
- Response caching with configurable expiration
- Token caching
- Request/Response compression
- Burst handling for rate limits
- Configurable timeouts

### Monitoring and Metrics
- Prometheus metrics integration
- Request/Response timing
- Active request tracking
- Rate limit monitoring
- Authentication failure tracking
- Custom metrics endpoint
- Health check endpoint

### Logging and Debugging
- Structured JSON logging
- Request ID tracking
- Error tracking with stack traces
- Performance metrics logging
- Request/Response logging
- Correlation IDs

## Prerequisites

- Python 3.8+
- Redis server
- Google Cloud Platform account with OAuth2 credentials
- Google APIs enabled for the services you want to use

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd google-auth-service
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up Google Cloud Platform:
   - Go to the Google Cloud Console
   - Create a new project or select an existing one
   - Enable the APIs you need (YouTube, Drive, Photos, Contacts)
   - Create OAuth2 credentials
   - Download the client configuration

5. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Fill in the required values:
     - `GOOGLE_CLIENT_ID`: Your Google OAuth client ID
     - `GOOGLE_CLIENT_SECRET`: Your Google OAuth client secret
     - `GOOGLE_REDIRECT_URI`: Your callback URL
     - `JWT_SECRET_KEY`: A secure random string for JWT encoding
     - `API_BASE_URL`: Your API base URL
     - `FRONTEND_REDIRECT_URL`: Your frontend application URL
     - `REDIS_URL`: Redis connection URL (default: redis://localhost:6379)

## Running the Service

1. Start Redis server:
```bash
redis-server
```

2. Start the server:
```bash
uvicorn app.main:app --reload
```

3. The service will be available at:
   - API: `http://localhost:8000`
   - Documentation: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`
   - Metrics: `http://localhost:8000/metrics`
   - Health Check: `http://localhost:8000/health`

## API Endpoints

### Authorization Flow

1. **Start Authorization**
   ```
   GET /api/v1/authorization?token={token}
   ```
   Initiates the Google OAuth2 flow and redirects to Google's consent screen.

2. **OAuth Callback**
   ```
   GET /api/v1/callback
   ```
   Handles the callback from Google's OAuth2 consent screen.

3. **Refresh Token**
   ```
   POST /api/v1/refresh-token
   ```
   Refreshes an expired access token.

### Monitoring Endpoints

1. **Health Check**
   ```
   GET /health
   ```
   Returns service health status and cache availability.

2. **Metrics**
   ```
   GET /metrics
   ```
   Returns Prometheus metrics for monitoring.

## Security Features

### Rate Limiting
- Default: 100 requests per minute per IP
- Burst protection: 20 requests per second
- Configurable limits
- IP-based tracking
- Metrics collection

### Request Validation
- Maximum body size: 10MB
- Maximum URI length: 2048 characters
- Host validation
- Path validation
- IP blocking support

### Security Headers
```json
{
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'...",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=()..."
}
```

## Caching System

### Response Caching
- Redis-based caching
- Configurable expiration times
- Cache key generation based on:
  - Request method
  - URL
  - Authorization header
- Automatic cache invalidation

### Token Caching
- Separate token cache
- User-specific cache keys
- 1-hour default expiration
- Automatic refresh

## Monitoring and Metrics

### Prometheus Metrics
- HTTP request counts
- Request duration
- Active requests
- Rate limit hits
- Authentication failures
- Custom metrics support

### Logging
- Structured JSON logging
- Request ID tracking
- Error tracking
- Performance metrics
- Request/Response details

## Error Handling

The service includes comprehensive error handling for:
- Invalid tokens
- Expired tokens
- Authorization failures
- Rate limit exceeded
- Invalid requests
- Server errors
- Cache failures

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 