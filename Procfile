web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
worker: huey_consumer app.tasks.huey_config.huey -w 2 -k thread
