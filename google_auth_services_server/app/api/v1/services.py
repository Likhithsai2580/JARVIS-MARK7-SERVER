from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from app.services.google_services import (
    GoogleCalendarService,
    GoogleGmailService,
    GoogleMessagesService
)
from app.core.security import get_current_user
from pydantic import BaseModel

router = APIRouter()

# Calendar Models
class EventCreate(BaseModel):
    summary: str
    description: Optional[str] = None
    start: Dict[str, Any]
    end: Dict[str, Any]
    attendees: Optional[List[Dict[str, str]]] = None

# Gmail Models
class EmailSend(BaseModel):
    to: str
    subject: str
    body: str
    html: Optional[str] = None

# Messages Models
class MessageSend(BaseModel):
    phone_number: str
    message: str

# Calendar Endpoints
@router.get("/calendar/events")
async def list_calendar_events(
    max_results: int = 10,
    credentials = Depends(get_current_user)
):
    calendar_service = GoogleCalendarService(credentials)
    return await calendar_service.list_events(max_results=max_results)

@router.post("/calendar/events")
async def create_calendar_event(
    event: EventCreate,
    credentials = Depends(get_current_user)
):
    calendar_service = GoogleCalendarService(credentials)
    return await calendar_service.create_event(event.dict())

# Gmail Endpoints
@router.get("/gmail/messages")
async def list_gmail_messages(
    max_results: int = 10,
    query: Optional[str] = None,
    credentials = Depends(get_current_user)
):
    gmail_service = GoogleGmailService(credentials)
    return await gmail_service.list_messages(max_results=max_results, query=query)

@router.post("/gmail/send")
async def send_email(
    email: EmailSend,
    credentials = Depends(get_current_user)
):
    gmail_service = GoogleGmailService(credentials)
    return await gmail_service.send_email(
        to=email.to,
        subject=email.subject,
        body=email.body,
        html=email.html
    )

# Messages Endpoints
@router.get("/messages")
async def list_messages(
    max_results: int = 10,
    credentials = Depends(get_current_user)
):
    messages_service = GoogleMessagesService(credentials)
    return await messages_service.list_messages(max_results=max_results)

@router.post("/messages/send")
async def send_message(
    message: MessageSend,
    credentials = Depends(get_current_user)
):
    messages_service = GoogleMessagesService(credentials)
    return await messages_service.send_message(
        phone_number=message.phone_number,
        message=message.message
    ) 