# from fastapi import FastAPI

# from app.routes.issues import router as issues_router
# from app.routes.auth import router as auth_router
# from app.routes.health import router as health_router

# from app.middleware.timer import timing_middleware
# from fastapi.middleware.cors import CORSMiddleware

# app = FastAPI(
#     title="Issue Tracker API",
#     version="0.1.0",
#     description="A mini production-style API built with FastAPI",
# )

# app.middleware("http")(timing_middleware)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# app.include_router(auth_router)
# app.include_router(issues_router)
# app.include_router(health_router)


# # https://teladoc-poug.onrender.com/api/v1/issues/


# import uvicorn
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel, Field
# from typing import List
# from uuid import UUID, uuid4
# from datetime import datetime

# # Event schema
# class Event(BaseModel):
#     event_id: UUID = Field(default_factory=uuid4)
#     tenant_id: UUID
#     type: str  # "tokens" or "inference_seconds"
#     amount: int
#     timestamp: datetime

# class Events(BaseModel):
#     events: List[Event]

# app = FastAPI(debug=True)

# origins = [
#     "http://localhost:5173",
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # In-memory DB
# memory_db = {"events": []}

# @app.get("/events", response_model=Events)
# def get_events():
#     return Events(events=memory_db["events"])

# @app.post("/events", response_model=Event)
# def add_event(event: Event):
#     # Only use tenant_id, type, amount from client
#     new_event = Event(
#         tenant_id=event.tenant_id,
#         type=event.type,
#         amount=event.amount
#     )
#     memory_db["events"].append(new_event)
#     return new_event

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Literal
from uuid import UUID, uuid4
from datetime import datetime, timezone


# ----------- Models -----------

class EventCreate(BaseModel):
    tenant_id: UUID
    event_type: Literal["tokens", "inference_seconds"]
    amount: int = Field(gt=0)


class Event(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    event_type: Literal["tokens", "inference_seconds"]
    amount: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EventsResponse(BaseModel):
    events: List[Event]


# ----------- App Setup -----------

app = FastAPI(debug=True)

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (resets on restart)
memory_db = {"events": []}


# ----------- Legacy Endpoints (optional) -----------

@app.get("/events", response_model=EventsResponse)
def get_events():
    return {"events": memory_db["events"]}


@app.post("/events", response_model=Event)
def add_event(event: EventCreate):
    new_event = Event(
        tenant_id=event.tenant_id,
        event_type=event.event_type,
        amount=event.amount,
    )
    memory_db["events"].append(new_event)
    return new_event


# ----------- New v1 API -----------

@app.post("/v1/usage/events", response_model=Event, status_code=201)
def create_usage_event(event: EventCreate):
    """
    Record a usage event for a tenant.
    """
    new_event = Event(
        tenant_id=event.tenant_id,
        event_type=event.event_type,
        amount=event.amount,
    )

    memory_db["events"].append(new_event)

    print("Current events:", memory_db["events"])  # debug log

    return new_event


@app.get("/v1/usage/events", response_model=EventsResponse)
def list_usage_events():
    """
    List all usage events (simple version).
    """
    return {"events": memory_db["events"]}


# ----------- Run Server -----------

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)