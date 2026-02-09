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

class SessionRequest(BaseModel):
    location_id: Optional[str] = None
    evse_uid: Optional[str] = None
    connector_id: Optional[str] = None
    kwh: float = 0.0

class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"

class SessionResponse(BaseModel):
    id: str
    status: SessionStatus


@router.post("/sessions", tags=["sessions"],
             description="CPO notifies the eMSP that a Session has started.")
async def create_session(
    request: SessionRequest,
    db: AsyncSession = Depends(get_db)) -> SessionResponse:

    now = datetime.now(timezone.utc)

    partner_id = os.getenv("DEFAULT_PARTNER_ID", "c3c3c6a6-5f1a-4f6d-bc8b-6b6f4b1e8d90")
    
    session = OCPISession(
        id=str(uuid.uuid4()),
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
    
