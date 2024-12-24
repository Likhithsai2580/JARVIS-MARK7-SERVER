from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager
import jwt
import datetime
import logging
import os
from dotenv import load_dotenv
import asyncio
import cv2
import numpy as np
import base64
from deepface import DeepFace
import uuid

# Import bot module
from bot import bot, start_bot
from face_auth.utils import setup_server

# Load environment variables
load_dotenv()

# Setup logging and data directories
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize data and server managers
data_manager, server_manager = setup_server()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        # Start bot in background task
        bot_task = asyncio.create_task(start_bot())
        logger.info("Discord bot startup initiated")
        yield
    finally:
        # Shutdown
        if 'bot_task' in locals():
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass
        logger.info("Discord bot shutdown complete")

# Initialize FastAPI app
app = FastAPI(
    title="JARVIS Database Server",
    description="API server for JARVIS database management",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")  # Change in production
ALGORITHM = "HS256"

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Data models
class User(BaseModel):
    username: str
    email: str
    password: str  # Make password required
    face_image: Optional[str] = None

class LoginRequest(BaseModel):
    identifier: str  # username or email
    password: Optional[str] = None
    face_image: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    jarvis_user_id: str
    auth_method: str  # "traditional" or "face_auth"

class LogEntry(BaseModel):
    level: str
    message: str
    source: str

class ErrorEntry(BaseModel):
    error_type: str
    message: str
    stack_trace: Optional[str] = None
    source: str

class Project(BaseModel):
    name: str
    description: str
    status: str
    jarvis_user_id: str  # This should match the field name in the request

class FaceAuthRequest(BaseModel):
    user_id: str
    image_data: str  # Base64 encoded image

class FaceAuthResponse(BaseModel):
    success: bool
    message: str
    username: Optional[str] = None
    token: Optional[str] = None

class FaceRegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    face_image: str  # Base64 encoded image

class FaceVerifyRequest(BaseModel):
    username: str
    face_image: str

class FaceVerifyResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None
    jarvis_user_id: Optional[str] = None

# Store user IDs (in memory - replace with database in production)
user_tokens = {}

# Authentication endpoints
@app.post("/token", response_model=Token)
async def register(user: User):
    """Register new user with either traditional or face authentication"""
    try:
        # Password is now required for all registrations
        if not user.password:
            raise HTTPException(
                status_code=400,
                detail="Password is required for registration"
            )

        # Determine authentication method
        auth_method = "traditional"
        if user.face_image:
            auth_method = "face_auth"
        
        try:
            # Always send authentication details to Discord
            jarvis_user_id = await bot.send_auth(user.username, user.email, user.password)
            
            # If face auth is enabled, also store the face image
            if user.face_image:
                await bot.send_face_auth(user.username, user.face_image)
                
        except Exception as e:
            logger.error(f"Discord communication error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to communicate with Discord: {str(e)}")
        
        # Generate JWT token
        token_data = {
            "sub": user.username,
            "jarvis_user_id": jarvis_user_id,
            "auth_method": auth_method,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
        }
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        
        # Store the token mapping
        user_tokens[token] = jarvis_user_id
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "jarvis_user_id": jarvis_user_id,
            "auth_method": auth_method
        }
    except ValueError as ve:
        logger.error(f"Validation error in registration: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error in registration: {str(e)}")
        raise HTTPException(status_code=500, detail="Error during registration")

@app.post("/login", response_model=Token)
async def login(request: LoginRequest):
    """Login with username/email and either password or face authentication"""
    try:
        if not request.password and not request.face_image:
            raise HTTPException(
                status_code=400,
                detail="Either password or face image is required"
            )

        # Check if using face authentication
        if request.face_image:
            # Verify face using the face auth endpoint
            face_auth_result = await verify_face_auth(request.identifier, request.face_image)
            if not face_auth_result["success"]:
                raise HTTPException(
                    status_code=401,
                    detail="Face authentication failed"
                )
            jarvis_user_id = face_auth_result["user_id"]
            auth_method = "face_auth"
        else:
            # Traditional authentication
            jarvis_user_id = await bot.check_auth(request.identifier, request.password)
            if not jarvis_user_id:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid credentials"
                )
            auth_method = "traditional"
        
        # Generate JWT token
        token_data = {
            "sub": request.identifier,
            "jarvis_user_id": jarvis_user_id,
            "auth_method": auth_method,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
        }
        access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "jarvis_user_id": jarvis_user_id,
            "auth_method": auth_method
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in login: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )

# Dependency for verifying token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        jarvis_user_id: str = payload.get("jarvis_user_id")
        if username is None or jarvis_user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return {"username": username, "jarvis_user_id": jarvis_user_id}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# Logs endpoint - Write to Discord logs channel
@app.post("/logs")
async def write_log(log: LogEntry, current_user: str = Depends(get_current_user)):
    try:
        await bot.send_log(log.level, log.message, log.source)
        return {
            "status": "success",
            "timestamp": datetime.datetime.now().isoformat(),
            "message": "Log entry recorded to Discord"
        }
    except Exception as e:
        logger.error(f"Error writing log: {str(e)}")
        raise HTTPException(status_code=500, detail="Error writing log entry")

# Errors endpoint - Write to Discord errors channel
@app.post("/errors")
async def write_error(error: ErrorEntry, current_user: str = Depends(get_current_user)):
    try:
        await bot.send_error(error.error_type, error.message, error.source, error.stack_trace)
        return {
            "status": "success",
            "timestamp": datetime.datetime.now().isoformat(),
            "message": "Error entry recorded to Discord"
        }
    except Exception as e:
        logger.error(f"Error writing error log: {str(e)}")
        raise HTTPException(status_code=500, detail="Error writing error entry")

# Projects endpoint - Create post in Discord forum
@app.post("/projects")
async def create_project(project: Project, current_user: dict = Depends(get_current_user)):
    try:
        if project.jarvis_user_id != current_user["jarvis_user_id"]:
            raise HTTPException(
                status_code=403,
                detail="Project jarvis_user_id does not match authenticated user"
            )
            
        # Create project post in Discord forum
        try:
            message_id = await bot.create_project_post(
                project.jarvis_user_id,
                project.name,
                project.description,
                project.status
            )
            
            return {
                "status": "success",
                "timestamp": datetime.datetime.now().isoformat(),
                "message": f"Project {project.name} created successfully",
                "project_id": message_id
            }
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating project: {str(e)}")

# Face authentication endpoint - Write to Discord face-auth channel
@app.post("/face-auth")
async def face_authentication(request: FaceAuthRequest, current_user: str = Depends(get_current_user)):
    try:
        if not request.image_data:
            raise HTTPException(status_code=400, detail="Image data is required")
            
        # Clean up base64 image data if needed
        image_data = request.image_data
        if "data:image/png;base64," in image_data:
            image_data = image_data.split("data:image/png;base64,")[1]
            
        # Validate base64 data
        try:
            # Check if the base64 string is valid
            base64.b64decode(image_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {str(e)}")
            
        # Process with increased timeout
        try:
            message_id = await asyncio.wait_for(
                bot.send_face_auth(request.user_id, image_data),
                timeout=20.0  # 20 seconds timeout
            )
            
            return {
                "status": "success",
                "timestamp": datetime.datetime.now().isoformat(),
                "message": "Face authentication processed and stored in Discord",
                "face_auth_id": message_id
            }
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Face authentication processing timed out")
            
    except ValueError as ve:
        logger.error(f"Validation error in face authentication: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error in face authentication: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing face authentication")

@app.post("/face-auth/verify", response_model=FaceVerifyResponse)
async def verify_face(request: FaceVerifyRequest):
    """Verify face authentication"""
    try:
        # Verify the face
        result = await verify_face_auth(request.username, request.face_image)
        
        if result["success"]:
            # Generate JWT token
            token_data = {
                "sub": request.username,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)
            }
            access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
            
            return FaceVerifyResponse(
                success=True,
                message="Face verification successful",
                access_token=access_token,
                jarvis_user_id=result["user_id"]
            )
        else:
            return FaceVerifyResponse(
                success=False,
                message="Face verification failed"
            )
            
    except Exception as e:
        logger.error(f"Error in face verification: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Face verification failed: {str(e)}"
        )

@app.post("/face-auth/register", response_model=FaceAuthResponse)
async def register_face(request: FaceRegisterRequest):
    try:
        # Check if user already exists in Discord channel
        channel = await bot.get_channel_by_name('face-auth')
        async for message in channel.history(limit=None):
            if message.content.startswith(f"JARVIS_USER_ID: {request.username}"):
                return FaceAuthResponse(
                    success=False,
                    message="Username already exists"
                )

        # First store credentials in authentication channel
        auth_message_id = await bot.send_auth(request.username, request.email, request.password)

        # Then store face image in face-auth channel
        face_auth_id = await bot.send_face_auth(request.username, request.face_image)
        
        if not face_auth_id:
            raise ValueError("Failed to store face image")

        # Generate JWT token
        token_data = {
            "sub": request.username,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
        }
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        return FaceAuthResponse(
            success=True,
            message="Face registration successful",
            username=request.username,
            token=token
        )

    except Exception as e:
        logger.error(f"Error during face registration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error during face registration: {str(e)}"
        )

async def verify_face_auth(username: str, face_image: str) -> dict:
    """Helper function to verify face authentication"""
    try:
        # Get face-auth channel from Discord
        channel = await bot.get_channel_by_name('face-auth')
        
        # Decode current face image
        if 'data:image' in face_image:
            face_image = face_image.split(',')[1]
            
        img_data = base64.b64decode(face_image)
        nparr = np.frombuffer(img_data, np.uint8)
        current_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if current_img is None:
            raise ValueError("Failed to decode image")

        # Search for user's registered face in Discord channel
        async for message in channel.history(limit=None):
            if message.content.startswith(f"JARVIS_USER_ID: {username}"):
                if message.attachments:
                    # Get the first attachment
                    attachment = message.attachments[0]
                    # Download the image
                    img_data = await attachment.read()
                    nparr = np.frombuffer(img_data, np.uint8)
                    registered_face = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    # Verify face using DeepFace
                    result = DeepFace.verify(
                        img1_path=current_img,
                        img2_path=registered_face,
                        model_name="VGG-Face",
                        enforce_detection=False
                    )
                    
                    if result["verified"]:
                        return {
                            "success": True,
                            "user_id": str(message.id)
                        }
                    break

        return {
            "success": False,
            "user_id": None
        }

    except Exception as e:
        logger.error(f"Error in face verification: {str(e)}")
        raise ValueError(f"Face verification failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info") 