"""
import_instagram_token.py

One-time helper: reads token_data.json (produced by get_access_token.py)
and saves/updates the Instagram credentials in the `accounts` DB table,
so the scheduler (worker.py) can load them automatically.

Place this file inside the `backend/` folder (next to main.py, worker.py, etc.)
and run it from the project root with:

    python -m backend.import_instagram_token

Re-run it any time you get a fresh token (e.g. after a manual refresh).
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models import Account

# token_data.json lives at the project root (same place get_access_token.py writes it)
TOKEN_FILE = Path(__file__).parent.parent / "token_data.json"


async def main():
    if not TOKEN_FILE.exists():
        print(f"ERROR: {TOKEN_FILE} not found. Run get_access_token.py first.")
        return

    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    access_token = data["access_token"]
    ig_user_id = data["instagram_user_id"]
    expires_in = data.get("expires_in_seconds")
    expires_at = (
        datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Account).where(Account.platform == "instagram"))
        account = result.scalar_one_or_none()

        if account is None:
            account = Account(platform="instagram")
            db.add(account)

        account.access_token = access_token
        account.expires_at = expires_at
        account.extra_data = json.dumps({"instagram_user_id": ig_user_id})

        await db.commit()

    print("✅ Instagram account saved to DB.")
    print(f"   instagram_user_id: {ig_user_id}")
    print(f"   expires_at:        {expires_at}")


if __name__ == "__main__":
    asyncio.run(main())