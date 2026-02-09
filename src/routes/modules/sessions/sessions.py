from ....router import router
from pydantic import BaseModel
from typing import Optional
from fastapi import Depends
from enum import Enum
from datetime import datetime, timezone
import uuid
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import relationship, sessionmaker, DeclarativeBase, selectinload, Mapped, mapped_column
from sqlalchemy import select, Table, MetaData, Column, String, DateTime, Boolean

import sqlalchemy as sa

from ....database import get_db
from ....models import Token, Partner, TokenAuthorization, OCPISession
from ....cache import get_valkey, get_redis

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

@router.post("/sessions", tags=["sessions"],
             description="CPO notifies the eMSP that a Session has started.")
async def create_session(
    request: SessionRequest,
    db: AsyncSession = Depends(get_db)) -> SessionResponse:

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
    db.add(session)
    await db.commit()

    return SessionResponse(id=session.id, status=SessionStatus.ACTIVE)

@router.put("/sessions/{session_id}", tags=["sessions"],
            description="CPO notifies the eMSP that a Session has updated.")
async def update_session(
    session_id: str,
    request: SessionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    cache = Depends(get_redis)) -> SessionResponse:

    stmt = select(OCPISession).where(OCPISession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        return SessionResponse(id=session_id, status=SessionStatus.ENDED)

    session.kwh = request.kwh
    session.delivered_kwh = request.delivered_kwh
    session.status = request.status.value
    session.last_updated = datetime.now(timezone.utc)

    await db.commit()

    duration = datetime.now(timezone.utc) - session.start_date_time
    session.last_updated = datetime.now(timezone.utc)
    await cache.hset(f"ocpi:session:{session_id}", 
               mapping={
                   "status": session.status,
                   "kwh": session.kwh,
                   "delivered_kwh": session.delivered_kwh,
                   "duration": str(duration),
                   "last_updated": session.last_updated.isoformat()
               })

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
    
