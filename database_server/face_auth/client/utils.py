import base64
import cv2
import requests
import json
from PIL import Image, ImageTk
import io
import logging
from flask import jsonify
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVER_URL = "http://127.0.0.1:5001"
USERS_DIR = "users"
if not os.path.exists(USERS_DIR):
    os.makedirs(USERS_DIR)

def capture_image():
    """Capture image from webcam and return base64 string"""
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    print(f"ret: {ret}, frame: {frame}")
    cap.release()
    
    if not ret:
        raise Exception("Could not capture image from webcam")
    
    # Convert to jpg
    _, buffer = cv2.imencode('.jpg', frame)
    # Convert to base64
    base64_image = base64.b64encode(buffer).decode('utf-8')
    return base64_image, frame

def register_user(face_image_base64, password, username):
    """Register a new user with face image, password, and username"""
    try:
        response = requests.post(
            f"{SERVER_URL}/register",
            json={
                'username': username,
                'password': password,
                'image': face_image_base64
            }
        )
        return response.json()
    except Exception as e:
        logger.error(f"Registration request failed: {str(e)}")
        return {"error": f"Registration request failed: {str(e)}"}

def login_user(face_image_base64):
    """Login with face image"""
    try:
        logger.info("Sending login request to server")
        response = requests.post(
            f"{SERVER_URL}/auth",
            json={
                'mode': 'login',
                'faceImage': face_image_base64
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code != 200:
            logger.error(f"Server error: {response.text}")
            return {"error": f"Server error: {response.text}"}
            
        return response.json()
    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to server")
        return {"error": "Could not connect to server. Please ensure the server is running."}
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return {"error": f"Login error: {str(e)}"}

def convert_cv2_to_tkinter(cv2_image):
    """Convert OpenCV image to Tkinter compatible image"""
    # Convert from BGR to RGB
    rgb_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
    # Convert to PIL Image
    pil_image = Image.fromarray(rgb_image)
    # Convert to PhotoImage
    return ImageTk.PhotoImage(pil_image)

def login_user_traditional(username, password):
    """Traditional login using username and password"""
    try:
        response = requests.post(
            f"{SERVER_URL}/traditional_login",
            json={
                'username': username,
                'password': password
            }
        )
        return response.json()
    except Exception as e:
        logger.error(f"Traditional login request failed: {str(e)}")
        return {"error": f"Traditional login request failed: {str(e)}"}