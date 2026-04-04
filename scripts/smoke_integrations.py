#!/usr/bin/env python3
"""Optional live sends for Resend + Twilio (and print Supabase / DB checks).

From repo root:
  ./venv/bin/python scripts/smoke_integrations.py
  ./venv/bin/python scripts/smoke_integrations.py --sms --email

Does not send anything unless --sms and/or --email are passed.
"""
import argparse
import asyncio
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from sqlalchemy import text

from genie.config import settings
from genie.db.database import engine
from genie.db.seed import DEMO_CONTACT_EMAIL, DEMO_CONTACT_PHONE
from genie.tools.communication_tools import (
    _send_resend_email,
    _send_twilio_sms,
    twilio_sms_configured,
)


async def check_db() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        print(f"database: FAIL ({exc})")
        return False


def check_supabase_config() -> dict:
    url = bool(settings.supabase_url.strip())
    anon = bool(settings.supabase_anon_key.strip())
    jwt = bool(settings.supabase_jwt_secret.strip())
    pooler = "supabase" in settings.database_url.lower()
    return {
        "supabase_url_set": url,
        "supabase_anon_key_set": anon,
        "supabase_jwt_secret_set": jwt,
        "database_url_looks_like_supabase_pooler": pooler,
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sms", action="store_true", help="Send one Twilio SMS to demo phone")
    parser.add_argument("--email", action="store_true", help="Send one Resend email to demo address")
    args = parser.parse_args()

    print("--- Config (no secrets printed) ---")
    print("  anthropic_api_key:", "set" if settings.anthropic_api_key.strip() else "missing")
    print("  resend_api_key:", "set" if settings.resend_api_key.strip() else "missing")
    print("  twilio_sms_configured:", twilio_sms_configured())
    for k, v in check_supabase_config().items():
        print(f"  {k}:", v)

    ok = await check_db()
    print("  database_reachable:", ok)

    if args.sms:
        if not twilio_sms_configured():
            print("SMS: skipped (Twilio not fully configured)")
        else:
            try:
                status = await _send_twilio_sms(DEMO_CONTACT_PHONE, "Genie smoke test: Twilio SMS OK.")
                print("SMS sent, Twilio status:", status)
            except Exception as exc:
                print("SMS: FAILED —", exc)

    if args.email:
        if not settings.resend_api_key.strip():
            print("Email: skipped (RESEND_API_KEY empty)")
        else:
            try:
                await _send_resend_email(
                    DEMO_CONTACT_EMAIL,
                    "Genie smoke test",
                    "If you see this, Resend is working.",
                )
                print("Email: sent via Resend to", DEMO_CONTACT_EMAIL)
            except Exception as exc:
                print("Email: FAILED —", exc)

    if not args.sms and not args.email:
        print("\n(No --sms / --email — no messages sent. Browser login tests Supabase Auth.)")


if __name__ == "__main__":
    asyncio.run(main())
