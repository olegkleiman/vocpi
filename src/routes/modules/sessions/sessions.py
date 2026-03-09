import logging
import sys
from ....router import router
from pydantic import BaseModel
from typing import Optional
from fastapi import Depends, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from sse_starlette.sse import EventSourceResponse
from enum import Enum
from datetime import datetime, timezone
import uuid
import os
import json
from collections import defaultdict
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# import sqlalchemy as sa
from sqlalchemy import select

from ....database import get_db
from ....models import OCPISessionModel, OCPISessionsUpdatesModel

from ....dependencies import get_pubsub, get_session_service

logger = logging.getLogger(__name__)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger.setLevel(LOG_LEVEL)
console_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(console_handler)

class OCPISession(BaseModel):
    id: str = str(uuid.uuid4())
    location_id: Optional[str] = None
    evse_uid: Optional[str] = None
    connector_id: Optional[str] = None
    party_id: str
    kwh: float = 0.0
    total_cost: float = 0.0
    authorization_reference: Optional[str] = None
    currency: str = "ILS"
    status: str
    last_updated: datetime

class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED",
    INVALID = "INVALID",
    PENDING = "PENDING",
    RESERVATION = "RESERVATION"

class SessionResponse(BaseModel):
    id: str
    status: SessionStatus

class SessionDetailsResponse(BaseModel):
    id: str
    status: SessionStatus
    delivered_kwh: float = 0.0
    total_cost: str
    duration: str

@router.get("/sessions/updates/{session_request_id}", tags=["Sessions"],
            description="SSE endpoint for real-time session updates.")
async def session_updates(request: Request, 
                          session_request_id: str, 
                          pubsub = Depends(get_pubsub)):

    queue = await pubsub.subscribe(session_request_id)

    async def event_generator():

        while True:

            try:
                
                if await request.is_disconnected():
                    print(f"Session {session_request_id} disconnected")
                    await pubsub.unsubscribe(session_request_id, queue) 
                    break

                # Every client is waiting on the SAME queue
                session_data = await queue.get()
                yield {
                    "event": "update", # SSE usually needs an event name
                    "id": str(uuid.uuid4()), # Unique ID for each event
                    "data" :json.dumps(jsonable_encoder(session_data)),
                }

            except asyncio.TimeoutError:
                # Send a 'heartbeat' comment if no message arrived
                yield ": heartbeat\n\n"
            except Exception as e:
                logger.error(f"Error in SSE sessions loop for session '{session_request_id}': {e}")
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)})
                }                  

    return EventSourceResponse(event_generator())

@router.post("/sessions", tags=["Sessions"],
             response_model=None,
             description="CPO notifies the eMSP that a new Session has started.")
async def create_session(
        session: OCPISession,
        session_service = Depends(get_session_service),
        db: AsyncSession = Depends(get_db),
        pubsub = Depends(get_pubsub)
    ) -> SessionResponse:

    now = datetime.now(timezone.utc)

    request_id = await session_service.get_request_id(session.location_id, session.evse_uid, session.connector_id)
    # Accociate this request_id with session.id
    await session_service.set_session_id(request_id, session.id)

    sessionModel = OCPISessionModel(
        id = str(uuid.uuid4()), 
        session_id = session.id,
        # start_date_time = now,
        # kwh = session.kwh,
        # total_cost = session.total_cost,
        auth_id = session.authorization_reference or "unknown",
        auth_method="AUTH_REQUEST",
        location_id = session.location_id or "unknown",
        evse_uid = session.evse_uid or "unknown",
        connector_id=session.connector_id or "unknown",
        currency= session.currency,
        party_id = session.party_id,
        status = SessionStatus.ACTIVE.value,
        last_updated=now
    )

    # Broadcast to anyone listening for this specific session ID
    await pubsub.publish(request_id, sessionModel)

    db.add(sessionModel)
    await db.commit()

    return SessionResponse(id=str(sessionModel.id), status=SessionStatus.ACTIVE)

@router.put("/sessions/{session_id}", tags=["Sessions"],
            description="CPO notifies the eMSP that a Session has updated.")
async def update_session(
        session: OCPISession,
        session_service = Depends(get_session_service),
        db: AsyncSession = Depends(get_db),
        pubsub = Depends(get_pubsub)
    ) -> SessionResponse:

    request_id = await session_service.get_request_id(session.location_id, session.evse_uid, session.connector_id)

    session_id = session.id
    sessionModel = OCPISessionsUpdatesModel(
        id = str(uuid.uuid4()),
        session_id = session_id,
        kwh = session.kwh,
        total_cost = session.total_cost,
        updated_at = session.last_updated,
        status = session.status
    )
       
    # Broadcast to anyone listening for this specific ID
    await pubsub.publish(request_id, sessionModel)

    db.add(sessionModel)
    await db.commit()

    return SessionResponse(id=session_id, 
                           status=SessionStatus.ACTIVE)    

@router.get("/sessions/{session_request_id}", tags=["Sessions"],
            description="Returns the details of the session.")
async def get_session(
    session_request_id: str,
    session_service = Depends(get_session_service),
    db: AsyncSession = Depends(get_db)) -> SessionDetailsResponse:

    session_id = await session_service.get_session_id(session_request_id)

    # SELECT * FROM public.ocpi_sessions s
    # JOIN ocpi_sessions_updates u
    # ON s.session_id = u.session_id
    # WHERE s.session_id = '<session_id>'
    # ORDER BY u.updated_at DESC
    # LIMIT 1

    stmt = (
        select(OCPISessionsUpdatesModel)
        .select_from(OCPISessionModel)
        .join(OCPISessionsUpdatesModel, OCPISessionModel.session_id == OCPISessionsUpdatesModel.session_id)
        .where(OCPISessionModel.session_id == session_id)
        .order_by(OCPISessionsUpdatesModel.updated_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    # session: OCPISessionsUpdatesModel = result.scalar_one_or_none()
    session = result.scalar_one_or_none()
 
    if not session:
        raise HTTPException(status_code=404, detail=f"Session with request id '{session_request_id}' not found")

    diff = datetime.now(timezone.utc) - session.updated_at
    total_seconds = int(diff.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    return SessionDetailsResponse(
        id=session.session_id, 
        status = SessionStatus(session.status),
        delivered_kwh = session.kwh,
        total_cost = f"{session.total_cost}", 
        duration = f"{hours:02}:{minutes:02}"
    )
