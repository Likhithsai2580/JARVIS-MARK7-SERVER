from .server_template import BaseServer
from fastapi import HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from typing import Optional, Dict
import asyncio
import cv2
import numpy as np
import base64
from PIL import Image
import io
from deepface import DeepFace
import os
import json
import logging
from utils import setup_server, DataManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthRequest(BaseModel):
    user_id: str
    metadata: Optional[Dict] = None

class FaceAuthServer(BaseServer):
    def __init__(self):
        super().__init__("FaceAuth")
        self.data_manager, self.server_manager = setup_server()
        
        @self.app.post("/register")
        async def register_face(
            user_id: str = Form(...),
            face_image: UploadFile = File(...),
            email: Optional[str] = Form(None),
            password: Optional[str] = Form(None)
        ):
            self.set_busy(True)
            try:
                await self.logger.log(
                    message=f"Processing face registration for user {user_id}",
                    log_type="info",
                    details={"email": email}
                )
                response = await self.process_registration(user_id, face_image, email, password)
                await self.logger.log(
                    message=f"Face registration successful for user {user_id}",
                    log_type="info"
                )
                return response
            except Exception as e:
                await self.logger.log(
                    message=f"Face registration failed for user {user_id}: {str(e)}",
                    log_type="error",
                    details={"error": str(e)}
                )
                raise
            finally:
                self.set_busy(False)
        
        @self.app.post("/verify")
        async def verify_face(face_image: UploadFile = File(...)):
            self.set_busy(True)
            try:
                await self.logger.log(
                    message="Processing face verification",
                    log_type="info"
                )
                response = await self.process_verification(face_image)
                await self.logger.log(
                    message="Face verification completed",
                    log_type="info",
                    details={"verified": response.get("verified", False)}
                )
                return response
            except Exception as e:
                await self.logger.log(
                    message=f"Face verification failed: {str(e)}",
                    log_type="error",
                    details={"error": str(e)}
                )
                raise
            finally:
                self.set_busy(False)
        
        @self.app.delete("/user/{user_id}")
        async def delete_user(user_id: str):
            """Delete user's face data"""
            try:
                await self.logger.log(
                    message=f"Attempting to delete user {user_id}",
                    log_type="info"
                )
                
                if user_id not in self.data_manager.users_cache:
                    await self.logger.log(
                        message=f"User {user_id} not found for deletion",
                        log_type="warning"
                    )
                    raise HTTPException(status_code=404, detail=f"User {user_id} not found")
                
                # Get user data before deletion
                user_data = self.data_manager.users_cache[user_id]
                
                # Delete face images
                for face_path in user_data.get('face_paths', []):
                    if os.path.exists(face_path):
                        os.remove(face_path)
                
                # Remove user directory if empty
                user_dir = os.path.join(self.data_manager.data_dir, user_id)
                if os.path.exists(user_dir) and not os.listdir(user_dir):
                    os.rmdir(user_dir)
                
                # Queue user deletion
                deletion_data = {user_id: None}
                self.data_manager.queue_write(deletion_data)
                
                await self.logger.log(
                    message=f"Successfully deleted user {user_id}",
                    log_type="info"
                )
                
                return {"status": "success", "message": f"Deleted user {user_id}"}
            except Exception as e:
                await self.logger.log(
                    message=f"Failed to delete user {user_id}: {str(e)}",
                    log_type="error",
                    details={"error": str(e)}
                )
                raise HTTPException(status_code=500, detail=str(e))
    
    async def process_registration(self, user_id: str, face_image: UploadFile, email: Optional[str], password: Optional[str]) -> Dict:
        """Process face registration"""
        try:
            # Check if user exists
            if user_id in self.data_manager.users_cache:
                raise HTTPException(status_code=400, detail="User already exists")
            
            # Read and validate image
            contents = await face_image.read()
            img = self._process_image_data(contents)
            
            # Detect faces
            faces = self._detect_faces(img)
            if not faces:
                raise HTTPException(status_code=400, detail="No face detected in image")
            
            # Save face image
            user_dir = os.path.join(self.data_manager.data_dir, user_id)
            os.makedirs(user_dir, exist_ok=True)
            face_path = os.path.join(user_dir, f"{user_id}.jpg")
            cv2.imwrite(face_path, img)
            
            # Prepare user data
            user_data = {
                user_id: {
                    'username': user_id,
                    'email': email,
                    'password': password,
                    'face_paths': [face_path],
                    'failed_attempts': 0
                }
            }
            
            # Queue data write
            self.data_manager.queue_write(user_data)
            
            return {
                "status": "success",
                "user_id": user_id,
                "message": "Face registered successfully"
            }
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def process_verification(self, face_image: UploadFile) -> Dict:
        """Process face verification"""
        try:
            # Read and validate image
            contents = await face_image.read()
            img = self._process_image_data(contents)
            
            # Detect faces
            faces = self._detect_faces(img)
            if not faces:
                raise HTTPException(status_code=400, detail="No face detected in image")
            
            # Save temporary image for verification
            temp_path = os.path.join(self.data_manager.data_dir, "temp_verify.jpg")
            cv2.imwrite(temp_path, img)
            
            try:
                # Find matching face
                matches = []
                for username, user_data in self.data_manager.users_cache.items():
                    for face_path in user_data.get('face_paths', []):
                        try:
                            result = DeepFace.verify(
                                img1_path=temp_path,
                                img2_path=face_path,
                                enforce_detection=False,
                                model_name="VGG-Face",
                                distance_metric="cosine"
                            )
                            
                            if result.get('verified', False):
                                similarity = 1 - result.get('distance', 1.0)
                                matches.append((username, similarity))
                        except Exception as e:
                            logger.error(f"Face comparison error: {str(e)}")
                            continue
                
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                if matches:
                    # Get best match
                    matches.sort(key=lambda x: x[1], reverse=True)
                    best_match, confidence = matches[0]
                    
                    return {
                        "status": "success",
                        "verified": True,
                        "user_id": best_match,
                        "confidence": f"{confidence:.2%}"
                    }
                else:
                    return {
                        "status": "success",
                        "verified": False,
                        "message": "No matching face found"
                    }
                    
            finally:
                # Ensure temporary file is removed
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            logger.error(f"Verification error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def _process_image_data(self, image_data: bytes) -> np.ndarray:
        """Process image data into OpenCV format"""
        try:
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Failed to decode image")
            return img
        except Exception as e:
            raise ValueError(f"Invalid image data: {str(e)}")
    
    def _detect_faces(self, img: np.ndarray) -> list:
        """Detect faces in image with multiple parameter attempts"""
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Try with default parameters
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        # If no faces found, try with more lenient parameters
        if len(faces) == 0:
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,
                minNeighbors=3,
                minSize=(20, 20)
            )
        
        return faces

if __name__ == "__main__":
    server = FaceAuthServer()
    server.run() 