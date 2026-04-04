#!/usr/bin/env python3
"""Overwrite phone + email on all subcontractors and leads (integration test contacts).

Run from repo root:
  ./venv/bin/python scripts/apply_demo_contacts.py

Uses the same DEMO_CONTACT_* values as genie.db.seed. Safe to run anytime.
"""
import asyncio
import sys
from pathlib import Path

# Repo root on sys.path
_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from sqlalchemy import update

from genie.db.database import AsyncSessionLocal
from genie.db.models import Lead, Subcontractor
from genie.db.seed import DEMO_CONTACT_EMAIL, DEMO_CONTACT_PHONE


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Subcontractor).values(phone=DEMO_CONTACT_PHONE, email=DEMO_CONTACT_EMAIL)
        )
        await session.execute(
            update(Lead).values(phone=DEMO_CONTACT_PHONE, email=DEMO_CONTACT_EMAIL)
        )
        await session.commit()
    r = await _counts()
    print(f"Updated all subcontractors and leads → phone={DEMO_CONTACT_PHONE} email={DEMO_CONTACT_EMAIL}")
    print(f"  ({r['subs']} subcontractor row(s), {r['leads']} lead row(s))")


async def _counts() -> dict:
    from sqlalchemy import func, select

    async with AsyncSessionLocal() as session:
        ns = await session.scalar(select(func.count()).select_from(Subcontractor))
        nl = await session.scalar(select(func.count()).select_from(Lead))
    return {"subs": int(ns or 0), "leads": int(nl or 0)}


if __name__ == "__main__":
    asyncio.run(main())
