import asyncio
import logging
import httpx

logger = logging.getLogger(__name__)

async def upload_to_instagram(video_url: str, caption: str, access_token: str, ig_user_id: str) -> dict:
    if not access_token or not ig_user_id:
        logger.warning("[Instagram] Missing credentials, upload aborted.")
        return {"success": False, "error": "Missing credentials"}

    # Use the latest Graph API version
    api_version = "v20.0"
    base_url = "https://graph.instagram.com"

    try:
        async with httpx.AsyncClient() as client:
            # ---------------------------------------------------------
            # Step 1: Create Media Container
            # ---------------------------------------------------------
            logger.info("[Instagram] Step 1: Creating Reels Container")
            media_url = f"{base_url}/{api_version}/{ig_user_id}/media"

            payload = {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "access_token": access_token
            }

            response = await client.post(media_url, data=payload, timeout=60.0)
            response_data = response.json()

            if response.status_code >= 400 or "error" in response_data:
                err_msg = response_data.get("error", {}).get("message", response.text)
                logger.error(f"[Instagram] Container creation failed: {err_msg}")
                return {"success": False, "error": f"Failed to create container: {err_msg}"}

            container_id = response_data.get("id")
            if not container_id:
                return {"success": False, "error": "No container ID returned from Meta."}

            # ---------------------------------------------------------
            # Step 2: Poll Container Status until FINISHED
            # ---------------------------------------------------------
            logger.info(f"[Instagram] Step 2: Waiting for container {container_id} to finish processing...")
            status_url = f"{base_url}/{api_version}/{container_id}"
            status_params = {
                "fields": "status_code,status",
                "access_token": access_token
            }

            is_finished = False
            # Poll every 10 seconds, up to 30 times (5 minutes max)
            for attempt in range(30):
                await asyncio.sleep(10)
                status_response = await client.get(status_url, params=status_params, timeout=30.0)
                status_data = status_response.json()

                status_code = status_data.get("status_code")

                if status_code == "FINISHED":
                    is_finished = True
                    break
                elif status_code in ["ERROR", "EXPIRED"]:
                    logger.error(f"[Instagram] Video processing failed with status: {status_code}")
                    return {"success": False, "error": f"Container processing failed: {status_code}"}

                logger.info(f"[Instagram] Container status: {status_code}. Retrying in 10s... ({attempt + 1}/30)")

            if not is_finished:
                logger.error("[Instagram] Timeout waiting for container processing.")
                return {"success": False, "error": "Timeout waiting for container processing"}

            # ---------------------------------------------------------
            # Step 3: Publish the Container
            # ---------------------------------------------------------
            logger.info("[Instagram] Step 3: Publishing Container")
            publish_url = f"{base_url}/{api_version}/{ig_user_id}/media_publish"
            publish_payload = {
                "creation_id": container_id,
                "access_token": access_token
            }

            pub_response = await client.post(publish_url, data=publish_payload, timeout=60.0)
            pub_data = pub_response.json()

            if pub_response.status_code >= 400 or "error" in pub_data:
                err_msg = pub_data.get("error", {}).get("message", pub_response.text)
                logger.error(f"[Instagram] Publishing failed: {err_msg}")
                return {"success": False, "error": f"Failed to publish: {err_msg}"}

            media_id = pub_data.get("id")
            logger.info(f"[Instagram] Upload successful! Media ID: {media_id}")
            return {"success": True, "platform_post_id": media_id}

    except Exception as e:
        logger.error(f"[Instagram] Exception occurred: {e}")
        return {"success": False, "error": str(e)}


# --- Standalone test entry point (module level, not inside the function) ---
if __name__ == "__main__":
    import os
    # Ensure you have run: pip install python-dotenv
    from dotenv import load_dotenv

    # 1. Load variables from the .env file
    load_dotenv()

    # 2. Get the credentials securely
    my_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    my_account_id = os.getenv("INSTAGRAM_ACCOUNT_ID")

    # 3. Provide a test public video URL and a caption
    test_video = "https://www.w3schools.com/html/mov_bbb.mp4"
    test_caption = "Testing automated Reels upload via Graph API!"

    # 4. Run the async function
    print("Starting upload process...")
    result = asyncio.run(upload_to_instagram(test_video, test_caption, my_token, my_account_id))
    print(f"Final Result: {result}")