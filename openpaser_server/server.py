from .server_template import BaseServer
from fastapi import HTTPException, File, UploadFile
from pydantic import BaseModel
from typing import Optional, Dict, List, Any, Tuple
import asyncio
import json
import aiofiles
import os
from datetime import datetime
from gradio_client import Client, handle_file

class ProcessRequest(BaseModel):
    image_url: str
    box_threshold: float = 0.05
    iou_threshold: float = 0.1

class OmniParserServer(BaseServer):
    def __init__(self):
        super().__init__("OmniParser")
        self.client = Client("microsoft/OmniParser")
        
        @self.app.post("/process")
        async def process_image(request: ProcessRequest) -> Dict:
            self.set_busy(True)
            try:
                await self.logger.log(
                    message="Processing image parse request",
                    log_type="info",
                    details={
                        "image_url": request.image_url,
                        "box_threshold": request.box_threshold,
                        "iou_threshold": request.iou_threshold
                    }
                )
                
                result = await self.process_image_request(request)
                return {
                    "status": "success",
                    "image_output": result[0],
                    "parsed_elements": result[1],
                    "coordinates": result[2]
                }
                
            except Exception as e:
                await self.logger.log(
                    message=f"Image parse error: {str(e)}",
                    log_type="error"
                )
                raise HTTPException(status_code=500, detail=str(e))
            finally:
                self.set_busy(False)
                
        @self.app.post("/process/file")
        async def process_file(
            file: UploadFile = File(...),
            box_threshold: float = 0.05,
            iou_threshold: float = 0.1
        ):
            self.set_busy(True)
            try:
                # Save file temporarily
                temp_path = f"temp_{datetime.now().timestamp()}"
                async with aiofiles.open(temp_path, 'wb') as out_file:
                    content = await file.read()
                    await out_file.write(content)
                
                request = ProcessRequest(
                    image_url=temp_path,
                    box_threshold=box_threshold,
                    iou_threshold=iou_threshold
                )
                
                result = await self.process_image_request(request)
                
                # Cleanup
                os.remove(temp_path)
                
                return {
                    "status": "success", 
                    "image_output": result[0],
                    "parsed_elements": result[1],
                    "coordinates": result[2]
                }
                
            finally:
                self.set_busy(False)
    
    async def process_image_request(self, request: ProcessRequest) -> Tuple:
        """Process image parsing request using OmniParser"""
        try:
            result = self.client.predict(
                image_input=handle_file(request.image_url),
                box_threshold=request.box_threshold,
                iou_threshold=request.iou_threshold,
                api_name="/process"
            )
            return result
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    server = OmniParserServer()
    server.run()