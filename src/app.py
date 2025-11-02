"""
Persistent Activities API

Replaces the in-memory activities storage with a small SQLite DB using SQLModel.
This file wires endpoints to DB models found in `src/db.py` and seeds sample activities
on first run.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path
from typing import Dict

from .db import (
    create_db_and_tables,
    get_session,
    Activity,
    Signup,
)
from sqlmodel import select

app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities",
)

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=current_dir / "static"), name="static")


def seed_activities():
    sample = [
        {
            "name": "Chess Club",
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
        },
        {
            "name": "Programming Class",
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
        },
        {
            "name": "Gym Class",
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
        },
        {
            "name": "Soccer Team",
            "description": "Join the school soccer team and compete in matches",
            "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
            "max_participants": 22,
        },
        {
            "name": "Basketball Team",
            "description": "Practice and play basketball with the school team",
            "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 15,
        },
        {
            "name": "Art Club",
            "description": "Explore your creativity through painting and drawing",
            "schedule": "Thursdays, 3:30 PM - 5:00 PM",
            "max_participants": 15,
        },
        {
            "name": "Drama Club",
            "description": "Act, direct, and produce plays and performances",
            "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
            "max_participants": 20,
        },
        {
            "name": "Math Club",
            "description": "Solve challenging problems and participate in math competitions",
            "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
            "max_participants": 10,
        },
        {
            "name": "Debate Team",
            "description": "Develop public speaking and argumentation skills",
            "schedule": "Fridays, 4:00 PM - 5:30 PM",
            "max_participants": 12,
        },
    ]

    with get_session() as sess:
        q = sess.exec("SELECT count(*) FROM activity")
        try:
            count = q.one()
        except Exception:
            count = 0
        if not count:
            for a in sample:
                activity = Activity(**a)
                sess.add(activity)
            sess.commit()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    seed_activities()


def activity_to_dict(activity: Activity, session) -> Dict:
    participants = session.exec(
        "SELECT email FROM signup WHERE activity_id = :aid",
        params={"aid": activity.id},
    ).all()

    return {
        "description": activity.description,
        "schedule": activity.schedule,
        "max_participants": activity.max_participants,
        "participants": participants,
    }


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    with get_session() as sess:
        activities = sess.exec(select(Activity)).all()
        result = {a.name: activity_to_dict(a, sess) for a in activities}
        return result


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    with get_session() as sess:
        activity = sess.exec(select(Activity).where(Activity.name == activity_name)).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        # check if already signed up
        existing = sess.exec(
            select(Signup).where(Signup.activity_id == activity.id).where(Signup.email == email)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Student is already signed up")

        # check capacity
        current = sess.exec(select(Signup).where(Signup.activity_id == activity.id)).all()
        if len(current) >= activity.max_participants:
            raise HTTPException(status_code=400, detail="Activity is full")

        signup = Signup(activity_id=activity.id, email=email)
        sess.add(signup)
        sess.commit()
        return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    with get_session() as sess:
        activity = sess.exec(select(Activity).where(Activity.name == activity_name)).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        signup = sess.exec(
            select(Signup).where(Signup.activity_id == activity.id).where(Signup.email == email)
        ).first()
        if not signup:
            raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

        sess.delete(signup)
        sess.commit()
        return {"message": f"Unregistered {email} from {activity_name}"}
