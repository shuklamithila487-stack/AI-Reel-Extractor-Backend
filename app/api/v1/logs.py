from fastapi import APIRouter, HTTPException
import os

router = APIRouter()

@router.get("/videos/{video_id}")
def get_video_logs(video_id: str):
    """
    Get the logs for a specific video.
    """
    project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    log_file = os.path.join(project_dir, "logs", "videos", f"{video_id}.log")
    
    if not os.path.exists(log_file):
        raise HTTPException(status_code=404, detail="Logs not found for this video")
        
    with open(log_file, "r") as f:
        logs = f.readlines()
        
    import json
    parsed_logs = []
    for line in logs:
        try:
            parsed_logs.append(json.loads(line))
        except:
            parsed_logs.append({"raw": line})
            
    return {"video_id": video_id, "logs": parsed_logs}
