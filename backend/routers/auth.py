import os
import json
import httpx
from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv
from sqlalchemy import select

from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.models import Account

load_dotenv()

# Required for local testing with HTTP instead of HTTPS
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── YouTube ────────────────────────────────────────────────────────────────────

YT_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
YT_REDIRECT = "http://localhost:8000/api/auth/youtube/callback"

auth_flows: dict = {}


def get_yt_client_config():
    return {
        "web": {
            "client_id": os.getenv("YOUTUBE_CLIENT_ID"),
            "client_secret": os.getenv("YOUTUBE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [YT_REDIRECT],
        }
    }


@router.get("/youtube")
def auth_youtube():
    flow = Flow.from_client_config(get_yt_client_config(), scopes=YT_SCOPES)
    flow.redirect_uri = YT_REDIRECT
    auth_url, state = flow.authorization_url(prompt="consent", access_type="offline")
    auth_flows[state] = flow
    return RedirectResponse(auth_url)


@router.get("/youtube/callback")
def auth_youtube_callback(state: str, code: str):
    if state not in auth_flows:
        return {"success": False, "error": "Auth session expired or invalid state. Please try again."}

    flow = auth_flows[state]
    flow.fetch_token(code=code)
    credentials = flow.credentials

    creds_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }

    with open("youtube_token.json", "w") as f:
        json.dump(creds_data, f)

    del auth_flows[state]
    return RedirectResponse(url="http://localhost:8000")


# ── Instagram ──────────────────────────────────────────────────────────────────
#
#  Uses "Instagram API with Instagram Login" (Business Login).
#  Scopes needed: instagram_business_basic, instagram_business_content_publish
#
#  IMPORTANT — before this flow works you must add the redirect URI
#  http://localhost:8000/api/auth/instagram/callback
#  in your Instagram App Dashboard:
#    App Dashboard → Instagram → API setup with Instagram login
#    → Valid OAuth Redirect URIs
#
#  Make sure META_APP_ID and META_APP_SECRET in your .env file match
#  the Instagram App credentials from that same page.

IG_REDIRECT = "http://localhost:8000/api/auth/instagram/callback"
IG_AUTH_URL = "https://www.instagram.com/oauth/authorize"
IG_SHORT_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
IG_LONG_TOKEN_URL = "https://graph.instagram.com/access_token"
IG_SCOPES = "instagram_business_basic,instagram_business_content_publish"


@router.get("/instagram")
def auth_instagram():
    """Redirects the user to Instagram's OAuth consent screen."""
    params = {
        "client_id": settings.meta_app_id,
        "redirect_uri": IG_REDIRECT,
        "response_type": "code",
        "scope": IG_SCOPES,
    }
    return RedirectResponse(f"{IG_AUTH_URL}?{urlencode(params)}")


@router.get("/instagram/callback")
async def auth_instagram_callback(code: str = None, error: str = None, error_reason: str = None):
    """Exchanges the code for a long-lived token and saves credentials to the DB."""
    if error:
        return {"success": False, "error": f"Authorization denied: {error_reason or error}"}
    if not code:
        return {"success": False, "error": "No authorization code received from Instagram."}

    # Instagram sometimes appends a trailing '#_' fragment — strip it
    code = code.split("#")[0]

    async with httpx.AsyncClient() as client:
        # Step 1: exchange code for a short-lived token
        short_resp = await client.post(
            IG_SHORT_TOKEN_URL,
            data={
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": IG_REDIRECT,
                "code": code,
            },
            timeout=30,
        )
        short_data = short_resp.json()

    if "error_type" in short_data or "error" in short_data:
        err = short_data.get("error_message") or short_data.get("error", {}).get("message", str(short_data))
        return {"success": False, "error": f"Token exchange failed: {err}"}

    ig_user_id = str(short_data.get("user_id", ""))
    short_token = short_data.get("access_token", "")

    async with httpx.AsyncClient() as client:
        # Step 2: exchange short-lived token for a 60-day long-lived token
        long_resp = await client.get(
            IG_LONG_TOKEN_URL,
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": settings.meta_app_secret,
                "access_token": short_token,
            },
            timeout=30,
        )
        long_data = long_resp.json()

        # Step 3: fetch the Instagram username so we can show it in the UI
        me_resp = await client.get(
            f"https://graph.instagram.com/me",
            params={"fields": "username", "access_token": long_data.get("access_token", short_token)},
            timeout=15,
        )
        me_data = me_resp.json()

    long_token = long_data.get("access_token", short_token)
    expires_in = long_data.get("expires_in", 5183944)  # default ~60 days
    username = me_data.get("username", ig_user_id)

    # Step 4: upsert into the accounts table
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Account).where(Account.platform == "instagram"))
        account = result.scalar_one_or_none()

        if account is None:
            account = Account(platform="instagram")
            db.add(account)

        account.account_name = username
        account.access_token = long_token
        account.extra_data = json.dumps({"instagram_user_id": ig_user_id})
        account.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        await db.commit()

    return RedirectResponse(url="http://localhost:8000?ig_connected=1")
