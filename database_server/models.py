from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sessions = relationship("Session", back_populates="user")
    commands = relationship("Command", back_populates="user")
    settings = relationship("UserSettings", back_populates="user", uselist=False)

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_token = Column(String(200), unique=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    last_activity = Column(DateTime, default=datetime.utcnow)
    device_info = Column(JSON)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    commands = relationship("Command", back_populates="session")

class Command(Base):
    __tablename__ = "commands"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(Integer, ForeignKey("sessions.id"))
    command_type = Column(String(50))
    command_data = Column(JSON)
    status = Column(String(20))  # pending, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    result = Column(JSON)
    
    # Relationships
    user = relationship("User", back_populates="commands")
    session = relationship("Session", back_populates="commands")

class UserSettings(Base):
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    preferences = Column(JSON)
    notifications_enabled = Column(Boolean, default=True)
    theme = Column(String(20), default="light")
    language = Column(String(10), default="en")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="settings")

# Pydantic models for API
class UserBase(BaseModel):
    username: str
    email: str
    
class UserCreate(UserBase):
    password: str
    
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class SessionCreate(BaseModel):
    device_info: Dict[str, Any]
    
class SessionResponse(BaseModel):
    id: int
    session_token: str
    is_active: bool
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    device_info: Dict[str, Any]
    
    class Config:
        orm_mode = True

class CommandCreate(BaseModel):
    command_type: str
    command_data: Dict[str, Any]
    
class CommandResponse(BaseModel):
    id: int
    command_type: str
    command_data: Dict[str, Any]
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    result: Optional[Dict[str, Any]]
    
    class Config:
        orm_mode = True

class UserSettingsUpdate(BaseModel):
    preferences: Optional[Dict[str, Any]] = None
    notifications_enabled: Optional[bool] = None
    theme: Optional[str] = None
    language: Optional[str] = None
    
class UserSettingsResponse(BaseModel):
    id: int
    preferences: Dict[str, Any]
    notifications_enabled: bool
    theme: str
    language: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

# Add this new model class
class ServerLog(Base):
    __tablename__ = "server_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    server_name = Column(String(50))
    log_type = Column(String(20))  # info, warning, error, debug
    message = Column(Text)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
class ServerLogCreate(BaseModel):
    server_name: str
    log_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    
class ServerLogResponse(BaseModel):
    id: int
    server_name: str
    log_type: str
    message: str
    details: Optional[Dict[str, Any]]
    timestamp: datetime
    
    class Config:
        orm_mode = True 