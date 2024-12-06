from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import base64
import logging
import os
import json
from deepface import DeepFace
import uuid
import logging.handlers
from werkzeug.serving import WSGIRequestHandler
import logging
import re

WSGIRequestHandler.triggered_reload = lambda self: None  # Prevent auto-reload during requests

app = Flask(__name__)

# Configure CORS with secure settings
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5173"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 3600,
        "send_wildcard": False
    }
})

# Add security headers to all responses
@app.after_request 
def add_security_headers(response):
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Accept')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Max-Age', '3600')
    response.headers.add('X-Content-Type-Options', 'nosniff')
    response.headers.add('X-Frame-Options', 'DENY')
    response.headers.add('X-XSS-Protection', '1; mode=block')
    response.headers.add('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
    return response

# Create data directory if it doesn't exist
DATA_DIR = "user_data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)
    logger.info(f"Created data directory at {DATA_DIR}")

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            'server.log',
            maxBytes=1024*1024,
            backupCount=5
        )
    ]
)
logger = logging.getLogger(__name__)

# Define constants
MAX_FAILED_ATTEMPTS = 5  # Maximum allowed failed face recognition attempts

@app.route('/auth', methods=['POST'])
def auth():
    try:
        logger.info("Received auth request")
        data = request.json
        mode = data.get('mode')
        logger.info(f"Auth mode: {mode}")
        
        if mode == 'register':
            username = data.get('username')
            password = data.get('password')
            email = data.get('email')
            face_image = data.get('faceImage')
            
            logger.info(f"Processing registration for user: {username}")
            logger.debug("Validating registration fields")
            
            if not all([username, password, email, face_image]):
                logger.error(f"Missing registration fields - Username: {'✓' if username else '✗'}, "
                           f"Email: {'✓' if email else '✗'}, "
                           f"Password: {'✓' if password else '✗'}, "
                           f"Face Image: {'✓' if face_image else '✗'}")
                return jsonify({
                    'success': False,
                    'error': 'All fields (username, email, password, and face image) are required'
                }), 400

            # Email format validation
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, email):
                return jsonify({
                    'success': False,
                    'error': 'Invalid email format'
                }), 400

            # Check if user already exists
            users_file = os.path.join(DATA_DIR, 'users.json')
            logger.debug(f"Checking if user exists in {users_file}")
            if os.path.exists(users_file):
                with open(users_file, 'r') as f:
                    users = json.load(f)
                    if username in users:
                        logger.error(f"Registration failed: User {username} already exists")
                        return jsonify({
                            'success': False,
                            'error': 'Username already exists'
                        }), 400

            try:
                # Process face image
                logger.info("Processing face image")
                logger.debug("Decoding base64 image data")
                img_data = base64.b64decode(face_image.split(',')[1] if ',' in face_image else face_image)
                img = cv2.imdecode(np.frombuffer(img_data, np.uint8), cv2.IMREAD_COLOR)
                
                # Verify face is present
                logger.debug("Detecting faces in image")
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                
                if len(faces) == 0:
                    logger.error("No face detected in registration image")
                    return jsonify({
                        'success': False,
                        'error': 'No face detected in image'
                    }), 400
                
                logger.info(f"Detected {len(faces)} faces in image")
                
                # Save face image
                user_dir = os.path.join(DATA_DIR, username)
                os.makedirs(user_dir, exist_ok=True)
                face_path = os.path.join(user_dir, f"{username}.jpg")
                cv2.imwrite(face_path, img)
                logger.info(f"Saved face image to: {face_path}")

                # Update users database
                logger.debug("Updating users database")
                users = users if os.path.exists(users_file) else {}
                users[username] = {
                    'username': username,
                    'password': password,
                    'email': email,
                    'face_paths': [face_path],
                    'failed_attempts': 0
                }

                with open(users_file, 'w') as f:
                    json.dump(users, f, indent=4)
                logger.info(f"Successfully registered user: {username}")

                return jsonify({
                    'success': True,
                    'message': 'Registration successful',
                    'username': username
                }), 200

            except Exception as e:
                logger.error(f"Error during registration process: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': f'Registration failed: {str(e)}'
                }), 500

        elif mode == 'login':
            try:
                face_image = data.get('faceImage')
                if not face_image:
                    logger.error("No face image provided in login request")
                    return jsonify({
                        'success': False,
                        'error': 'Face image is required for login'
                    }), 400

                try:
                    # Process the image in memory first
                    if 'data:image' in face_image:
                        face_image = face_image.split(',')[1]
                    
                    img_data = base64.b64decode(face_image)
                    nparr = np.frombuffer(img_data, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if img is None:
                        logger.error("Failed to decode image data")
                        raise ValueError("Failed to decode image")

                    # More lenient face detection parameters
                    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    
                    # Adjust these parameters for more lenient face detection
                    faces = face_cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.1,  # Smaller value = more detections but slower (was 1.3)
                        minNeighbors=3,   # Smaller value = more detections but more false positives (was 5)
                        minSize=(30, 30)  # Minimum face size to detect
                    )
                    
                    if len(faces) == 0:
                        # Try with even more lenient parameters
                        faces = face_cascade.detectMultiScale(
                            gray,
                            scaleFactor=1.05,
                            minNeighbors=2,
                            minSize=(20, 20)
                        )
                        
                    if len(faces) == 0:
                        logger.error("No face detected in login image")
                        return jsonify({
                            'success': False,
                            'error': 'No face detected in image. Please ensure your face is clearly visible and well-lit.'
                        }), 400

                    # Log face detection details
                    logger.info(f"Detected {len(faces)} faces in image")
                    for (x, y, w, h) in faces:
                        logger.info(f"Face detected at position: x={x}, y={y}, width={w}, height={h}")

                    # Use the largest face if multiple faces are detected
                    if len(faces) > 1:
                        faces = sorted(faces, key=lambda x: x[2] * x[3], reverse=True)  # Sort by area
                        logger.info("Multiple faces detected, using the largest face")

                    # Extract and save the face region with padding
                    x, y, w, h = faces[0]
                    padding = 40  # Add padding around the face
                    start_y = max(y - padding, 0)
                    start_x = max(x - padding, 0)
                    end_y = min(y + h + padding, img.shape[0])
                    end_x = min(x + w + padding, img.shape[1])
                    
                    face_img = img[start_y:end_y, start_x:end_x]

                    # Create a unique directory for this login attempt
                    login_attempt_dir = os.path.join(DATA_DIR, f"login_attempt_{uuid.uuid4().hex}")
                    os.makedirs(login_attempt_dir, exist_ok=True)
                    
                    # Save temporary image
                    temp_path = os.path.join(login_attempt_dir, "temp.jpg")
                    if not cv2.imwrite(temp_path, face_img):  # Save the face region instead of full image
                        raise ValueError("Failed to save temporary image")
                    
                    logger.info(f"Temporary image saved at: {temp_path}")

                    try:
                        # Load users database
                        users_file = os.path.join(DATA_DIR, 'users.json')
                        if not os.path.exists(users_file):
                            raise FileNotFoundError("Users database not found")

                        with open(users_file, 'r') as f:
                            users = json.load(f)

                        # Try to find matching face
                        matches = []
                        for username, user_data in users.items():
                            logger.info(f"Comparing with user: {username}")
                            face_paths = user_data.get('face_paths', [])
                            
                            for face_path in face_paths:
                                if not os.path.exists(face_path):
                                    logger.warning(f"Stored face image not found: {face_path}")
                                    continue

                                try:
                                    logger.info(f"Attempting face verification with: {face_path}")
                                    result = DeepFace.verify(
                                        img1_path=temp_path,
                                        img2_path=face_path,
                                        enforce_detection=False,
                                        model_name="VGG-Face",
                                        distance_metric="cosine"
                                    )
                                    
                                    logger.info(f"Verification result: {result}")
                                    
                                    if result.get('verified', False):
                                        matches.append((username, result.get('distance', 1.0)))
                                        logger.info(f"Match found: {username} with distance {result.get('distance', 1.0)}")

                                except Exception as e:
                                    logger.error(f"Face comparison error with {face_path}: {str(e)}")
                                    continue

                        # Process results
                        if matches:
                            # Sort by confidence (lower distance is better)
                            matches.sort(key=lambda x: x[1])
                            best_match, best_distance = matches[0]
                            
                            logger.info(f"Best match: {best_match} with distance {best_distance}")
                            return jsonify({
                                'success': True,
                                'message': 'Login successful',
                                'username': best_match,
                                'confidence': f"{(1 - best_distance) * 100:.2f}%"
                            }), 200
                        else:
                            logger.warning("No matching faces found")
                            return jsonify({
                                'success': False,
                                'error': 'Face not recognized'
                            }), 401

                    finally:
                        # Clean up
                        try:
                            import shutil
                            shutil.rmtree(login_attempt_dir)
                            logger.info(f"Cleaned up login attempt directory: {login_attempt_dir}")
                        except Exception as e:
                            logger.error(f"Error cleaning up temporary files: {str(e)}")

                except Exception as e:
                    logger.error(f"Image processing error: {str(e)}")
                    return jsonify({
                        'success': False,
                        'error': f'Failed to process image: {str(e)}'
                    }), 400

            except Exception as e:
                logger.error(f"Login error: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        else:
            return jsonify({
                'success': False,
                'error': 'Invalid mode'
            }), 400

    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/traditional_login', methods=['POST'])
def traditional_login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Username and password are required.'}), 400

        users_file = os.path.join(DATA_DIR, 'users.json')
        if os.path.exists(users_file):
            with open(users_file, 'r') as f:
                users = json.load(f)
        else:
            users = {}

        user = users.get(username)
        if not user:
            return jsonify({'error': 'User does not exist.'}), 401

        # In production, use hashed passwords!
        if user.get('password') != password:
            return jsonify({'error': 'Incorrect password.'}), 401

        return jsonify({
            'message': 'Traditional login successful',
            'username': username
        }), 200

    except Exception as e:
        logger.error(f"Traditional Login error: {str(e)}")
        return jsonify({'error': 'Traditional login failed.'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False) 