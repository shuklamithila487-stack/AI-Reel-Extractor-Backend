"""
Background tasks using Huey.
Exports task functions and Huey instance.
"""

from app.tasks.huey_config import huey, task, periodic_task

# Import all tasks to register them with Huey
from app.tasks import video_tasks, email_tasks

__all__ = [
    "huey",
    "task",
    "periodic_task",
    "video_tasks",
    "email_tasks",
]