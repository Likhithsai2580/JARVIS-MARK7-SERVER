try:
    from llm.base import LLM, Model, ModelType, Role
except ImportError:
    import os
    import sys
    
    sys.path.append(os.path.dirname(__file__))
    from base import LLM, Model, ModelType, Role

from typing import Optional, List, Dict, Generator
import requests
from dotenv import load_dotenv
from rich import print

load_dotenv()

# Define available models
GPT35_TURBO = Model(name="gpt-3.5-turbo", typeof=ModelType.textonly)

class LLMServer(LLM):
    def __init__(
        self,
        model: Model,
        server_url: str = "http://localhost:8000",
        apiKey: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        systemPrompt: Optional[str] = None,
        maxTokens: int = 2048,
        logFile: Optional[str] = None,
        extra: Dict[str, str] = {},
    ):
        messages = messages if messages is not None else []
        super().__init__(model, apiKey, messages, temperature, systemPrompt, maxTokens, logFile)
        
        self.server_url = server_url.rstrip('/')
        self.extra = extra

    def constructClient(self):
        # No client needed for REST API
        return None

    def testClient(self) -> bool:
        try:
            response = requests.get(f"{self.server_url}/health")
            response.raise_for_status()
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to LLM server: {str(e)}")
            return False

    def run(self, prompt: str = "", imageUrl: Optional[str] = None, save: bool = True) -> str:
        toSend = []
        if save and prompt:
            self.addMessage(Role.user, prompt, imageUrl)
        elif not save and prompt:
            toSend.append(self.getMessage(Role.user, prompt, imageUrl))

        try:
            response = requests.post(
                f"{self.server_url}/chat/completions",
                json={"messages": self.messages + toSend}
            )
            response.raise_for_status()
            result = response.json()
            
            if save:
                self.addMessage(Role.assistant, result["response"])
            
            return result["response"]

        except Exception as e:
            self.logger.error(f"LLM server error: {str(e)}")
            return f"Error: {str(e)}"

    def streamRun(self, prompt: str = "", imageUrl: Optional[str] = None, save: bool = True) -> Generator[str, None, None]:
        # For now, just use non-streaming version since LLM server doesn't support streaming yet
        response = self.run(prompt, imageUrl, save)
        yield response 