# JARVIS MARK7 Database Server

A sophisticated authentication and database server that combines traditional authentication with facial recognition, featuring Discord bot integration for data management.

## Features

- **Multi-factor Authentication System**
  - Traditional username/password authentication
  - Facial recognition authentication using DeepFace
  - JWT-based token system

- **Discord Bot Integration**
  - Automated channel management
  - Project tracking
  - Logging system
  - Error reporting

- **RESTful API Endpoints**
  - User registration and login
  - Face authentication
  - Project management
  - Logging and error tracking

## Tech Stack

- FastAPI - Modern web framework for building APIs
- Discord.py - Discord bot integration
- DeepFace - Facial recognition system
- JWT - Token-based authentication
- OpenCV - Image processing
- Pydantic - Data validation
- Uvicorn - ASGI server

## Prerequisites

- Python 3.8+
- Discord Bot Token
- Webcam (for facial authentication)

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with the following variables:
```env
DISCORD_TOKEN=your_discord_bot_token
JWT_SECRET_KEY=your_jwt_secret
ALGORITHM=HS256
```

## Project Structure

- `server.py` - Main FastAPI server implementation
- `bot.py` - Discord bot implementation
- `face_auth/` - Facial authentication modules
- `requirements.txt` - Project dependencies
- `.env` - Environment variables

## API Endpoints

### Authentication
- `POST /token` - Register new user
- `POST /login` - User login
- `POST /face-auth/register` - Register face
- `POST /face-auth/verify` - Verify face
- `POST /face-auth` - Face authentication

### Project Management
- `POST /projects` - Create new project

### Logging
- `POST /logs` - Write logs
- `POST /errors` - Write errors

## Discord Bot Commands

- `/setup` - Initialize database channels (Admin only)
- `/ping` - Check bot responsiveness
- `/reset` - Reset database channels (Admin only)

## Security Features

- JWT-based authentication
- Facial recognition verification
- Password hashing
- CORS middleware
- OAuth2 password flow

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License. 