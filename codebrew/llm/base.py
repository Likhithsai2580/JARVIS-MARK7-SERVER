from abc import ABC, abstractmethod
from typing import Optional, Union, List, Dict, Any, Tuple, Callable, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv
from pythonjsonlogger import jsonlogger

import logging
import os

load_dotenv()

class Role(Enum):
    system = "system"
    user = "user"
    assistant = "assistant"

class ModelType(Enum):
    textonly = "textonly"
    textandimage = "textandimage"
    textandfile = "textandfile"

@dataclass
class FileContent:
    """File content for file-based models"""
    content: str
    filename: str
    mime_type: str

@dataclass
class Model:
    name: str
    typeof: ModelType
    supported_files: Optional[List[str]] = None  # List of supported file extensions
    max_file_size: Optional[int] = None  # Maximum file size in bytes
    
    def __post_init__(self):
        if self.typeof == ModelType.textandfile and not self.supported_files:
            self.supported_files = [".txt", ".py", ".js", ".json", ".md", ".csv"]
        if self.typeof == ModelType.textandfile and not self.max_file_size:
            self.max_file_size = 10 * 1024 * 1024  # 10MB default

class LLM(ABC):
    def __init__(
        self,
        model: Model,
        apiKey: str,
        messages: Optional[List[Dict[str, Union[str, List[Dict[str, Any]]]]]] = None,
        temperature: float = 0.0,
        systemPrompt: Optional[str] = None,
        maxTokens: int = 2048,
        logFile: Optional[str] = None,
    ) -> None:
        messages = messages if messages is not None else []
        self.apiKey = apiKey
        self.messages = messages
        self.temperature = temperature
        self.systemPrompt = systemPrompt
        self.maxTokens = maxTokens
        self.model = model

        # logger setup
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)  # Set default log level
        
        # Create a JSON formatter
        json_formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(message)s %(name)s %(funcName)s')
        
        # Check if logFile is None, in that case use console logging (pseudo-logging)
        if logFile is None:
            # Pseudo-logging with RichHandler (for console output)
            from rich.logging import RichHandler
            rich_handler = RichHandler()
            self.logger.addHandler(rich_handler)
        else:
            # If logFile is provided, log to a file in JSON format            
            LOG_FILE = logFile
            file_handler = logging.FileHandler(LOG_FILE)
            file_handler.setFormatter(json_formatter)
            self.logger.addHandler(file_handler)
            

        # Handle case where `model` is passed as a string
        if type(model) is str:
            self.logger.error("Model name must be a Model object. Fixed temporarily.")
            self.model = Model(model, ModelType.textandimage)
            model = self.model
        
        self.logger.info(
            {   
                "message": "Initializing LLM",
                "model": model.name,
                "modelType": model.typeof.value,
                "temperature": temperature
            }
        )

        # Set the appropriate message handler based on the model type
        self.addMessage = self.addMessageTextOnly if model.typeof == ModelType.textonly else self.addMessageVision
        
        if systemPrompt:
            self.addMessage(Role.system, systemPrompt)

        
    @abstractmethod
    async def streamRun(self, prompt: str, save: bool = True) -> AsyncGenerator[str, None]:
        """Async generator for streaming responses."""
        raise NotImplementedError
        
    @abstractmethod
    async def run(self, prompt: str, save: bool = True) -> str:
        """Async method for getting responses."""
        raise NotImplementedError
        
    @abstractmethod
    async def constructClient(self) -> Any:
        """Async method for constructing client."""
        raise NotImplementedError
        
    @abstractmethod
    async def testClient(self) -> bool:
        """Async method for testing client connection."""
        raise NotImplementedError

    
    def addMessage(self, role: Role, content: str, imageUrl: Optional[str] = None) -> None:
        """Add a message to the conversation history based on model type."""
        if type(role) is str:
            role = Role[role]
            
        if self.model.typeof == ModelType.textonly:
            self.addMessageTextOnly(role, content, imageUrl)
        else:
            self.addMessageVision(role, content, imageUrl)
            
        self.logger.info({
            "message": "Added message to history",
            "role": role.value,
            "contentLength": len(content),
            "hasImage": imageUrl is not None
        })

    def addMessageVision(self, role: Role, content: str, imageUrl: Optional[str] = None) -> None:
        
        if imageUrl is None:
            return self.addMessageTextOnly(role, content, imageUrl)
        if type(role) is str:
            role = Role[role]

        message: Dict[str, list] = {"role": role.value, "content": []}

        if content:
            message["content"].append(
                {
                    "type": "text",
                    "text": content
                }
            )

        if imageUrl:
            message["content"].append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": imageUrl
                    }
                }
            )

        self.messages.append(message)

    def addMessageTextOnly(self, role: Role, content: str, imageUrl: Optional[str] = None) -> None:
        if type(role) is str:
            role = Role[role]

        if imageUrl is not None:
            self.logger.error("Image URL is not supported for text-only model. Ignoring the image URL.")
            
        self.messages.append({
            "role": role.value,
            "content": content
        })

    def addMessageWithFile(self, role: Role, content: str, file: FileContent) -> None:
        """Add a message with file content."""
        if self.model.typeof != ModelType.textandfile:
            self.logger.error("File content is not supported for this model type")
            return self.addMessageTextOnly(role, content)
            
        if not self.model.supported_files:
            self.logger.error("No supported file types defined for this model")
            return self.addMessageTextOnly(role, content)
            
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in self.model.supported_files:
            self.logger.error(f"File type {file_ext} not supported")
            return self.addMessageTextOnly(role, content)
            
        if len(file.content.encode()) > self.model.max_file_size:
            self.logger.error(f"File size exceeds maximum allowed size of {self.model.max_file_size} bytes")
            return self.addMessageTextOnly(role, content)
            
        message: Dict[str, list] = {"role": role.value, "content": []}
        
        if content:
            message["content"].append({
                "type": "text",
                "text": content
            })
            
        message["content"].append({
            "type": "file",
            "file": {
                "content": file.content,
                "filename": file.filename,
                "mime_type": file.mime_type
            }
        })
        
        self.messages.append(message)
        self.logger.info({
            "message": "Added message with file to history",
            "role": role.value,
            "contentLength": len(content),
            "fileName": file.filename,
            "fileSize": len(file.content.encode())
        })
        
    
    def getMessage(self, role: Role, content: str, imageUrl: Optional[str] = None) -> List[Dict[str, str]]:        
        if type(role) is str:
            role = Role[role]

        if imageUrl is not None:
            message: Dict[str, list] = {"role": role.value, "content": []}

            if content:
                message["content"].append(
                    {
                        "type": "text",
                        "text": content
                    }
                )

            if imageUrl:
                message["content"].append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": imageUrl
                        }
                    }
                )
            return message
        else:
            return {
                "role": role.value,
                "content": content
            }
        
    
    def log(self, **kwargs) -> None:
        self.logger.info(kwargs)


if __name__ == "__main__":
    print(Role.system.value)
