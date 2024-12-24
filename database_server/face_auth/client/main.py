import tkinter as tk
from tkinter import ttk, messagebox
import cv2
from utils import register_user, login_user, convert_cv2_to_tkinter, login_user_traditional, capture_image
import threading
import time
import base64
import requests
from queue import Queue
import numpy as np
from collections import deque

class FaceAuthApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Face Authentication")
        self.root.geometry("800x600")
        
        # Variables
        self.username = tk.StringVar()
        self.preview_image = None
        self.captured_image = None
        self.captured_base64 = None
        self.camera_active = False
        self.cap = None
        
        self.api_queue = Queue()
        self.start_api_thread()
        
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.registration_angles = deque(['front', 'left', 'right'])
        self.captured_angles = {}
        self.password = tk.StringVar()
        
        # Add a variable to track failed login attempts
        self.failed_login_attempts = 0
        self.max_failed_attempts = 3  # Threshold for fallback to traditional login
        
        self.setup_ui()
        self.initialize_camera()
    
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Center frame for auth buttons
        auth_frame = ttk.Frame(main_frame)
        auth_frame.grid(row=0, column=0, columnspan=2, pady=20)
        
        # Style configuration for buttons
        style = ttk.Style()
        style.configure('Auth.TButton', 
                       padding=10, 
                       font=('Helvetica', 12, 'bold'),
                       width=20)
        
        # Auth buttons
        ttk.Button(auth_frame, 
                  text="Login with Face", 
                  command=self.login,
                  style='Auth.TButton').pack(pady=10)
        
        ttk.Button(auth_frame, 
                  text="Register New User", 
                  command=self.show_registration_form,
                  style='Auth.TButton').pack(pady=10)
        
        # Registration frame (initially hidden)
        self.registration_frame = ttk.LabelFrame(main_frame, text="Registration", padding="10")
        self.registration_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        self.registration_frame.grid_remove()  # Hide initially
        
        # Registration fields
        ttk.Label(self.registration_frame, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.username_entry = ttk.Entry(self.registration_frame, textvariable=self.username)
        self.username_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(self.registration_frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.password_entry = ttk.Entry(self.registration_frame, textvariable=self.password, show="*")
        self.password_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Camera preview (initially hidden)
        self.preview_frame = ttk.Frame(main_frame)
        self.preview_frame.grid(row=2, column=0, columnspan=2, pady=10)
        self.preview_frame.grid_remove()  # Hide initially
        
        self.preview_label = ttk.Label(self.preview_frame, text="Camera preview")
        self.preview_label.pack(pady=5)
        
        # Camera controls
        self.camera_btn = ttk.Button(self.preview_frame, text="Start Camera", command=self.toggle_camera)
        self.camera_btn.pack(pady=5)
        
        ttk.Button(self.preview_frame, text="Capture", command=self.capture).pack(pady=5)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="")
        self.status_label.grid(row=3, column=0, columnspan=2, pady=5)
        
        # Traditional login frame (initially hidden)
        self.traditional_login_frame = ttk.LabelFrame(main_frame, text="Traditional Login", padding="10")
        self.traditional_login_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        self.traditional_login_frame.grid_remove()

    def initialize_camera(self):
        """Try to initialize the camera and update UI accordingly"""
        try:
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Try DirectShow
            if not self.cap.isOpened():
                raise Exception("Could not open camera")
            
            # Test capture
            ret, _ = self.cap.read()
            if not ret:
                raise Exception("Could not read from camera")
            
            self.camera_active = True
            self.camera_btn.config(text="Stop Camera")
            self.status_label.config(text="Camera initialized successfully")
            self.camera_thread = threading.Thread(target=self.update_preview, daemon=True)
            self.camera_thread.start()
            
        except Exception as e:
            self.camera_active = False
            self.status_label.config(text=f"Camera error: {str(e)}")
            messagebox.showerror("Camera Error", 
                               "Could not initialize camera. Please ensure:\n"
                               "1. Camera is connected\n"
                               "2. No other application is using the camera\n"
                               "3. Camera permissions are granted")
    
    def toggle_camera(self):
        """Toggle camera on/off"""
        if self.camera_active:
            self.camera_active = False
            if self.cap:
                self.cap.release()
            self.cap = None
            self.camera_btn.config(text="Start Camera")
            self.preview_label.config(image='', text="Camera stopped")
        else:
            self.initialize_camera()
    
    def update_preview(self):
        """Update camera preview"""
        while self.camera_active:
            try:
                if self.cap and self.cap.isOpened():
                    ret, frame = self.cap.read()
                    if ret:
                        # Resize frame to fit UI
                        frame = cv2.resize(frame, (640, 480))
                        # Convert to Tkinter image
                        photo = convert_cv2_to_tkinter(frame)
                        # Update label
                        self.preview_label.configure(image=photo)
                        self.preview_label.image = photo
                    else:
                        self.status_label.config(text="Failed to grab frame")
                time.sleep(0.03)  # Limit to ~30 FPS
            except Exception as e:
                self.status_label.config(text=f"Preview error: {str(e)}")
                time.sleep(1)  # Wait before retrying
    
    def capture(self):
        """Enhanced capture with face detection and angle guidance"""
        if not self.cap or not self.camera_active:
            messagebox.showwarning("Warning", "Camera is not active!")
            return
        
        try:
            ret, frame = self.cap.read()
            if not ret:
                messagebox.showwarning("Warning", "Could not capture frame!")
                return
            
            # Check for face and liveness
            has_face, face_rect = self.detect_face(frame)
            if not has_face:
                messagebox.showwarning("Warning", "No face detected!")
                return
                
            is_live = self.check_liveness(frame)
            if not is_live:
                messagebox.showwarning("Warning", "Liveness check failed! Please blink naturally.")
                return
            
            # For registration, capture multiple angles
            if len(self.registration_angles) > 0:
                current_angle = self.registration_angles[0]
                self.captured_angles[current_angle] = frame
                self.registration_angles.rotate(-1)
                self.angle_label.config(text=f"Please turn your head slightly to the {self.registration_angles[0]}")
                
                if len(self.captured_angles) >= 3:
                    # Combine all angles for registration
                    self.captured_image = frame  # Use front face as primary
                    _, buffer = cv2.imencode('.jpg', frame)
                    self.captured_base64 = base64.b64encode(buffer).decode('utf-8')
                    self.status_label.config(text="All angles captured successfully!")
                    self.angle_label.config(text="")
                    return
                    
            else:
                # Normal capture for login
                self.captured_image = frame
                _, buffer = cv2.imencode('.jpg', frame)
                self.captured_base64 = base64.b64encode(buffer).decode('utf-8')
                self.status_label.config(text="Image captured successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to capture image: {str(e)}")
    
    def register(self):
        if not self.captured_base64:
            messagebox.showwarning("Warning", "Please capture an image first!")
            return
        
        if not self.username.get():
            messagebox.showwarning("Warning", "Please enter a username!")
            return
        
        try:
            response = register_user(self.username.get(), self.captured_base64)
            if 'error' in response:
                messagebox.showerror("Error", response['error'])
            else:
                messagebox.showinfo("Success", f"Registration successful! Face count: {response['face_count']}")
                self.status_label.config(text="Registration successful!")
        except Exception as e:
            messagebox.showerror("Error", f"Registration failed: {str(e)}")
    
    def start_api_thread(self):
        """Start a thread to handle API calls"""
        def process_api_queue():
            while True:
                try:
                    func, args, callback = self.api_queue.get()
                    result = func(*args)
                    self.root.after(0, callback, result)
                except Exception as e:
                    print(f"API thread error: {str(e)}")
        
        api_thread = threading.Thread(target=process_api_queue, daemon=True)
        api_thread.start()
    
    def login(self):
        """Start face recognition login process"""
        self.preview_frame.grid()
        self.status_label.config(text="Please look at the camera for face recognition")
        self.initialize_camera()
        
    def register_face(self):
        """Handle face registration"""
        if not self.username.get():
            messagebox.showwarning("Warning", "Please enter a username!")
            return
            
        if not self.password.get():
            messagebox.showwarning("Warning", "Please enter a password!")
            return
            
        if not self.captured_base64:
            messagebox.showwarning("Warning", "Please capture your face image!")
            return
            
        try:
            # Add registration request to queue
            self.api_queue.put((
                register_user,
                (self.captured_base64, self.password.get(), self.username.get()),
                self.handle_registration_response
            ))
            self.status_label.config(text="Processing registration...")
            
        except Exception as e:
            self.status_label.config(text=f"Registration error: {str(e)}")
            messagebox.showerror("Error", f"Registration error: {str(e)}")

    def handle_registration_response(self, response):
        """Handle registration response"""
        if 'error' in response:
            self.status_label.config(text=f"Registration failed: {response['error']}")
            messagebox.showerror("Error", response['error'])
        else:
            self.status_label.config(text="Registration successful!")
            messagebox.showinfo("Success", "Registration successful!")
            # Clear form and hide registration frame
            self.username.set("")
            self.password.set("")
            self.captured_base64 = None
            self.registration_frame.grid_remove()
            self.preview_frame.grid_remove()
    
    def traditional_login(self):
        """Fallback traditional login using username and password"""
        username = self.trad_username.get()
        password = self.trad_password.get()

        if not username or not password:
            messagebox.showwarning("Warning", "Please enter both username and password!")
            return

        try:
            response = login_user_traditional(username, password)
            if 'error' in response:
                self.status_label.config(text=f"Traditional Login failed: {response['error']}")
                messagebox.showerror("Error", response['error'])
            else:
                success_message = (
                    f"Login successful!\n"
                    f"Username: {response['username']}"
                )
                self.status_label.config(text=f"Logged in as: {response['username']}")
                messagebox.showinfo("Success", success_message)
        except Exception as e:
            self.status_label.config(text=f"Traditional Login error: {str(e)}")
            messagebox.showerror("Error", f"Traditional Login error: {str(e)}")

    def traditional_login_Frame_show(self):
        """Show the traditional login frame"""
        self.traditional_login_frame.grid()
        self.traditional_login_frame.lift()
    
    def traditional_login_Frame_hide(self):
        """Hide the traditional login frame"""
        self.traditional_login_frame.grid_remove()
    
    def __del__(self):
        """Cleanup on exit"""
        if self.cap:
            self.cap.release()

        # Ensure traditional login frame is hidden on exit
        self.traditional_login_Frame_hide()
    
    def detect_face(self, frame):
        """Detect face in frame and return face rectangle"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        return len(faces) > 0, faces[0] if len(faces) > 0 else None
    
    def check_liveness(self, frame):
        """Basic liveness detection using eye blink detection"""
        # This is a simplified version. In production, you'd want more sophisticated liveness detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        for (x, y, w, h) in faces:
            roi_gray = gray[y:y+h, x:x+w]
            eyes = eye_cascade.detectMultiScale(roi_gray)
            return len(eyes) >= 2
        return False
    
    def login_face(self):
        """Login with face image"""
        try:
            login_image_base64, _ = capture_image()  # Capture image
            ...
        except Exception as e:
            print(f"Login error: {str(e)}")  # Debugging line
            self.status_label.config(text=f"Login error: {str(e)}")
            messagebox.showerror("Error", f"Login error: {str(e)}")
    
    def show_registration_form(self):
        """Show registration form and camera preview"""
        self.registration_frame.grid()
        self.preview_frame.grid()
        self.status_label.config(text="Please enter your details and capture your face")
        self.initialize_camera()
    
    def renderAuthUI(self):
        # Replace JSX with Tkinter widgets
        login_face_button = ttk.Button(self.root, text="Login with Face", command=self.login_face)
        login_face_button.grid(row=7, column=0, columnspan=2, pady=5)

if __name__ == "__main__":
    root = tk.Tk()
    app = FaceAuthApp(root)
    root.mainloop()