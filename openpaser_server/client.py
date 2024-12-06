import httpx
import asyncio
from typing import Dict, List, Any
import json
import base64
from PIL import Image
import io

class OmniParserClient:
    def __init__(self, omniparser_url: str = "http://localhost:8001", 
                 llm_url: str = "http://localhost:8000"):
        self.omniparser_url = omniparser_url
        self.llm_url = llm_url
        
    async def parse_image(self, image_path: str) -> Dict[str, Any]:
        """Parse an image using OmniParser server"""
        async with httpx.AsyncClient() as client:
            with open(image_path, "rb") as f:
                files = {"file": f}
                response = await client.post(f"{self.omniparser_url}/parse", 
                                          files=files)
                return response.json()

    async def get_llm_completion(self, messages: List[Dict[str, str]]) -> str:
        """Get completion from LLM server"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.llm_url}/chat/completions",
                json={"messages": messages}
            )
            return response.json()["response"]

    async def analyze_ui_elements(self, image_path: str, task_description: str) -> str:
        """
        Analyze UI elements in an image and get LLM guidance for the specified task
        """
        # First parse the image
        parse_results = await self.parse_image(image_path)
        
        if parse_results["status"] != "success":
            raise Exception(f"Failed to parse image: {parse_results['message']}")
            
        # Prepare context for LLM
        elements_description = json.dumps(parse_results["data"], indent=2)
        
        # Create prompt for LLM
        messages = [
            {"role": "system", "content": """You are an AI assistant that helps users 
             interact with UI elements. Given the coordinates and types of UI elements, 
             help users accomplish their tasks."""},
            {"role": "user", "content": f"""
            I have a UI with the following elements:
            {elements_description}
            
            Task to accomplish: {task_description}
            
            Please provide step-by-step guidance on how to accomplish this task using 
            the detected UI elements. Include specific coordinates when relevant."""}
        ]
        
        # Get LLM completion
        return await self.get_llm_completion(messages)

async def main():
    # Example usage
    client = OmniParserClient()
    
    # Example task
    image_path = "path/to/your/screenshot.png"
    task = "I want to click the login button"
    
    try:
        guidance = await client.analyze_ui_elements(image_path, task)
        print("AI Assistant's Guidance:")
        print(guidance)
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 