from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
import asyncio
import json
from datetime import datetime
from pathlib import Path
from sqlalchemy import select
from backend.database import AsyncSessionLocal
from backend.models import Post, PostStatus, Account
from backend.config import settings

# Platform imports
from backend.services.platforms.youtube import upload_to_youtube
from backend.services.platforms.tiktok import upload_to_tiktok
from backend.services.platforms.instagram import upload_to_instagram
from backend.services.platforms.facebook import upload_to_facebook
from backend.services.platforms.x import upload_to_x

logger = logging.getLogger(__name__)


async def get_account(db, platform: str) -> Account | None:
    """Fetch stored OAuth/API credentials for a platform from the Account table."""
    result = await db.execute(select(Account).where(Account.platform == platform))
    return result.scalar_one_or_none()


def build_public_video_url(video_path: str) -> str | None:
    """Turns a locally-stored video path into a publicly fetchable URL,
    using the /uploads static mount + PUBLIC_BASE_URL setting."""
    if not settings.public_base_url:
        logger.warning(
            "[Config] PUBLIC_BASE_URL is not set — cannot build a public video URL. "
            "Set it to your deployed app's domain (e.g. https://your-app.up.railway.app)."
        )
        return None
    filename = Path(video_path).name
    base = settings.public_base_url.rstrip("/")
    return f"{base}/uploads/{filename}"


async def process_pending_posts():
    async with AsyncSessionLocal() as db:
        now = datetime.now()

        # --- DEBUGGING SYSTEM ---
        debug_result = await db.execute(select(Post).where(Post.status == PostStatus.pending))
        all_pending = debug_result.scalars().all()
        if all_pending:
            logger.info(f"[DEBUG] Current system time: {now}")
            for p in all_pending:
                logger.info(f"[DEBUG] Video #{p.id} is pending in DB for: {p.scheduled_at}")
        # ------------------------

        result = await db.execute(
            select(Post).where(
                Post.status == PostStatus.pending,
                Post.scheduled_at <= now
            )
        )
        posts = result.scalars().all()

        if not posts:
            logger.info("[Scheduler] ⏳ No videos are ready at this moment.")
            return

        # Load Instagram credentials once per run (same account for every post, for now)
        ig_account = await get_account(db, "instagram")

        for post in posts:
            logger.info(f"[Scheduler] 🚀 Starting publication for video #{post.id}!")

            # Set status to processing to avoid duplicate runs
            post.status = PostStatus.processing
            await db.commit()

            # --- PLATFORM API CALLS ---
            yt_res = await upload_to_youtube(post.video_path, post.caption, "dummy_token")
            logger.info(f"YouTube Response: {yt_res}")

            tt_res = await upload_to_tiktok(post.video_path, post.caption, "dummy_token", "dummy_openid")
            logger.info(f"TikTok Response: {tt_res}")

            # --- Instagram ---
            if ig_account and ig_account.access_token:
                video_public_url = build_public_video_url(post.video_path)
                extra = json.loads(ig_account.extra_data or "{}")
                ig_user_id = extra.get("instagram_user_id")

                if not video_public_url:
                    ig_res = {"success": False, "error": "PUBLIC_BASE_URL is not configured"}
                elif not ig_user_id:
                    ig_res = {"success": False, "error": "Missing instagram_user_id in Account.extra_data"}
                else:
                    ig_res = await upload_to_instagram(
                        video_public_url, post.caption, ig_account.access_token, ig_user_id
                    )
            else:
                ig_res = {"success": False, "error": "Instagram account not connected"}
            logger.info(f"Instagram Response: {ig_res}")

            fb_res = await upload_to_facebook(post.video_path, post.caption, "dummy_token", "dummy_page_id")
            logger.info(f"Facebook Response: {fb_res}")

            x_res = await upload_to_x(post.video_path, post.caption, "dummy_token", "dummy_secret")
            logger.info(f"X/Twitter Response: {x_res}")

            # Mark as completed
            post.status = PostStatus.posted
            await db.commit()
            logger.info(f"[Scheduler] ✅ Process for video #{post.id} completed.")


def check_pending_posts():
    asyncio.run(process_pending_posts())


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=check_pending_posts,
        trigger=IntervalTrigger(minutes=1),
        id="check_pending_posts",
        name="Publish pending posts",
        replace_existing=True,
        misfire_grace_time=30,
    )
    scheduler.start()
    logger.info("[Scheduler] Worker started — Checking DB every 60 seconds.")
    return scheduler