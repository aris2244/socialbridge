from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models import Post
from backend.config import settings
import shutil
import os
import uuid
from datetime import datetime

router = APIRouter()

@router.post("/upload")
async def upload_post(
    video: UploadFile = File(...),
    caption: str = Form(""),
    hashtags: str = Form("[]"),
    scheduled_at: datetime = Form(...),
    db: AsyncSession = Depends(get_db)
):
    # 1. Δημιουργούμε ένα μοναδικό όνομα για το βίντεο (π.χ. 123e4567.mp4)
    file_extension = video.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(settings.upload_dir, unique_filename)
    
    # 2. Σώζουμε το βίντεο στον φάκελο uploads
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)
        
    # 3. Εισαγωγή στη βάση δεδομένων
    new_post = Post(
        video_path=file_path,
        caption=caption,
        hashtags=hashtags,
        scheduled_at=scheduled_at
    )
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post)
    
    return {"message": "Το βίντεο προγραμματίστηκε επιτυχώς!", "post_id": new_post.id}