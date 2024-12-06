try:
    from llm.base import LLM, Model, ModelType, Role
except ImportError:
    import os
    import sys
    
    sys.path.append(os.path.dirname(__file__))
    from base import LLM, Model, ModelType, Role

from typing import Optional, List, Dict, Generator
from dotenv import load_dotenv
from rich import print
from copy import deepcopy

import os
import ollama

load_dotenv()

LLAMA_3_1 = Model(name="llama3.1", typeof=ModelType.textonly)
LLAMA_2 = Model(name="llama2", typeof=ModelType.textonly)
MISTRAL = Model(name="mistral", typeof=ModelType.textonly)
CODELLAMA = Model(name="codellama", typeof=ModelType.textonly)

class Ollama(LLM):
    def __init__(
        self,
        model: Model,
        apiKey: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.0,
        systemPrompt: Optional[str] = None,
        maxTokens: int = 2048,
        cheatCode: Optional[str] = None,
        logFile: Optional[str] = None,
        extra: Dict[str, str] = {},
    ):
        messages = messages if messages is not None else []
        super().__init__(model, apiKey, messages, temperature, systemPrompt, maxTokens, logFile)
        
        self.extra = extra
        self.cheatCode = cheatCode
        self.client = self.constructClient()
        
        if cheatCode is None:
            p = self.testClient()
            if p:
                self.logger.info("Test successful for Ollama. Model found.")
        else:
            self.logger.info("Cheat code provided. Model found.")

    def constructClient(self):
        try:
            return ollama
        except Exception as e:
            print(e)
            self.logger.error(e)

    def testClient(self) -> bool:
        try:
            models = self.client.list()
            for model in models['models']:
                if model['name'] == self.model.name:
                    break
            else:
                self.logger.error("Model not found")
                raise Exception("Model not found in Ollama, please pull it first using 'ollama pull model_name'")
            return True
        except Exception as e:
            print(e)
            self.logger.error(e)
            return False

    def streamRun(self, prompt: str = "", imageUrl: Optional[str] = None, save: bool = True) -> Generator[str, None, None]:
        toSend = []
        if save and prompt:
            self.addMessage(Role.user, prompt, imageUrl)
        elif not save and prompt:
            toSend.append(self.getMessage(Role.user, prompt, imageUrl))

        try:
            stream = self.client.chat(
                model=self.model.name,
                messages=self.messages + toSend,
                stream=True,
                **self.extra
            )
        except Exception as e:
            self.logger.error(e)
            return "Please check log file some error occurred."

        final_response = ""
        for chunk in stream:
            if chunk['message']['content'] is not None:
                final_response += chunk['message']['content']
                yield chunk['message']['content']

        if save:
            self.addMessage(Role.assistant, final_response)

    def run(self, prompt: str = "", imageUrl: Optional[str] = None, save: bool = True) -> str:
        toSend = []
        if save and prompt:
            self.addMessage(Role.user, prompt, imageUrl)
        elif not save and prompt:
            toSend.append(self.getMessage(Role.user, prompt, imageUrl))

        try:
            response = self.client.chat(
                model=self.model.name,
                messages=self.messages + toSend,
                **self.extra
            )
        except Exception as e:
            self.logger.error(e)
            return "Please check log file some error occurred."

        log_response = deepcopy(response)
        log_response['message']['content'] = log_response['message']['content'][:20]
        self.logger.info(log_response)

        if save:
            self.addMessage(Role.assistant, response['message']['content'])

        return response['message']['content']

if __name__ == "__main__":
    llm = Ollama(LLAMA_3_1, logFile="ollama.log")
    print(llm.run("What is the meaning of life?"))
