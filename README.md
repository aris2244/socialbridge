# SocialBridge

**Upload once, schedule everywhere.** A self-hosted scheduler that takes a vertical video, generates an AI caption for it, and auto-publishes it to multiple social platforms at a chosen time.

## What it does

- **Upload & schedule** — upload a vertical video (Reel/Short/TikTok format) with a caption and a publish time; it's stored and queued in a local database.
- **AI caption generation** — generates a caption + hashtags for a topic using Google Gemini.
- **Background scheduler** — a background job checks every minute for posts whose scheduled time has arrived and publishes them automatically.
- **Multi-platform publishing** — current status per platform:
  - **YouTube** — real upload via the YouTube Data API v3 (OAuth2), uploads as a private Short by default.
  - **Instagram** — real upload via the Instagram Graph API (Business Login), full container-create → poll → publish flow.
  - **Facebook, TikTok, X/Twitter** — integration points exist (`backend/services/platforms/`) but currently return a dummy/placeholder response; the real API calls are not wired up yet (marked with `TODO` in the code).
- **OAuth connection flows** — `/api/auth/youtube` and `/api/auth/instagram` routes handle the OAuth dance and store the resulting tokens.

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI (async) |
| Database | SQLite (via SQLAlchemy, async) — local file, no external DB needed |
| Frontend | Static HTML (`frontend/index.html`) |
| Scheduler | APScheduler, polling every 60 seconds |
| AI | Google Gemini (`google-generativeai`), for caption generation |
| Auth to platforms | OAuth2 — Google (`google-auth-oauthlib`) for YouTube, Instagram's own OAuth flow via `httpx` |

## Project structure

```
.
├── backend/
│   ├── main.py                  # FastAPI app, routers, static mounts
│   ├── config.py                 # Settings loaded from environment variables
│   ├── database.py                # SQLite (async) engine + session
│   ├── models.py                   # Post / PostPlatform / Account tables
│   ├── routers/
│   │   ├── auth.py                   # OAuth flows (YouTube, Instagram)
│   │   ├── posts.py                   # Upload + schedule a post
│   │   └── captions.py                 # AI caption generation endpoint
│   ├── scheduler/worker.py              # Background job: publishes due posts
│   └── services/
│       ├── ai/caption_generator.py       # Gemini caption generation
│       └── platforms/                      # One file per platform (youtube, instagram, facebook, tiktok, x)
├── frontend/index.html             # Static single-page frontend
├── get_access_token.py               # Standalone CLI helper to get an Instagram token without running the server
├── requirements.txt
└── .env.example                        # Template for required environment variables
```

## Getting started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Fill in `.env` with real values — see the table in `.env.example` for what each one does. You only need credentials for the platforms you intend to use. **Never commit `.env`** (already covered by `.gitignore`).

### 3. Run locally

```bash
uvicorn backend.main:app --reload
```

The app serves the API and the static frontend together on `http://localhost:8000`.

### 4. Connect accounts

- YouTube: visit `/api/auth/youtube`, log in, grant permission.
- Instagram: visit `/api/auth/instagram` (requires `META_APP_ID`/`META_APP_SECRET` set and the redirect URI registered in your Meta App Dashboard), **or** run `python get_access_token.py` as a one-off CLI flow and import the result with `python -m backend.import_instagram_token`.

## Security notes

This repository was cleaned up from an earlier version where `get_access_token.py` had a real Meta/Instagram **App ID and App Secret hardcoded directly in the source** (`INSTAGRAM_APP_ID` / `INSTAGRAM_APP_SECRET`). That has been moved to environment variables (`META_APP_ID` / `META_APP_SECRET` in `.env`, see `.env.example`). The rest of the codebase (`backend/config.py`, `backend/routers/auth.py`) was already reading these from the environment correctly — only this one helper script had the literal values.

**If you ever used this script with real credentials, treat that Meta App Secret as compromised and rotate it** in the Meta App Dashboard (App settings → Basic → App Secret → Reset) before reusing this project, even though the repo was never public with that commit in it.

`backend/config.py` also has an `app_secret_key` setting with a placeholder default (`"change-me-in-production"`). It isn't used anywhere yet, but if you wire up signed sessions or JWTs later, replace it with a real random value — never ship the placeholder.

## License

No license has been specified yet. All rights reserved by default until one is added.
