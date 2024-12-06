from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
import jwt
from datetime import datetime, timedelta

from .database import get_db_session, init_db, check_database_connection, get_database_stats
from .models import (
    UserCreate, UserUpdate, UserResponse,
    SessionCreate, SessionResponse,
    CommandCreate, CommandResponse,
    UserSettingsUpdate, UserSettingsResponse,
    ServerLogCreate, ServerLogResponse
)
from .crud import (
    create_user, get_user, get_users, update_user, delete_user,
    create_session, get_session, get_active_sessions, invalidate_session,
    create_command, get_command, get_user_commands, update_command_status,
    get_user_settings, update_user_settings,
    verify_password, create_access_token,
    create_server_log, get_server_logs
)

app = FastAPI(title="Database Server")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Initialize database
@app.on_event("startup")
async def startup_event():
    init_db()

# Authentication
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db_session)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.JWTError:
        raise credentials_exception
        
    user = get_user(db, user_id)
    if user is None:
        raise credentials_exception
    return user

# User endpoints
@app.post("/users/", response_model=UserResponse)
async def create_new_user(user: UserCreate, db: Session = Depends(get_db_session)):
    return create_user(db, user)

@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user = Depends(get_current_user)):
    return current_user

@app.get("/users/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    db_user = get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user_info(
    user_id: int,
    user_update: UserUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this user")
    
    updated_user = update_user(db, user_id, user_update)
    if updated_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

@app.delete("/users/{user_id}")
async def delete_user_account(
    user_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this user")
    
    if delete_user(db, user_id):
        return {"message": "User deleted successfully"}
    raise HTTPException(status_code=404, detail="User not found")

# Session endpoints
@app.post("/sessions/", response_model=SessionResponse)
async def create_new_session(
    session: SessionCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    return create_session(db, current_user.id, session)

@app.get("/sessions/active", response_model=List[SessionResponse])
async def read_active_sessions(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    return get_active_sessions(db, current_user.id)

@app.delete("/sessions/{session_id}")
async def end_session(
    session_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    session = get_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if invalidate_session(db, session_id):
        return {"message": "Session ended successfully"}
    raise HTTPException(status_code=404, detail="Session not found")

# Command endpoints
@app.post("/commands/", response_model=CommandResponse)
async def create_new_command(
    command: CommandCreate,
    session_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    session = get_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return create_command(db, current_user.id, session_id, command)

@app.get("/commands/{command_id}", response_model=CommandResponse)
async def read_command(
    command_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    command = get_command(db, command_id)
    if not command or command.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Command not found")
    return command

@app.get("/commands/", response_model=List[CommandResponse])
async def read_user_commands(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    return get_user_commands(db, current_user.id, skip=skip, limit=limit)

@app.put("/commands/{command_id}/status", response_model=CommandResponse)
async def update_command(
    command_id: int,
    status: str,
    result: Optional[dict] = None,
    error_message: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    command = get_command(db, command_id)
    if not command or command.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Command not found")
    
    updated_command = update_command_status(db, command_id, status, result, error_message)
    if updated_command is None:
        raise HTTPException(status_code=404, detail="Command not found")
    return updated_command

# User Settings endpoints
@app.get("/users/{user_id}/settings", response_model=UserSettingsResponse)
async def read_user_settings(
    user_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to read these settings")
    
    settings = get_user_settings(db, user_id)
    if settings is None:
        raise HTTPException(status_code=404, detail="Settings not found")
    return settings

@app.put("/users/{user_id}/settings", response_model=UserSettingsResponse)
async def update_settings(
    user_id: int,
    settings_update: UserSettingsUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update these settings")
    
    updated_settings = update_user_settings(db, user_id, settings_update)
    if updated_settings is None:
        raise HTTPException(status_code=404, detail="Settings not found")
    return updated_settings

# Health check and stats endpoints
@app.get("/health")
async def health_check():
    try:
        is_healthy = await check_database_connection()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }

@app.get("/stats")
async def database_stats(current_user = Depends(get_current_user)):
    try:
        stats = get_database_stats()
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get database stats: {str(e)}"
        )

# Add these new endpoints
@app.post("/logs/", response_model=ServerLogResponse)
async def create_log(
    log: ServerLogCreate,
    db: Session = Depends(get_db_session)
):
    return create_server_log(db, log)

@app.get("/logs/", response_model=List[ServerLogResponse])
async def read_logs(
    server_name: Optional[str] = None,
    log_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_session)
):
    return get_server_logs(db, server_name, log_type, skip, limit) 