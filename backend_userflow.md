# Backend User Flow and Architecture

This document describes the end-to-end workflow of the AI Reel Pipeline, detailing how a user interacts with the system and how the backend processes video data to extract structured information.

## Why is this useful?

The AI Reel Pipeline automates the tedious process of extracting structured data from unstructured video content (e.g., real estate walkthroughs).

1. **Efficiency**: Replaces hours of manual video watching and note-taking with automated processing. Ideally suited for high-volume content ingestion.
2. **Accuracy**: Computerized transcription and extraction reduce human error and fatigue, ensuring consistent data capture across thousands of videos.
3. **Structured Data**: Transforms raw media (MP4/MP3) into queryable, structured JSON data and database records, enabling powerful search, analytics, and integration with other systems (CRM, listings).
4. **Scalability**: The asynchronous architecture (Huey + Cloudinary) allows for parallel processing of multiple videos without blocking the user interface.
5. **Interactivity**: The "Human-in-the-Loop" design (Column Suggestion -> User Selection -> Extraction) ensures the AI focuses exactly on what the user needs, adapting to different video types dynamically.

---

## End-to-End Workflow Diagram

The following interactive chart illustrates the system architecture and data flow.
*(View this in VS Code or GitHub to interact with the diagram)*

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as FastAPI Backend
    participant DB as Database (Postgres)
    participant Cloud as Cloudinary
    participant Queue as Huey Task Queue
    participant AI as AI Services (Sarvam/LLM)

    Note over User, AI: Phase 1: Upload & Processing

    User->>API: 1. POST /videos/upload (Video File)
    activate API
    API->>Cloud: 2. Upload Video (Direct/Proxy)
    Cloud-->>API: 3. Return Video URL & Metadata
    API->>DB: 4. Create Video Record (status="pending")
    API->>Queue: 5. Enqueue 'process_video_pipeline'
    API-->>User: 6. Return Video Status (id, status="pending")
    deactivate API

    Note over Queue, AI: Async Background Processing

    Queue->>Queue: 7. Pick up Task
    Queue->>Cloud: 8. Download Video / Extract Audio
    Cloud-->>Queue: 9. Return Audio File (MP3)
    Queue->>AI: 10. Send Audio for Transcription (Sarvam AI)
    AI-->>Queue: 11. Return Transcript Text
    Queue->>DB: 12. Save Transcript
    Queue->>AI: 13. Analyze Transcript -> Suggest Columns (LLM)
    AI-->>Queue: 14. Return JSON Suggestions
    Queue->>DB: 15. Save Suggestions & Update Status ("awaiting_selection")
    
    Note over User, AI: Phase 2: User Interaction

    User->>API: 16. GET /videos/{id} (Poll Status)
    API-->>User: 17. Return Status "awaiting_selection" + Suggested Columns
    
    User->>API: 18. POST /extractions/extract (Selected Columns)
    activate API
    API->>DB: 19. Save Selected Columns
    API->>Queue: 20. Enqueue 'extract_data_task'
    API-->>User: 21. Return Status "extracting"
    deactivate API

    Note over Queue, AI: Phase 3: Data Extraction

    Queue->>Queue: 22. Pick up Extraction Task
    Queue->>DB: 23. Fetch Transcript & Columns
    Queue->>AI: 24. Extract specific data points (LLM)
    AI-->>Queue: 25. Return Structured JSON
    Queue->>DB: 26. Save Extracted Data & Update Status ("completed")

    Note over User, AI: Phase 4: Consumption

    User->>API: 27. GET /videos/{id} or /history
    API-->>User: 28. Return Final Extracted Data (JSON)
```

## detailed System Components

### 1. Frontend / User

- Initiates the upload.
- Periodically polls for status updates.
- Reviews AI suggestions and selects fields of interest.
- Consumes the final JSON output.

### 2. API Layer (FastAPI)

- Handles authentication and validation.
- Orchestrates the flow between User, Database, and Queue.
- Proxies huge file uploads to Cloudinary to keep the server lightweight.

### 3. Background Workers (Huey)

- **Critical Component**: Decouples heavy processing (transcription, LLM calls) from the user-facing API.
- Ensures the API remains responsive (sub-100ms response times) even when processing hour-long videos.
- Handles retries and failures gracefully.

### 4. AI Services

- **Sarvam AI**: Specialized for highly accurate transcription (Speech-to-Text), handling diverse accents and languages.
- **LLM (Claude/GPT)**: The "brain" that understands the context of the transcript to suggest relevant data fields and extract precise values based on user intent.
