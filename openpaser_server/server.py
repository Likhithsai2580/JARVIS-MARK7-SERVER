from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import torch
from PIL import Image
import io
from transformers import AutoProcessor, AutoModelForObjectDetection
import numpy as np
from typing import List, Dict, Any

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OmniParser model
processor = AutoProcessor.from_pretrained("microsoft/omniparser-layout")
model = AutoModelForObjectDetection.from_pretrained("microsoft/omniparser-layout")

class OmniParserService:
    def __init__(self):
        self.processor = processor
        self.model = model
        
    async def process_image(self, image: Image.Image) -> Dict[str, Any]:
        # Process image with OmniParser
        inputs = self.processor(images=image, return_tensors="pt")
        outputs = self.model(**inputs)
        
        # Convert outputs to normalized coordinates
        target_sizes = torch.tensor([image.size[::-1]])
        results = self.processor.post_process_object_detection(outputs, 
                                                            target_sizes=target_sizes,
                                                            threshold=0.5)[0]
        
        # Format results
        boxes = results["boxes"].tolist()
        scores = results["scores"].tolist()
        labels = results["labels"].tolist()
        
        parsed_elements = []
        for box, score, label in zip(boxes, scores, labels):
            parsed_elements.append({
                "box": box,  # [x1, y1, x2, y2]
                "score": score,
                "label": self.processor.id2label[label],
                "coordinates": {
                    "x1": box[0],
                    "y1": box[1],
                    "x2": box[2],
                    "y2": box[3]
                }
            })
            
        return {
            "elements": parsed_elements,
            "image_size": image.size
        }

parser_service = OmniParserService()

@app.post("/parse")
async def parse_image(file: UploadFile = File(...)):
    """
    Parse an image and return the detected UI elements with their coordinates
    """
    try:
        # Read and process the image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # Get parsing results
        results = await parser_service.process_image(image)
        
        return {
            "status": "success",
            "data": results
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 