"""
get_access_token.py

Obtains a long-lived Instagram User access token using the
"Instagram API with Instagram Login" (Business Login) flow.

This flow does NOT require a Facebook Page and does NOT require
App Review / Advanced Access as long as you are using the app on
an Instagram Professional account that you added as a Tester/Admin
in the App Dashboard (App Dashboard > App roles > Roles).

Requirements (from App Dashboard > Instagram > API setup with Instagram login):
    - INSTAGRAM_APP_ID       (different from your main Facebook App ID)
    - INSTAGRAM_APP_SECRET   (different from your main Facebook App Secret)
    - REDIRECT_URI           (must exactly match a URI registered in the dashboard)

Usage:
    1. Fill in the constants below.
    2. Run: python get_access_token.py
    3. Open the printed URL in a browser, log in with the Instagram
       professional account, approve the permissions.
    4. Copy the FULL URL you get redirected to and paste it back
       into the terminal when prompted.
    5. The script prints and saves the long-lived access token and
       the Instagram User ID to token_data.json.
"""

import json
import os
import sys
from urllib.parse import urlencode, urlparse, parse_qs

import requests
from dotenv import load_dotenv

load_dotenv()

# --------------------------------------------------------------------------
# CONFIGURATION - read from environment variables (.env), never hardcoded.
# Set META_APP_ID, META_APP_SECRET and INSTAGRAM_REDIRECT_URI in your .env
# (the first two are the same values used by backend/config.py).
# --------------------------------------------------------------------------
INSTAGRAM_APP_ID = os.getenv("META_APP_ID", "")
INSTAGRAM_APP_SECRET = os.getenv("META_APP_SECRET", "")
REDIRECT_URI = os.getenv(
    "INSTAGRAM_REDIRECT_URI", "http://localhost:8000/api/auth/instagram/callback"
)

# Scopes required to publish video/reels content
SCOPES = [
    "instagram_business_basic",
    "instagram_business_content_publish",
]

AUTH_BASE_URL = "https://www.instagram.com/oauth/authorize"
SHORT_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
LONG_TOKEN_URL = "https://graph.instagram.com/access_token"

TOKEN_FILE = "token_data.json"


def build_authorization_url() -> str:
    """Builds the URL the user must open in a browser to grant permissions."""
    params = {
        "client_id": INSTAGRAM_APP_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": ",".join(SCOPES),
    }
    return f"{AUTH_BASE_URL}?{urlencode(params)}"


def extract_code_from_redirect(redirect_url: str) -> str:
    """Extracts the 'code' query parameter from the redirect URL pasted by the user."""
    parsed = urlparse(redirect_url.strip())
    query = parse_qs(parsed.query)

    if "error" in query:
        error_desc = query.get("error_description", ["Unknown error"])[0]
        raise ValueError(f"Authorization was denied or failed: {error_desc}")

    if "code" not in query:
        raise ValueError(
            "No 'code' parameter found in the URL you pasted. "
            "Make sure you copied the full redirected URL."
        )

    # Instagram sometimes appends a trailing '#_' fragment, strip it just in case
    code = query["code"][0].split("#")[0]
    return code


def exchange_code_for_short_lived_token(code: str) -> dict:
    """Step 2: exchange the authorization code for a short-lived access token."""
    payload = {
        "client_id": INSTAGRAM_APP_ID,
        "client_secret": INSTAGRAM_APP_SECRET,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code": code,
    }

    response = requests.post(SHORT_TOKEN_URL, data=payload, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to exchange code for short-lived token: "
            f"{response.status_code} {response.text}"
        )

    data = response.json()

    # The API returns either a top-level dict or a "data" list depending on version
    if "data" in data:
        result = data["data"][0]
    else:
        result = data

    return result


def exchange_for_long_lived_token(short_lived_token: str) -> dict:
    """Step 3: exchange the short-lived token for a 60-day long-lived token."""
    params = {
        "grant_type": "ig_exchange_token",
        "client_secret": INSTAGRAM_APP_SECRET,
        "access_token": short_lived_token,
    }

    response = requests.get(LONG_TOKEN_URL, params=params, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to exchange for long-lived token: "
            f"{response.status_code} {response.text}"
        )

    return response.json()


def main() -> None:
    if not INSTAGRAM_APP_ID or not INSTAGRAM_APP_SECRET:
        print("ERROR: Set META_APP_ID and META_APP_SECRET in your .env file first.")
        sys.exit(1)

    auth_url = build_authorization_url()
    print("\nOpen this URL in your browser and log in with your Instagram")
    print("professional account, then approve the requested permissions:\n")
    print(auth_url)
    print()

    redirect_url = input(
        "After approving, paste the FULL URL you were redirected to here:\n> "
    )

    try:
        code = extract_code_from_redirect(redirect_url)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    print("\nExchanging authorization code for a short-lived access token...")
    try:
        short_lived = exchange_code_for_short_lived_token(code)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    ig_user_id = short_lived["user_id"]
    short_lived_token = short_lived["access_token"]
    print(f"Short-lived token obtained. Instagram User ID: {ig_user_id}")

    print("Exchanging short-lived token for a long-lived (60-day) token...")
    try:
        long_lived = exchange_for_long_lived_token(short_lived_token)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    result = {
        "instagram_user_id": ig_user_id,
        "access_token": long_lived["access_token"],
        "token_type": long_lived.get("token_type", "bearer"),
        "expires_in_seconds": long_lived.get("expires_in"),
    }

    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"\nSuccess. Long-lived token saved to {TOKEN_FILE}")
    print(f"Instagram User ID: {result['instagram_user_id']}")
    print(f"Token expires in:  {result['expires_in_seconds']} seconds (~60 days)")
    print(
        "\nRemember: this token must be refreshed before it expires. "
        "See refresh_token() usage notes in instagram_publisher.py."
    )


if __name__ == "__main__":
    main()