"""Seed the database with demo subcontractors and sample jobs.

Subcontractors are **app data** (SQLAlchemy), stored in whatever DATABASE_URL points to
(local SQLite or Supabase Postgres). They are not Supabase Auth users — those are only
people who log into the SPA (see UserProfile, which maps auth.sub → profile row).

For integration testing, demo subs share one phone (SMS) and one email (Resend).
"""
import uuid
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from genie.db.models import Job, Lead, Message, Schedule, Subcontractor

# All seeded subs use these for Twilio / Resend smoke tests (store E.164 with +).
DEMO_CONTACT_PHONE = "+14087221995"
DEMO_CONTACT_EMAIL = "z.hensley.m@gmail.com"

SUBCONTRACTORS = [
    {"name": "Marcus Rivera", "email": DEMO_CONTACT_EMAIL, "phone": DEMO_CONTACT_PHONE, "skills": ["electrical", "wiring", "panel upgrades"], "hourly_rate": 85.0, "location": "San Jose, CA", "rating": 4.8, "completed_jobs": 142},
    {"name": "Sarah Chen", "email": DEMO_CONTACT_EMAIL, "phone": DEMO_CONTACT_PHONE, "skills": ["plumbing", "pipe fitting", "water heaters"], "hourly_rate": 75.0, "location": "San Jose, CA", "rating": 4.9, "completed_jobs": 198},
    {"name": "Derek Johnson", "email": DEMO_CONTACT_EMAIL, "phone": DEMO_CONTACT_PHONE, "skills": ["carpentry", "framing", "drywall"], "hourly_rate": 65.0, "location": "Santa Clara, CA", "rating": 4.5, "completed_jobs": 87},
    {"name": "Priya Patel", "email": DEMO_CONTACT_EMAIL, "phone": DEMO_CONTACT_PHONE, "skills": ["landscaping", "irrigation", "hardscaping"], "hourly_rate": 55.0, "location": "Cupertino, CA", "rating": 4.7, "completed_jobs": 223},
    {"name": "Tom O'Brien", "email": DEMO_CONTACT_EMAIL, "phone": DEMO_CONTACT_PHONE, "skills": ["hvac", "refrigeration", "ductwork"], "hourly_rate": 95.0, "location": "San Jose, CA", "rating": 4.6, "completed_jobs": 115},
    {"name": "Lisa Nguyen", "email": DEMO_CONTACT_EMAIL, "phone": DEMO_CONTACT_PHONE, "skills": ["painting", "drywall", "finishing"], "hourly_rate": 50.0, "location": "Sunnyvale, CA", "rating": 4.3, "completed_jobs": 64},
    {"name": "Carlos Mendez", "email": DEMO_CONTACT_EMAIL, "phone": DEMO_CONTACT_PHONE, "skills": ["tiling", "flooring", "waterproofing"], "hourly_rate": 70.0, "location": "San Jose, CA", "rating": 4.7, "completed_jobs": 176},
    {"name": "James Park", "email": DEMO_CONTACT_EMAIL, "phone": DEMO_CONTACT_PHONE, "skills": ["roofing", "gutters", "waterproofing"], "hourly_rate": 80.0, "location": "Mountain View, CA", "rating": 4.4, "completed_jobs": 93},
]

SAMPLE_JOBS = [
    {
        "title": "Electrical Panel Upgrade — Westlake Home",
        "description": "Upgrade 100A panel to 200A, add 4 new circuits for EV charger and kitchen remodel. Home built in 1985.",
        "required_skills": ["electrical", "panel upgrades"],
        "location": "San Jose, CA",
        "status": "pending",
        "budget": 3200.0,
        "priority": "high",
    },
    {
        "title": "Master Bath Plumbing Rough-In",
        "description": "Rough-in plumbing for new master bathroom addition. Includes 2 sinks, walk-in shower, soaking tub, and toilet.",
        "required_skills": ["plumbing", "bathroom remodel"],
        "location": "San Jose, CA",
        "status": "pending",
        "budget": 4500.0,
        "priority": "medium",
    },
    {
        "title": "Commercial Landscaping — Office Park",
        "description": "Install new irrigation system and hardscaping for 2-acre commercial property. Deadline is end of month.",
        "required_skills": ["landscaping", "irrigation", "hardscaping"],
        "location": "Cupertino, CA",
        "status": "pending",
        "budget": 12000.0,
        "priority": "high",
    },
    {
        "title": "HVAC System Replacement",
        "description": "Replace aging 5-ton HVAC system with new high-efficiency unit. Includes ductwork inspection and sealing.",
        "required_skills": ["hvac", "ductwork"],
        "location": "San Jose, CA",
        "status": "pending",
        "budget": 8500.0,
        "priority": "critical",
    },
    {
        "title": "Interior Painting — 3BR Rental Property",
        "description": "Full interior repaint of 3-bedroom rental unit between tenants. Ceilings, walls, trim. Needs to be done within 5 days.",
        "required_skills": ["painting", "finishing"],
        "location": "Sunnyvale, CA",
        "status": "pending",
        "budget": 2200.0,
        "priority": "medium",
    },
]


async def seed_database(session: AsyncSession) -> None:
    """Insert seed data if tables are empty."""
    from sqlalchemy import select

    result = await session.execute(select(Subcontractor).limit(1))
    if result.scalar_one_or_none() is not None:
        return  # already seeded

    today = date.today()

    for data in SUBCONTRACTORS:
        sub = Subcontractor(
            id=str(uuid.uuid4()),
            availability_status="available",
            **data,
        )
        session.add(sub)

    # Future jobs (pending)
    for i, data in enumerate(SAMPLE_JOBS):
        start = today + timedelta(days=3 + i * 2)
        end = start + timedelta(days=2)
        job = Job(
            id=str(uuid.uuid4()),
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            **data,
        )
        session.add(job)

    # --- Demo: overdue in-progress jobs (the "money moment") ---
    from sqlalchemy import select as _select
    sub_result = await session.execute(_select(Subcontractor).limit(4))
    demo_subs = sub_result.scalars().all()

    overdue_jobs = [
        {
            "title": "Drywall & Tape — Oakview Remodel",
            "description": "Hang, tape, and finish drywall in master bedroom addition. 3 coats required.",
            "required_skills": ["carpentry", "drywall"],
            "location": "San Jose, CA",
            "status": "in_progress",
            "budget": 2800.0,
            "priority": "high",
        },
        {
            "title": "Bathroom Tile Install — Riverside Condo",
            "description": "Install floor and shower tile in primary bath, including waterproofing membrane.",
            "required_skills": ["tiling", "waterproofing"],
            "location": "San Jose, CA",
            "status": "in_progress",
            "budget": 3400.0,
            "priority": "medium",
        },
    ]

    for i, data in enumerate(overdue_jobs):
        sub = demo_subs[i] if i < len(demo_subs) else None
        overdue_start = today - timedelta(days=7 + i * 2)
        overdue_end = today - timedelta(days=2 + i)  # past due
        job = Job(
            id=str(uuid.uuid4()),
            start_date=overdue_start.isoformat(),
            end_date=overdue_end.isoformat(),
            assigned_subcontractor_id=sub.id if sub else None,
            **data,
        )
        session.add(job)

        if sub:
            sched = Schedule(
                id=str(uuid.uuid4()),
                job_id=job.id,
                subcontractor_id=sub.id,
                scheduled_start=overdue_start.isoformat() + "T08:00:00",
                scheduled_end=overdue_end.isoformat() + "T17:00:00",
                notes="Overdue — no check-in received.",
            )
            session.add(sched)

            msg = Message(
                id=str(uuid.uuid4()),
                job_id=job.id,
                subcontractor_id=sub.id,
                direction="outbound",
                channel="sms",
                subject=f"Assignment: {data['title']}",
                body=f"Hi {sub.name}, you've been assigned to {data['title']}. Start date is {overdue_start.isoformat()}. Let me know if you have questions.",
                status="delivered",
            )
            session.add(msg)

    demo_lead = Lead(
        id=str(uuid.uuid4()),
        name="Demo Lead",
        email=DEMO_CONTACT_EMAIL,
        phone=DEMO_CONTACT_PHONE,
        message="Hi, I'm looking to renovate my kitchen — new cabinets, countertops, and tile backsplash. Would love to get a quote this week if possible.",
        status="new",
        ai_summary="Homeowner seeking kitchen renovation — quote requested this week.",
        auto_reply_sent=False,
    )
    session.add(demo_lead)

    await session.commit()
    n = len(SUBCONTRACTORS)
    print(f"✓ Database seeded with {n} subs, 5 pending jobs, 2 overdue jobs, and 1 demo lead.")
