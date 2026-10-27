import httpx
import logging

logger = logging.getLogger(__name__)

async def upload_to_tiktok(video_path: str, caption: str, access_token: str, open_id: str) -> dict:
    if not access_token:
        logger.warning("[TikTok] Λείπει το access token, η ανάρτηση ακυρώθηκε.")
        return {"success": False, "error": "Missing access token"}

    try:
        logger.info("[TikTok] Αίτημα για Direct Post")
        
        # 1. Επικοινωνία με το endpoint: POST https://open.tiktokapis.com/v2/post/publish/video/init/
        # Εδώ στέλνουμε το μέγεθος του αρχείου και παίρνουμε το upload URL.
        # 2. Ανέβασμα του βίντεο στο URL που μας έδωσε.
        
        # TODO: Ενεργοποίηση της κανονικής κλήσης όταν μπουν τα OAuth Tokens
        return {"success": True, "platform_post_id": "tt_dummy_id_101"}
        
    except Exception as e:
        logger.error(f"[TikTok] Σφάλμα: {e}")
        return {"success": False, "error": str(e)}