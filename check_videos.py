import sys
from app.db.session import SessionLocal
from app import models
from sqlalchemy import func
import logging

logging.basicConfig(level=logging.INFO)

db = SessionLocal()
try:
    print("------- Video Status Counts -------")
    counts = db.query(models.Video.status, func.count(models.Video.id)).group_by(models.Video.status).all()
    if not counts:
        print("No videos found.")
    for status, count in counts:
        print(f"  {status}: {count}")
    
    print("\n------- Recent 5 Videos -------")
    recent_videos = db.query(models.Video).order_by(models.Video.created_at.desc()).limit(5).all()
    for v in recent_videos:
        print(f"  ID: {v.id}, User: {v.user_id}, Status: {v.status}, Created: {v.created_at}")

except Exception as e:
    print(f"Error querying videos: {e}")
finally:
    db.close()
