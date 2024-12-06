from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import jwt
from typing import Optional, List, Dict, Any
from passlib.context import CryptContext
import uuid

from .models import User, Session as DBSession, Command, UserSettings, ServerLog
from .models import UserCreate, UserUpdate, SessionCreate, CommandCreate, UserSettingsUpdate, ServerLogCreate

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = "your-secret-key"  # Move to environment variables
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# User CRUD operations
def create_user(db: Session, user: UserCreate) -> User:
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Create default user settings
        create_user_settings(db, db_user.id)
        return db_user
    except IntegrityError:
        db.rollback()
        raise ValueError("Username or email already exists")

def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()

def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None
        
    update_data = user_update.dict(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
    for key, value in update_data.items():
        setattr(db_user, key, value)
        
    try:
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        raise ValueError("Username or email already exists")

def delete_user(db: Session, user_id: int) -> bool:
    db_user = get_user(db, user_id)
    if not db_user:
        return False
    
    db_user.is_active = False
    db.commit()
    return True

# Session CRUD operations
def create_session(db: Session, user_id: int, session_create: SessionCreate) -> DBSession:
    session_token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    db_session = DBSession(
        user_id=user_id,
        session_token=session_token,
        device_info=session_create.device_info,
        expires_at=expires_at
    )
    
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def get_session(db: Session, session_id: int) -> Optional[DBSession]:
    return db.query(DBSession).filter(DBSession.id == session_id).first()

def get_active_sessions(db: Session, user_id: int) -> List[DBSession]:
    return db.query(DBSession).filter(
        DBSession.user_id == user_id,
        DBSession.is_active == True,
        DBSession.expires_at > datetime.utcnow()
    ).all()

def invalidate_session(db: Session, session_id: int) -> bool:
    db_session = get_session(db, session_id)
    if not db_session:
        return False
    
    db_session.is_active = False
    db.commit()
    return True

# Command CRUD operations
def create_command(db: Session, user_id: int, session_id: int, command: CommandCreate) -> Command:
    db_command = Command(
        user_id=user_id,
        session_id=session_id,
        command_type=command.command_type,
        command_data=command.command_data,
        status="pending"
    )
    
    db.add(db_command)
    db.commit()
    db.refresh(db_command)
    return db_command

def get_command(db: Session, command_id: int) -> Optional[Command]:
    return db.query(Command).filter(Command.id == command_id).first()

def get_user_commands(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Command]:
    return db.query(Command).filter(Command.user_id == user_id).offset(skip).limit(limit).all()

def update_command_status(
    db: Session,
    command_id: int,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> Optional[Command]:
    db_command = get_command(db, command_id)
    if not db_command:
        return None
    
    db_command.status = status
    db_command.completed_at = datetime.utcnow()
    if result:
        db_command.result = result
    if error_message:
        db_command.error_message = error_message
    
    db.commit()
    db.refresh(db_command)
    return db_command

# UserSettings CRUD operations
def create_user_settings(db: Session, user_id: int) -> UserSettings:
    db_settings = UserSettings(
        user_id=user_id,
        preferences={},
        notifications_enabled=True,
        theme="light",
        language="en"
    )
    
    db.add(db_settings)
    db.commit()
    db.refresh(db_settings)
    return db_settings

def get_user_settings(db: Session, user_id: int) -> Optional[UserSettings]:
    return db.query(UserSettings).filter(UserSettings.user_id == user_id).first()

def update_user_settings(
    db: Session,
    user_id: int,
    settings_update: UserSettingsUpdate
) -> Optional[UserSettings]:
    db_settings = get_user_settings(db, user_id)
    if not db_settings:
        return None
        
    update_data = settings_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        if key == "preferences" and value:
            db_settings.preferences.update(value)
        else:
            setattr(db_settings, key, value)
    
    db.commit()
    db.refresh(db_settings)
    return db_settings

# ServerLog CRUD operations
def create_server_log(db: Session, log: ServerLogCreate) -> ServerLog:
    db_log = ServerLog(
        server_name=log.server_name,
        log_type=log.log_type,
        message=log.message,
        details=log.details
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

def get_server_logs(
    db: Session,
    server_name: Optional[str] = None,
    log_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[ServerLog]:
    query = db.query(ServerLog)
    if server_name:
        query = query.filter(ServerLog.server_name == server_name)
    if log_type:
        query = query.filter(ServerLog.log_type == log_type)
    return query.order_by(ServerLog.timestamp.desc()).offset(skip).limit(limit).all() 