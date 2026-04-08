from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func, desc
from datetime import datetime
from typing import List
import os
from dotenv import load_dotenv

from database import get_db, init_db, Session, Event
from models import SessionData, SessionResponse, EventResponse, AnalyticsResponse

load_dotenv()

app = FastAPI(
    title="AIMirror API",
    description="Backend API for AIMirror behavioral tracking system",
    version="1.0.0"
)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,chrome-extension://*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("🚀 Starting AIMirror Backend API...")
    init_db()
    print("✅ API ready to receive requests")

@app.get("/")
async def root():
    return {
        "message": "AIMirror API",
        "version": "1.0.0",
        "status": "running"
    }

@app.post("/api/events", status_code=201)
async def create_events(session_data: SessionData, db: DBSession = Depends(get_db)):
    try:
        existing_session = db.query(Session).filter(
            Session.session_id == session_data.session_id
        ).first()

        if existing_session:
            existing_session.end_time = datetime.fromisoformat(session_data.end_time.replace('Z', '+00:00'))
            existing_session.total_events = len(session_data.events)
            existing_session.total_watch_time = sum(event.watch_time for event in session_data.events)
        else:
            new_session = Session(
                session_id=session_data.session_id,
                start_time=datetime.fromisoformat(session_data.start_time.replace('Z', '+00:00')),
                end_time=datetime.fromisoformat(session_data.end_time.replace('Z', '+00:00')),
                total_events=len(session_data.events),
                total_watch_time=sum(event.watch_time for event in session_data.events)
            )
            db.add(new_session)

        for event_data in session_data.events:
            existing_event = db.query(Event).filter(
                Event.session_id == session_data.session_id,
                Event.reel_id == event_data.reel_id
            ).first()

            if not existing_event:
                new_event = Event(
                    session_id=session_data.session_id,
                    reel_id=event_data.reel_id,
                    username=event_data.username,
                    caption=event_data.caption,
                    liked=event_data.liked,
                    watch_time=event_data.watch_time,
                    replay_count=event_data.replay_count,
                    scroll_speed=event_data.scroll_speed,
                    timestamp=datetime.fromisoformat(event_data.timestamp.replace('Z', '+00:00'))
                )
                db.add(new_event)

        db.commit()

        return {
            "success": True,
            "message": f"Stored {len(session_data.events)} events for session {session_data.session_id}",
            "session_id": session_data.session_id,
            "events_count": len(session_data.events)
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to store events: {str(e)}")

@app.get("/api/sessions", response_model=List[SessionResponse])
async def get_sessions(
    limit: int = 50,
    offset: int = 0,
    db: DBSession = Depends(get_db)
):
    sessions = db.query(Session).order_by(desc(Session.created_at)).offset(offset).limit(limit).all()
    return sessions

@app.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.get("/api/sessions/{session_id}/events", response_model=List[EventResponse])
async def get_session_events(session_id: str, db: DBSession = Depends(get_db)):
    events = db.query(Event).filter(Event.session_id == session_id).order_by(Event.timestamp).all()
    return events

@app.get("/api/events", response_model=List[EventResponse])
async def get_events(
    limit: int = 100,
    offset: int = 0,
    db: DBSession = Depends(get_db)
):
    events = db.query(Event).order_by(desc(Event.timestamp)).offset(offset).limit(limit).all()
    return events

@app.get("/api/analytics", response_model=AnalyticsResponse)
async def get_analytics(db: DBSession = Depends(get_db)):
    total_sessions = db.query(func.count(Session.id)).scalar() or 0
    total_events = db.query(func.count(Event.id)).scalar() or 0
    
    total_watch_time = db.query(func.sum(Event.watch_time)).scalar() or 0.0
    avg_watch_time_per_reel = (total_watch_time / total_events) if total_events > 0 else 0.0
    avg_watch_time_per_session = (total_watch_time / total_sessions) if total_sessions > 0 else 0.0
    
    liked_count = db.query(func.count(Event.id)).filter(Event.liked == True).scalar() or 0
    like_ratio = (liked_count / total_events * 100) if total_events > 0 else 0.0
    
    avg_scroll_speed = db.query(func.avg(Event.scroll_speed)).scalar() or 0.0
    
    reels_per_session = (total_events / total_sessions) if total_sessions > 0 else 0.0
    
    most_watched_users = db.query(
        Event.username,
        func.count(Event.id).label('view_count'),
        func.sum(Event.watch_time).label('total_watch_time')
    ).group_by(Event.username).order_by(desc('total_watch_time')).limit(10).all()
    
    most_watched_users_list = [
        {
            "username": user[0],
            "view_count": user[1],
            "total_watch_time": float(user[2])
        }
        for user in most_watched_users
    ]
    
    total_replays = db.query(func.sum(Event.replay_count)).scalar() or 0
    
    return AnalyticsResponse(
        total_sessions=total_sessions,
        total_events=total_events,
        total_watch_time=round(total_watch_time, 2),
        avg_watch_time_per_reel=round(avg_watch_time_per_reel, 2),
        avg_watch_time_per_session=round(avg_watch_time_per_session, 2),
        like_ratio=round(like_ratio, 2),
        avg_scroll_speed=round(avg_scroll_speed, 2),
        reels_per_session=round(reels_per_session, 2),
        most_watched_users=most_watched_users_list,
        total_replays=total_replays
    )

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.query(Event).filter(Event.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    
    return {"success": True, "message": f"Session {session_id} deleted"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
