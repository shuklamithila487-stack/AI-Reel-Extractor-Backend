import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models import Video
from app.tasks.video_tasks import process_video_pipeline

def retrigger_video(video_id):
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            print(f"Error: Video {video_id} not found.")
            return

        print(f"Retriggering processing for video: {video_id}")
        print(f"Current Status: {video.status}")
        
        # Reset status if it's failed or stuck
        if video.status in ["failed", "pending"]:
            video.status = "pending"
            db.commit()
            print("Status reset to pending.")

        # Manually call the task
        process_video_pipeline(video_id)
        print("Pipeline task queued.")
        
    except Exception as e:
        print(f"Failed to retrigger video: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 retrigger_video.py <video_id>")
    else:
        retrigger_video(sys.argv[1])
