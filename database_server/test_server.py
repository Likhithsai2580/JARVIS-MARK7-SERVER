import aiohttp
import asyncio
import base64
from datetime import datetime
import logging
import json
import uuid
import cv2
import numpy as np
from io import BytesIO
from PIL import Image

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Server URL
BASE_URL = "http://127.0.0.1:8000"

async def get_token(session):
    """Get authentication token"""
    print("\n=== User Registration ===")
    username = input("Enter username: ")
    email = input("Enter email: ")
    password = input("Enter password: ")
    
    url = f"{BASE_URL}/token"
    data = {
        "username": username,
        "email": email,
        "password": password
    }
    
    async with session.post(url, json=data) as response:
        if response.status == 200:
            result = await response.json()
            print("\n✅ Successfully registered and got token!")
            return result["access_token"], result["jarvis_user_id"]
        else:
            error_text = await response.text()
            print(f"\n❌ Failed to get token: {error_text}")
            raise Exception(f"Failed to get token: {error_text}")

async def register_user(session, auth_type="traditional"):
    """Register a new user"""
    print("\n=== User Registration ===")
    username = input("Enter username: ")
    email = input("Enter email: ")
    password = input("Enter password: ")  # Always ask for password
    
    data = {
        "username": username,
        "email": email,
        "password": password
    }
    
    if auth_type == "face_auth":
        print("\nInitializing camera for face registration... (Press 'q' to capture)")
        face_image = await capture_face_image()
        if not face_image:
            return None, None
        data["face_image"] = face_image
    
    url = f"{BASE_URL}/token"
    
    try:
        async with session.post(url, json=data) as response:
            if response.status == 200:
                result = await response.json()
                print("\n✅ Successfully registered!")
                return result["access_token"], result["jarvis_user_id"]
            else:
                error_text = await response.text()
                print(f"\n❌ Failed to register: {error_text}")
                return None, None
    except Exception as e:
        print(f"\n❌ Registration error: {str(e)}")
        return None, None

async def login_user(session, auth_type="traditional"):
    """Login existing user"""
    print("\n=== User Login ===")
    
    try:
        if auth_type == "traditional":
            identifier = input("Enter username or email: ")
            password = input("Enter password: ")
            url = f"{BASE_URL}/login"
            data = {
                "identifier": identifier,
                "password": password
            }
        else:  # face_auth
            username = input("Enter username: ")
            password = input("Enter password: ")  # Always ask for password
            print("\nInitializing camera for face verification... (Press 'q' to capture)")
            face_image = await capture_face_image()
            if not face_image:
                return None, None
                
            url = f"{BASE_URL}/login"
            data = {
                "identifier": username,
                "password": password,
                "face_image": face_image
            }
        
        async with session.post(url, json=data) as response:
            if response.status == 200:
                result = await response.json()
                print("\n✅ Successfully logged in!")
                return result["access_token"], result["jarvis_user_id"]
            else:
                error_text = await response.text()
                error_data = json.loads(error_text)
                print(f"\n❌ Login failed: {error_data.get('detail', 'Unknown error')}")
                return None, None
                
    except Exception as e:
        print(f"\n❌ Login error: {str(e)}")
        return None, None

async def capture_face_image():
    """Capture face image from camera"""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open webcam")
        return None
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Could not capture frame")
                return None
            
            # Show preview
            cv2.imshow('Camera Preview (Press q to capture)', frame)
            
            # Wait for 'q' key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        try:
            # Convert frame to base64
            success, buffer = cv2.imencode('.png', frame)
            if not success:
                print("❌ Failed to encode image to PNG")
                return None
                
            base64_image = base64.b64encode(buffer).decode('utf-8')
            return f"data:image/png;base64,{base64_image}"
            
        except Exception as e:
            print(f"❌ Failed to convert image to base64: {str(e)}")
            return None
            
    except Exception as e:
        print(f"\n❌ Exception while capturing image: {str(e)}")
        return None
    finally:
        cap.release()
        cv2.destroyAllWindows()

async def test_logs(session, token):
    """Test logging endpoint"""
    print("\n=== Testing Logs ===")
    print("Enter log details:")
    
    log_levels = ["INFO", "WARNING", "ERROR"]
    for level in log_levels:
        message = input(f"Enter a {level} level message (or press Enter to skip): ")
        if message:
            log_entry = {
                "level": level,
                "message": message,
                "source": "test_script"
            }
            
            url = f"{BASE_URL}/logs"
            headers = {"Authorization": f"Bearer {token}"}
            
            async with session.post(url, json=log_entry, headers=headers) as response:
                if response.status == 200:
                    print(f"✅ Successfully sent {level} log")
                else:
                    print(f"❌ Failed to send {level} log: {await response.text()}")

async def test_errors(session, token):
    """Test error logging endpoint"""
    print("\n=== Testing Error Logging ===")
    error_message = input("Enter an error message (or press Enter to skip): ")
    
    if error_message:
        error_entry = {
            "error_type": "TestError",
            "message": error_message,
            "stack_trace": "File 'test.py', line 1\n  raise TestError('Test error')",
            "source": "test_script"
        }
        
        url = f"{BASE_URL}/errors"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with session.post(url, json=error_entry, headers=headers) as response:
            if response.status == 200:
                print("✅ Successfully sent error log")
            else:
                print(f"❌ Failed to send error log: {await response.text()}")

async def test_projects(session, token, jarvis_user_id):
    """Test project creation endpoint"""
    print("\n=== Testing Project Creation ===")
    create_project = input("Would you like to create a project? (y/n): ").lower()
    
    if create_project == 'y':
        project_name = input("Enter project name: ")
        description = input("Enter project description: ")
        status = input("Enter project status (active/pending/completed): ")
        
        project = {
            "name": project_name,
            "description": description,
            "status": status,
            "jarvis_user_id": jarvis_user_id
        }
        
        url = f"{BASE_URL}/projects"
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            async with session.post(url, json=project, headers=headers) as response:
                result = await response.json()
                if response.status == 200:
                    print(f"\n✅ Successfully created project '{project_name}'")
                    print(f"Project ID: {result.get('project_id')}")
                    return result.get('project_id')
                else:
                    print(f"\n❌ Failed to create project:")
                    print(f"Status code: {response.status}")
                    print(f"Error details: {result.get('detail', 'Unknown error')}")
                    return None
        except Exception as e:
            print(f"\n❌ Exception while creating project: {str(e)}")
            return None

async def test_face_auth(session, token):
    """Test face authentication endpoint"""
    print("\n=== Testing Face Authentication ===")
    use_camera = input("Would you like to test face authentication using your camera? (y/n): ").lower()
    
    if use_camera == 'y':
        print("\nInitializing camera... (Press 'q' to capture)")
        face_image = await capture_face_image()
        if not face_image:
            return None
        
        url = f"{BASE_URL}/face-auth"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "user_id": "test_user_id",
            "image_data": face_image
        }
        
        # Add retry logic
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=30)  # 30 seconds timeout
                async with session.post(url, json=data, headers=headers, timeout=timeout) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"\n✅ Successfully sent face auth")
                        print(f"Face Auth ID: {result.get('face_auth_id')}")
                        return result.get('face_auth_id')
                    else:
                        error_text = await response.text()
                        print(f"\n❌ Failed to send face auth: {error_text}")
                        return None
                        
            except asyncio.TimeoutError:
                print(f"\n⚠️ Attempt {attempt + 1} timed out, retrying...")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                continue
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"\n⚠️ Attempt {attempt + 1} failed: {str(e)}, retrying...")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    print(f"\n❌ All attempts failed: {str(e)}")
                    return None

async def main():
    """Main test function"""
    print("=== JARVIS Server Test Suite ===")
    print("This script will help you test various endpoints of the JARVIS server.")
    
    # Configure timeout
    timeout = aiohttp.ClientTimeout(
        total=30,      # Total timeout
        connect=10,    # Connection timeout
        sock_read=10   # Socket read timeout
    )
    
    # Create session with timeout
    connector = aiohttp.TCPConnector(force_close=True)
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        try:
            # Authentication choice
            print("\n=== Authentication ===")
            print("1. Register new user")
            print("2. Login existing user")
            auth_choice = input("\nEnter your choice (1-2): ")
            
            if auth_choice not in ['1', '2']:
                print("❌ Invalid choice")
                return
                
            # Authentication method choice
            print("\n=== Authentication Method ===")
            print("1. Traditional (username/password)")
            print("2. Face Authentication")
            method_choice = input("\nEnter your choice (1-2): ")
            
            if method_choice not in ['1', '2']:
                print("❌ Invalid choice")
                return
                
            auth_type = "traditional" if method_choice == '1' else "face_auth"
            
            # Get token based on choice
            if auth_choice == '1':
                token, jarvis_user_id = await register_user(session, auth_type)
            else:
                token, jarvis_user_id = await login_user(session, auth_type)
                
            if not token or not jarvis_user_id:
                print("❌ Authentication failed")
                return
            
            # Main test menu
            while True:
                print("\n=== Test Menu ===")
                print("1. Test Logs")
                print("2. Test Errors")
                print("3. Test Projects")
                print("4. Test Face Authentication")
                print("5. Exit")
                
                choice = input("\nEnter your choice (1-5): ")
                
                if choice == '1':
                    await test_logs(session, token)
                elif choice == '2':
                    await test_errors(session, token)
                elif choice == '3':
                    await test_projects(session, token, jarvis_user_id)
                elif choice == '4':
                    await test_face_auth(session, token)
                elif choice == '5':
                    print("\nExiting test suite. Goodbye!")
                    break
                else:
                    print("\nInvalid choice. Please try again.")
            
        except Exception as e:
            print(f"\n❌ Test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 