from flask import Flask, request, jsonify
from deepface import DeepFace
import numpy as np
import base64
import io
from PIL import Image
import os
import json
import cv2
import logging
from flask_cors import CORS  # Add CORS support
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS

# Directory to store user data and models
DATA_DIR = "user_data"
USERS_FILE = "users.json"

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# Load existing users if available
users_db = {}
if os.path.exists(os.path.join(DATA_DIR, USERS_FILE)):
    with open(os.path.join(DATA_DIR, USERS_FILE), 'r') as f:
        users_db = json.load(f)

def base64_to_image(base64_string):
    try:
        # Remove header if present
        if 'data:image' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # Decode base64 string to bytes
        img_data = base64.b64decode(base64_string)
        
        # Convert to PIL Image
        img = Image.open(io.BytesIO(img_data))
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Convert to OpenCV format
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    except Exception as e:
        logger.error(f"Error converting base64 to image: {str(e)}")
        raise e

@app.route('/register', methods=['POST'])
def register():
    logger.info("Starting registration process")
    try:
        data = request.get_json()
        logger.debug(f"Received data: {data}")  # Log the received data

        if not data:
            logger.error("No JSON data received")
            return jsonify({'error': 'No data received'}), 400

        if 'username' not in data or 'password' not in data or 'image' not in data:
            logger.error("Missing username, password, or image in request")
            return jsonify({'error': 'Missing username, password, or image'}), 400

        username = data['username']
        password = data['password']
        logger.debug(f"Processing registration for username: {username}")

        # Convert base64 to image
        try:
            image = base64_to_image(data['image'])
            logger.info("Successfully decoded image")
        except Exception as e:
            logger.error(f"Failed to decode image: {str(e)}")
            return jsonify({'error': 'Invalid image data'}), 400
        
        # Create user directory
        user_dir = os.path.join(DATA_DIR, username)
        os.makedirs(user_dir, exist_ok=True)
        
        # Get number of existing images for this user
        existing_images = len(os.listdir(user_dir))
        image_path = os.path.join(user_dir, f'face_{existing_images + 1}.jpg')
        
        # Save image
        cv2.imwrite(image_path, image)
        logger.info(f"Saved face image: {image_path}")
        
        # Update users database
        if username not in users_db:
            users_db[username] = {'password': password, 'face_paths': []}
        users_db[username]['face_paths'].append(image_path)
        
        # Save updated users database
        with open(os.path.join(DATA_DIR, USERS_FILE), 'w') as f:
            json.dump(users_db, f, indent=4)
        
        logger.info(f"Registration successful for user: {username}")
        return jsonify({
            'message': 'Registration successful',
            'face_count': len(users_db[username]['face_paths'])
        }), 200
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    logger.info("Starting login process")
    try:
        data = request.get_json()
        logger.debug(f"Received login data: {data}")

        if not data or 'image' not in data:
            logger.error("Missing image data for login")
            return jsonify({'error': 'Image data is required for login'}), 400

        face_image = data['image']
        logger.debug("Processing face verification")

        # Convert base64 to image
        try:
            img = base64_to_image(face_image)
            logger.info("Successfully decoded login image")
        except Exception as e:
            logger.error(f"Failed to decode login image: {str(e)}")
            return jsonify({'error': 'Invalid image data'}), 400

        # Save temporary image for face recognition
        temp_path = os.path.join(DATA_DIR, f"temp_{uuid.uuid4().hex}.jpg")
        cv2.imwrite(temp_path, img)
        logger.info(f"Saved temporary login image to: {temp_path}")

        try:
            # Perform face verification against all users
            matches = []
            for username, user_data in users_db.items():
                for face_path in user_data.get('face_paths', []):
                    if not os.path.exists(face_path):
                        logger.warning(f"Face image not found: {face_path}")
                        continue
                    try:
                        result = DeepFace.verify(
                            img1_path=temp_path,
                            img2_path=face_path,
                            enforce_detection=False,
                            model_name="VGG-Face"
                        )
                        
                        if result['verified']:
                            similarity = 1 - result['distance']
                            matches.append((username, similarity))
                            logger.info(f"Match found for {username} with similarity {similarity:.2%}")
                    except Exception as e:
                        logger.error(f"Error comparing faces: {str(e)}")
                        continue
            
            # Cleanup temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.info(f"Removed temporary file: {temp_path}")
            
            if matches:
                # Sort matches by similarity
                matches.sort(key=lambda x: x[1], reverse=True)
                best_match, highest_similarity = matches[0]
                
                if highest_similarity > 0.6:
                    logger.info(f"Login successful for {best_match} with confidence {highest_similarity:.2%}")
                    return jsonify({
                        'message': 'Login successful',
                        'username': best_match,
                        'confidence': f'{highest_similarity:.2%}'
                    }), 200
            
            logger.warning("No face match found with sufficient confidence")
            return jsonify({'error': 'Face not recognized or confidence too low'}), 401

        except Exception as e:
            logger.error(f"Error during face verification: {str(e)}")
            return jsonify({'error': 'Face verification failed'}), 500

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/traditional_login', methods=['POST'])
def traditional_login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            logger.error("Username and password are required for traditional login")
            return jsonify({'error': 'Username and password are required.'}), 400

        users_file = os.path.join(DATA_DIR, 'users.json')
        if os.path.exists(users_file):
            with open(users_file, 'r') as f:
                users = json.load(f)
        else:
            users = {}

        user = users.get(username)
        if not user:
            logger.error(f"Traditional login failed: User {username} does not exist")
            return jsonify({'error': 'User does not exist.'}), 401

        # In production, use hashed passwords!
        if user.get('password') != password:
            logger.error(f"Traditional login failed: Incorrect password for user {username}")
            return jsonify({'error': 'Incorrect password.'}), 401

        logger.info(f"Traditional login successful for user: {username}")
        return jsonify({
            'message': 'Traditional login successful',
            'username': username
        }), 200

    except Exception as e:
        logger.error(f"Traditional Login error: {str(e)}")
        return jsonify({'error': 'Traditional login failed.'}), 500

@app.route('/auth', methods=['POST', 'OPTIONS'])
def auth():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    try:
        logger.info("Received auth request")
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data received'}), 400
            
        mode = data.get('mode')
        logger.info(f"Auth mode: {mode}")
        
        if mode == 'login':
            face_image = data.get('faceImage')
            if not face_image:
                return jsonify({'error': 'Face image is required'}), 400
                
            # Convert base64 to image
            try:
                img = base64_to_image(face_image)
                logger.info("Successfully decoded login image")
            except Exception as e:
                logger.error(f"Failed to decode login image: {str(e)}")
                return jsonify({'error': 'Invalid image data'}), 400

            # Create temporary directory for login attempt
            temp_dir = os.path.join(DATA_DIR, f"temp_{uuid.uuid4().hex}")
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, "temp.jpg")
            cv2.imwrite(temp_path, img)
            
            try:
                # Load users database
                users_file = os.path.join(DATA_DIR, USERS_FILE)
                if os.path.exists(users_file):
                    with open(users_file, 'r') as f:
                        users_db = json.load(f)
                else:
                    users_db = {}
                
                # Perform face verification against all users
                matches = []
                for username, user_data in users_db.items():
                    face_paths = user_data.get('face_paths', [])
                    if not face_paths:
                        continue
                        
                    for face_path in face_paths:
                        if not os.path.exists(face_path):
                            logger.warning(f"Face image not found: {face_path}")
                            continue
                            
                        try:
                            result = DeepFace.verify(
                                img1_path=temp_path,
                                img2_path=face_path,
                                enforce_detection=False,
                                model_name="VGG-Face"
                            )
                            
                            if result['verified']:
                                similarity = 1 - result['distance']
                                matches.append((username, similarity))
                                logger.info(f"Match found for {username} with similarity {similarity:.2%}")
                                
                        except Exception as e:
                            logger.error(f"Error comparing faces: {str(e)}")
                            continue
                
                # Cleanup
                import shutil
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temporary directory: {temp_dir}")
                
                if matches:
                    matches.sort(key=lambda x: x[1], reverse=True)
                    best_match, highest_similarity = matches[0]
                    
                    if highest_similarity > 0.6:
                        logger.info(f"Login successful for {best_match} with confidence {highest_similarity:.2%}")
                        return jsonify({
                            'message': 'Login successful',
                            'username': best_match,
                            'confidence': f'{highest_similarity:.2%}'
                        }), 200
                
                logger.warning("No face match found with sufficient confidence")
                return jsonify({'error': 'Face not recognized'}), 401

            except Exception as e:
                logger.error(f"Face verification error: {str(e)}")
                return jsonify({'error': 'Face verification failed'}), 500
                
        else:
            return jsonify({'error': 'Invalid mode'}), 400
            
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
