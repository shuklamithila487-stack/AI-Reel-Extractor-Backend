#!/bin/bash
# start.sh

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Start Huey consumer in the background
echo "Starting Huey consumer..."
huey_consumer app.tasks.huey_config.huey --workers 2 &

# Start FastAPI application
echo "Starting FastAPI server..."
# Using gunicorn with uvicorn workers for production stability
gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT