from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
import logging

from backend.database import init_db
from backend.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────────
    logger.info("SocialBridge starting up...")

    # 1. Create DB tables
    await init_db()
    logger.info("Database ready ✓")

    # 2. Ensure /uploads exists
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    logger.info(f"Upload dir '{settings.upload_dir}' ready ✓")

    # 3. Start background scheduler
    from backend.scheduler.worker import start_scheduler
    scheduler = start_scheduler()

    yield  # app is now running

    # ── Shutdown ───────────────────────────────────────────────────────────
    scheduler.shutdown(wait=False)
    logger.info("SocialBridge stopped.")

app = FastAPI(
    title="SocialBridge",
    description="Auto-schedule & post vertical videos to social platforms",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
from backend.routers import posts, captions, auth

app.include_router(posts.router, prefix="/api", tags=["posts"])
app.include_router(captions.router, prefix="/api", tags=["captions"])
app.include_router(auth.router)
# app.include_router(accounts.router, prefix="/api", tags=["accounts"])


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "app": "SocialBridge", "version": "0.1.0"}

# ── Uploaded videos (MUST be mounted BEFORE the frontend catch-all "/" mount) ──
# This makes videos publicly fetchable at:
#   {PUBLIC_BASE_URL}/uploads/<filename>.mp4
# which is required by Instagram's Graph API (it needs a public video_url,
# not a local file path).
_uploads_dir = Path(settings.upload_dir)
_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")

# ── Frontend (HTML/JS/CSS) ────────────────────────────────────────────────────
_frontend = Path(__file__).parent.parent / "frontend"
if _frontend.exists():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")