from .server_template import BaseServer
from fastapi import HTTPException, File, UploadFile
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import asyncio
import json
import aiofiles
import os
from datetime import datetime

class ParseRequest(BaseModel):
    content: str
    parser_type: str
    options: Optional[Dict[str, Any]] = None

class BatchParseRequest(BaseModel):
    items: List[ParseRequest]
    parallel: Optional[bool] = True

class OpenParserServer(BaseServer):
    def __init__(self):
        super().__init__("OpenParser")
        self.supported_parsers = ["json", "xml", "yaml", "csv", "markdown"]
        
        @self.app.post("/parse")
        async def parse_content(request: ParseRequest):
            self.set_busy(True)
            try:
                await self.logger.log(
                    message=f"Processing parse request",
                    log_type="info",
                    details={
                        "parser_type": request.parser_type,
                        "content_length": len(request.content)
                    }
                )
                response = await self.process_parse_request(request)
                return response
            except Exception as e:
                await self.logger.log(
                    message=f"Parse error: {str(e)}",
                    log_type="error",
                    details={"parser_type": request.parser_type}
                )
                raise
            finally:
                self.set_busy(False)
        
        @self.app.post("/batch")
        async def batch_parse(request: BatchParseRequest):
            self.set_busy(True)
            try:
                if request.parallel:
                    tasks = [
                        self.process_parse_request(item)
                        for item in request.items
                    ]
                    results = await asyncio.gather(*tasks)
                else:
                    results = []
                    for item in request.items:
                        result = await self.process_parse_request(item)
                        results.append(result)
                return {"results": results}
            finally:
                self.set_busy(False)
        
        @self.app.post("/parse/file")
        async def parse_file(
            file: UploadFile = File(...),
            parser_type: Optional[str] = None
        ):
            self.set_busy(True)
            try:
                # Save file temporarily
                temp_path = f"temp_{datetime.now().timestamp()}"
                async with aiofiles.open(temp_path, 'wb') as out_file:
                    content = await file.read()
                    await out_file.write(content)
                
                # Detect parser type if not specified
                if not parser_type:
                    parser_type = self.detect_parser_type(file.filename)
                
                # Parse file content
                request = ParseRequest(
                    content=content.decode(),
                    parser_type=parser_type
                )
                response = await self.process_parse_request(request)
                
                # Cleanup
                os.remove(temp_path)
                return response
            finally:
                self.set_busy(False)
        
        @self.app.get("/parsers")
        async def list_parsers():
            """List available parsers"""
            return {
                "parsers": self.supported_parsers,
                "count": len(self.supported_parsers)
            }
    
    def detect_parser_type(self, filename: str) -> str:
        """Detect parser type from filename"""
        ext = filename.lower().split('.')[-1]
        parser_map = {
            'json': 'json',
            'xml': 'xml',
            'yaml': 'yaml',
            'yml': 'yaml',
            'csv': 'csv',
            'md': 'markdown'
        }
        return parser_map.get(ext, 'text')
    
    async def process_parse_request(self, request: ParseRequest) -> Dict:
        """Process parsing request"""
        try:
            if request.parser_type not in self.supported_parsers:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported parser type: {request.parser_type}"
                )
            
            # Simulate parsing with different parsers
            await asyncio.sleep(0.5)  # Simulate processing
            
            if request.parser_type == "json":
                result = json.loads(request.content)
            elif request.parser_type == "xml":
                # Add XML parsing logic
                result = {"xml": "parsed"}
            elif request.parser_type == "yaml":
                # Add YAML parsing logic
                result = {"yaml": "parsed"}
            elif request.parser_type == "csv":
                # Add CSV parsing logic
                result = {"csv": "parsed"}
            elif request.parser_type == "markdown":
                # Add Markdown parsing logic
                result = {"markdown": "parsed"}
            else:
                result = {"text": request.content}
            
            return {
                "parser": request.parser_type,
                "parsed": result,
                "options": request.options
            }
            
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON content")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    server = OpenParserServer()
    server.run() 