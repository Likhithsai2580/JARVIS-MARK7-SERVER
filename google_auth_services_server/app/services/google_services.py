from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class GoogleCalendarService:
    def __init__(self, credentials: Credentials):
        self.service = build('calendar', 'v3', credentials=credentials)

    async def list_events(self, calendar_id: str = 'primary', 
                         max_results: int = 10) -> List[Dict[str, Any]]:
        """List upcoming calendar events"""
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = self.service.events().list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])

    async def create_event(self, event_data: Dict[str, Any], 
                          calendar_id: str = 'primary') -> Dict[str, Any]:
        """Create a new calendar event"""
        event = self.service.events().insert(
            calendarId=calendar_id,
            body=event_data
        ).execute()
        return event

    async def update_event(self, event_id: str, event_data: Dict[str, Any], 
                          calendar_id: str = 'primary') -> Dict[str, Any]:
        """Update an existing calendar event"""
        event = self.service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event_data
        ).execute()
        return event

    async def delete_event(self, event_id: str, 
                          calendar_id: str = 'primary') -> None:
        """Delete a calendar event"""
        self.service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()

class GoogleGmailService:
    def __init__(self, credentials: Credentials):
        self.service = build('gmail', 'v1', credentials=credentials)

    async def list_messages(self, max_results: int = 10, 
                           query: str = None) -> List[Dict[str, Any]]:
        """List Gmail messages"""
        try:
            messages = []
            request = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query
            )
            response = request.execute()
            
            if 'messages' in response:
                for msg in response['messages']:
                    message = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    messages.append(message)
                    
            return messages
        except Exception as e:
            raise Exception(f"Failed to list messages: {str(e)}")

    async def send_email(self, to: str, subject: str, body: str, 
                        html: Optional[str] = None) -> Dict[str, Any]:
        """Send an email"""
        try:
            message = MIMEMultipart('alternative')
            message['to'] = to
            message['subject'] = subject

            # Add plain text version
            message.attach(MIMEText(body, 'plain'))

            # Add HTML version if provided
            if html:
                message.attach(MIMEText(html, 'html'))

            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')

            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return sent_message
        except Exception as e:
            raise Exception(f"Failed to send email: {str(e)}")

    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """Get a specific message"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            return message
        except Exception as e:
            raise Exception(f"Failed to get message: {str(e)}")

class GoogleMessagesService:
    def __init__(self, credentials: Credentials):
        self.service = build('messages', 'v1', credentials=credentials)

    async def list_messages(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """List messages from Google Messages"""
        try:
            messages = self.service.messages().list(
                maxResults=max_results
            ).execute()
            return messages.get('messages', [])
        except Exception as e:
            raise Exception(f"Failed to list messages: {str(e)}")

    async def send_message(self, phone_number: str, 
                          message: str) -> Dict[str, Any]:
        """Send a message using Google Messages"""
        try:
            result = self.service.messages().send(
                body={
                    'phoneNumber': phone_number,
                    'text': message
                }
            ).execute()
            return result
        except Exception as e:
            raise Exception(f"Failed to send message: {str(e)}") 