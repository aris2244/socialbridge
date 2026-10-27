from fastapi import APIRouter
from pydantic import BaseModel
from backend.services.ai.caption_generator import generate_caption

router = APIRouter()

class CaptionRequest(BaseModel):
    topic: str

@router.post("/generate")
async def api_generate_caption(request: CaptionRequest):
    result = await generate_caption(request.topic)
    return result