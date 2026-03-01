from ....router import router
from pydantic import BaseModel
from typing import Optional
from fastapi import Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from sse_starlette.sse import EventSourceResponse
from enum import Enum
from datetime import datetime, timezone
import uuid
import os
import json
from collections import defaultdict
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import relationship, sessionmaker, DeclarativeBase, selectinload, Mapped, mapped_column
from sqlalchemy import select, Table, MetaData, Column, String, DateTime, Boolean

import sqlalchemy as sa

from ....database import get_db
from ....models import Token, Partner, TokenAuthorization, OCPISession

from ....dependencies import get_pubsub

class SessionRequest(BaseModel):
    id: str = str(uuid.uuid4())
    location_id: Optional[str] = None
    evse_uid: Optional[str] = None
    connector_id: Optional[str] = None
    kwh: float = 0.0

class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"

class SessionUpdateRequest(BaseModel):
    id: Optional[str] = None
    location_id: Optional[str] = None
    kwh: float = 0.0
    delivered_kwh: float = 0.0
    current_cost: float = 0.0
    status: SessionStatus = SessionStatus.ENDED

class SessionResponse(BaseModel):
    id: str
    status: SessionStatus

class SessionDetailsResponse(BaseModel):
    id: str
    status: SessionStatus
    kwh: float = 0.0
    delivered_kwh: float = 0.0
    current_cost: float = 0.0    
    duration: datetime

@router.get("/sessions/updates/{session_id}", tags=["sessions"],
            description="SSE endpoint for real-time session updates.")
async def session_updates(request: Request, 
                          session_id: str, 
                          pubsub = Depends(get_pubsub)):

    queue = await pubsub.subscribe(session_id)

    async def event_generator():

        while True:

            if await request.is_disconnected():
                print(f"Session {session_id} disconnected")
                await pubsub.unsubscribe(session_id, queue) 
                break

            # Every client is waiting on the SAME queue
            session_data = await queue.get()
            yield {
                "event": "update", # SSE usually needs an event name
                "id": str(uuid.uuid4()), # Unique ID for each event
                "data" :json.dumps(jsonable_encoder(session_data)),
            }

    return EventSourceResponse(event_generator())

@router.post("/sessions", tags=["sessions"],
             description="CPO notifies the eMSP that a Session has started.")
async def create_session(
        request: SessionRequest,
        db: AsyncSession = Depends(get_db),
        pubsub = Depends(get_pubsub)
    ) -> SessionResponse:

    now = datetime.now(timezone.utc)

    partner_id = os.getenv("DEFAULT_PARTNER_ID", "c3c3c6a6-5f1a-4f6d-bc8b-6b6f4b1e8d90")

    session = OCPISession(
        id=request.id,
        start_date_time=now,
        kwh=request.kwh,
        auth_id=request.location_id or "unknown",
        auth_method="AUTH_REQUEST",
        location_id=request.location_id or "unknown",
        evse_uid=request.evse_uid or "unknown",
        connector_id=request.connector_id or "unknown",
        currency="ILS",
        status=SessionStatus.ACTIVE.value,
        last_updated=now,
        partner_id=partner_id
        )
    # Broadcast to anyone listening for this specific ID
    await pubsub.publish(request.id, session)

    # db.add(session)
    # await db.commit()

    return SessionResponse(id=session.id, status=SessionStatus.ACTIVE)

@router.put("/sessions/{session_id}", tags=["sessions"],
            description="CPO notifies the eMSP that a Session has updated.")
async def update_session(
        session_id: str,
        request: SessionUpdateRequest,
        db: AsyncSession = Depends(get_db),
        pubsub = Depends(get_pubsub)
    ) -> SessionResponse:

    # stmt = select(OCPISession).where(OCPISession.id == session_id)
    # result = await db.execute(stmt)
    # session = result.scalar_one_or_none()

    # if not session:
    #     return SessionResponse(id=session_id, status=SessionStatus.ENDED)

    session = OCPISession(
        id=session_id,
        kwh=request.kwh,
        # current_cost=request.current_cost,
        status = request.status.value,
        last_updated = datetime.now(timezone.utc)       
    )
       
    # Broadcast to anyone listening for this specific ID
    await pubsub.publish(request.id, session)

    # await db.commit()

    # duration = datetime.now(timezone.utc) - session.start_date_time
    # session.last_updated = datetime.now(timezone.utc)
    # await cache.hset(f"ocpi:session:{session_id}", 
    #            mapping={
    #                "status": session.status,
    #                "kwh": session.kwh,
    #                "delivered_kwh": session.delivered_kwh,
    #                "duration": str(duration),
    #                "last_updated": session.last_updated.isoformat()
    #            })

    # event = {
    #     "event": "SESSION_UPDATED",
    #     "session_id": session_id,
    #     "status": session.status,
    #     "kwh": session.kwh,
    #     "delivered_kwh": session.delivered_kwh,
    #     "duration": str(duration),
    #     "last_updated": session.last_updated.isoformat()
    # }           
    # await cache.publish("ocpi:session:updated", json.dumps(event))

    return SessionResponse(id=session.id, status=SessionStatus.ACTIVE)    


@router.get("/sessions/{session_id}", tags=["sessions"],
            description="Returns the details of the session.")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)) -> SessionDetailsResponse:

    stmt = select(OCPISession).where(OCPISession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        return SessionDetailsResponse(
            id=session_id, 
            status=SessionStatus.ENDED,
            kwh=0.0, 
            delivered_kwh=0.0,
            current_cost=0.0, 
            duration=datetime.now(timezone.utc)
        )

    duration = session.last_updated - session.start_date_time
    return SessionDetailsResponse(
        id=session.id, 
        status=SessionStatus(session.status),
        kwh=session.kwh,
        delivered_kwh=getattr(session, 'delivered_kwh', 0.0),
        current_cost=getattr(session, 'current_cost', 0.0),
        duration=session.start_date_time
    )
    
