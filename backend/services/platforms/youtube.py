import os
import json
import logging
import asyncio
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

async def upload_to_youtube(video_path: str, caption: str, dummy_token: str = None) -> dict:
    """Uploads a vertical video (Short) to YouTube."""
    token_file = "youtube_token.json"
    
    if not os.path.exists(token_file):
        logger.error("[YouTube] Missing token. Please authenticate via /api/auth/youtube first.")
        return {"success": False, "error": "Not authenticated"}

    try:
        # Load saved credentials
        with open(token_file, "r") as f:
            creds_data = json.load(f)
        
        creds = Credentials(
            token=creds_data["token"],
            refresh_token=creds_data["refresh_token"],
            token_uri=creds_data["token_uri"],
            client_id=creds_data["client_id"],
            client_secret=creds_data["client_secret"],
            scopes=creds_data["scopes"]
        )

        youtube = build("youtube", "v3", credentials=creds)

        # Truncate title to 90 chars (YouTube limit is 100)
        title = caption[:90] + "..." if len(caption) > 90 else caption

        body = {
            "snippet": {
                "title": title,
                "description": caption,
                "categoryId": "22"  # 22 = People & Blogs
            },
            "status": {
                "privacyStatus": "private"  # Set to private for testing, change to "public" later
            }
        }

        # Upload the video file in chunks
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        logger.info("[YouTube] Starting real video upload...")
        
        # Execute the upload in a separate thread so it doesn't block our async server
        response = await asyncio.to_thread(request.execute)
        
        logger.info(f"[YouTube] Upload successful! Video ID: {response['id']}")
        return {"success": True, "platform_post_id": response["id"]}

    except Exception as e:
        logger.error(f"[YouTube] Upload failed: {str(e)}")
        return {"success": False, "error": str(e)}