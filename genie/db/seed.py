"""Seed the database with realistic fake subcontractors and sample jobs."""
import uuid
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from genie.db.models import Job, Lead, Message, Schedule, Subcontractor


SUBCONTRACTORS = [
    {"name": "Prad Chebolu", "email": "pc65@rice.edu", "phone": "3467196530", "skills": ["electrical", "wiring", "panel upgrades"], "hourly_rate": 85.0, "location": "Austin, TX", "rating": 4.8, "completed_jobs": 142},
    {"name": "Zane Hensley", "email": "zh66@rice.edu", "phone": "4087221995", "skills": ["plumbing", "pipe fitting", "water heaters"], "hourly_rate": 75.0, "location": "Austin, TX", "rating": 4.9, "completed_jobs": 198},
    {"name": "Prad Chebolu", "email": "pc65@rice.edu", "phone": "3467196530", "skills": ["carpentry", "framing", "drywall"], "hourly_rate": 65.0, "location": "Round Rock, TX", "rating": 4.5, "completed_jobs": 87},
    {"name": "Zane Hensley", "email": "zh66@rice.edu", "phone": "4087221995", "skills": ["landscaping", "irrigation", "hardscaping"], "hourly_rate": 55.0, "location": "Cedar Park, TX", "rating": 4.7, "completed_jobs": 223},
    {"name": "Prad Chebolu", "email": "pc65@rice.edu", "phone": "3467196530", "skills": ["hvac", "refrigeration", "ductwork"], "hourly_rate": 95.0, "location": "Austin, TX", "rating": 4.6, "completed_jobs": 115},
    {"name": "Zane Hensley", "email": "zh66@rice.edu", "phone": "4087221995", "skills": ["painting", "drywall", "finishing"], "hourly_rate": 50.0, "location": "Pflugerville, TX", "rating": 4.3, "completed_jobs": 64},
    {"name": "Prad Chebolu", "email": "pc65@rice.edu", "phone": "3467196530", "skills": ["tiling", "flooring", "waterproofing"], "hourly_rate": 70.0, "location": "Austin, TX", "rating": 4.7, "completed_jobs": 176},
    {"name": "Zane Hensley", "email": "zh66@rice.edu", "phone": "4087221995", "skills": ["roofing", "gutters", "waterproofing"], "hourly_rate": 80.0, "location": "Georgetown, TX", "rating": 4.4, "completed_jobs": 93},
    {"name": "Prad Chebolu", "email": "pc65@rice.edu", "phone": "3467196530", "skills": ["cleaning", "pressure washing", "window cleaning"], "hourly_rate": 40.0, "location": "Austin, TX", "rating": 4.9, "completed_jobs": 312},
    {"name": "Zane Hensley", "email": "zh66@rice.edu", "phone": "4087221995", "skills": ["concrete", "foundations", "stamped concrete"], "hourly_rate": 90.0, "location": "Leander, TX", "rating": 4.5, "completed_jobs": 108},
    {"name": "Prad Chebolu", "email": "pc65@rice.edu", "phone": "3467196530", "skills": ["electrical", "smart home", "solar"], "hourly_rate": 110.0, "location": "Austin, TX", "rating": 4.8, "completed_jobs": 79},
    {"name": "Zane Hensley", "email": "zh66@rice.edu", "phone": "4087221995", "skills": ["plumbing", "drain cleaning", "bathroom remodel"], "hourly_rate": 80.0, "location": "Austin, TX", "rating": 4.2, "completed_jobs": 55},
    {"name": "Prad Chebolu", "email": "pc65@rice.edu", "phone": "3467196530", "skills": ["carpentry", "cabinetry", "custom millwork"], "hourly_rate": 95.0, "location": "Austin, TX", "rating": 4.9, "completed_jobs": 203},
    {"name": "Zane Hensley", "email": "zh66@rice.edu", "phone": "4087221995", "skills": ["landscaping", "tree trimming", "lawn care"], "hourly_rate": 45.0, "location": "Kyle, TX", "rating": 4.1, "completed_jobs": 287},
    {"name": "Prad Chebolu", "email": "pc65@rice.edu", "phone": "3467196530", "skills": ["hvac", "mini-split", "air quality"], "hourly_rate": 100.0, "location": "Buda, TX", "rating": 4.7, "completed_jobs": 134},
    {"name": "Zane Hensley", "email": "zh66@rice.edu", "phone": "4087221995", "skills": ["painting", "stucco", "exterior coatings"], "hourly_rate": 55.0, "location": "Austin, TX", "rating": 4.4, "completed_jobs": 91},
    {"name": "Prad Chebolu", "email": "pc65@rice.edu", "phone": "3467196530", "skills": ["tiling", "mosaic", "bathroom remodel"], "hourly_rate": 75.0, "location": "Round Rock, TX", "rating": 4.6, "completed_jobs": 147},
    {"name": "Zane Hensley", "email": "zh66@rice.edu", "phone": "4087221995", "skills": ["roofing", "shingles", "flat roof"], "hourly_rate": 75.0, "location": "Austin, TX", "rating": 4.3, "completed_jobs": 68},
    {"name": "Prad Chebolu", "email": "pc65@rice.edu", "phone": "3467196530", "skills": ["cleaning", "janitorial", "post-construction cleanup"], "hourly_rate": 38.0, "location": "Austin, TX", "rating": 4.8, "completed_jobs": 421},
    {"name": "Zane Hensley", "email": "zh66@rice.edu", "phone": "4087221995", "skills": ["concrete", "steel framing", "structural"], "hourly_rate": 105.0, "location": "Austin, TX", "rating": 4.6, "completed_jobs": 62},
]

SAMPLE_JOBS = [
    {
        "title": "Electrical Panel Upgrade — Westlake Home",
        "description": "Upgrade 100A panel to 200A, add 4 new circuits for EV charger and kitchen remodel. Home built in 1985.",
        "required_skills": ["electrical", "panel upgrades"],
        "location": "Austin, TX",
        "status": "pending",
        "budget": 3200.0,
        "priority": "high",
    },
    {
        "title": "Master Bath Plumbing Rough-In",
        "description": "Rough-in plumbing for new master bathroom addition. Includes 2 sinks, walk-in shower, soaking tub, and toilet.",
        "required_skills": ["plumbing", "bathroom remodel"],
        "location": "Austin, TX",
        "status": "pending",
        "budget": 4500.0,
        "priority": "medium",
    },
    {
        "title": "Commercial Landscaping — Office Park",
        "description": "Install new irrigation system and hardscaping for 2-acre commercial property. Deadline is end of month.",
        "required_skills": ["landscaping", "irrigation", "hardscaping"],
        "location": "Cedar Park, TX",
        "status": "pending",
        "budget": 12000.0,
        "priority": "high",
    },
    {
        "title": "HVAC System Replacement",
        "description": "Replace aging 5-ton HVAC system with new high-efficiency unit. Includes ductwork inspection and sealing.",
        "required_skills": ["hvac", "ductwork"],
        "location": "Austin, TX",
        "status": "pending",
        "budget": 8500.0,
        "priority": "critical",
    },
    {
        "title": "Interior Painting — 3BR Rental Property",
        "description": "Full interior repaint of 3-bedroom rental unit between tenants. Ceilings, walls, trim. Needs to be done within 5 days.",
        "required_skills": ["painting", "finishing"],
        "location": "Pflugerville, TX",
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
    # Fetch first few subs to assign
    from sqlalchemy import select as _select
    sub_result = await session.execute(_select(Subcontractor).limit(4))
    demo_subs = sub_result.scalars().all()

    overdue_jobs = [
        {
            "title": "Drywall & Tape — Oakview Remodel",
            "description": "Hang, tape, and finish drywall in master bedroom addition. 3 coats required.",
            "required_skills": ["carpentry", "drywall"],
            "location": "Austin, TX",
            "status": "in_progress",
            "budget": 2800.0,
            "priority": "high",
        },
        {
            "title": "Bathroom Tile Install — Riverside Condo",
            "description": "Install floor and shower tile in primary bath, including waterproofing membrane.",
            "required_skills": ["tiling", "waterproofing"],
            "location": "Austin, TX",
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
            # Add a schedule entry for this overdue job
            sched = Schedule(
                id=str(uuid.uuid4()),
                job_id=job.id,
                subcontractor_id=sub.id,
                scheduled_start=overdue_start.isoformat() + "T08:00:00",
                scheduled_end=overdue_end.isoformat() + "T17:00:00",
                notes="Overdue — no check-in received.",
            )
            session.add(sched)

            # Add a prior outbound message for context
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

    # --- Demo: a new lead that came in overnight ---
    demo_lead = Lead(
        id=str(uuid.uuid4()),
        name="Rachel Torres",
        email="rachel.t@gmail.com",
        phone="512-555-0192",
        message="Hi, I'm looking to renovate my kitchen — new cabinets, countertops, and tile backsplash. My house is in South Austin, about 180 sq ft kitchen. Would love to get a quote this week if possible. Budget is around $25k.",
        status="new",
        ai_summary="Homeowner seeking full kitchen renovation (cabinets, countertops, tile) in South Austin. ~180 sq ft, $25k budget. Interested in a quote this week — high-intent, time-sensitive lead.",
        auto_reply_sent=False,
    )
    session.add(demo_lead)

    await session.commit()
    print("✓ Database seeded with 20 subs, 5 pending jobs, 2 overdue jobs, and 1 demo lead.")
