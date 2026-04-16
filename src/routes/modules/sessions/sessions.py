"""
src.routes.modules.sessions.sessions.py

Project: WEV (OCPI+ Server)
Author: Oleg Kleiman
Date: Feb, 2026

"""

import logging
import sys
from pydantic import BaseModel
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from sse_starlette.sse import EventSourceResponse
from enum import Enum
from datetime import datetime, timezone
import uuid
import os
import json
import asyncio
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from src.models.pydantic.models import SessionUpdate
from src.models.ocpi.models_ocpi import OCPISession, SessionStatus, SessionDetailsResponse, OCPIAuthMethod, OCPIResponse
from src.models.sqlalchemy.models import DbSessionModel, DbSessionsUpdatesModel
from src.models.pydantic.models import TargetConnector, TargetLocation

from src.database import get_db

from src.dependencies import get_pubsub, get_session_service, get_locations_service, get_tariff_service

logger = logging.getLogger(__name__)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger.setLevel(LOG_LEVEL)
console_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(console_handler)

router = APIRouter(prefix="/sessions", tags=["Sessions"])
api_router = APIRouter(prefix="/sessions", tags=["Sessions"])

# SSE endpoint for real-time session updates
@api_router.get("/updates/{session_request_id}", tags=["Sessions"],
            description="SSE endpoint for real-time session updates.")
async def session_updates(request: Request, 
                          session_request_id: str, 
                          pubsub = Depends(get_pubsub)):

    queue = await pubsub.subscribe(session_request_id)

    async def event_generator():

        # Flush headers immediately so client onopen fires without waiting for first message
        yield {"comment": f"ping - {datetime.now(timezone.utc).isoformat()}"}

        while True:

            try:
                
                if await request.is_disconnected():
                    print(f"Session {session_request_id} disconnected")
                    pubsub.unsubscribe(session_request_id, queue) 
                    break

                # Every client is waiting on the SAME queue
                session_data = await queue.get()
                yield {
                    "event": "success", # SSE usually needs an event name
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

@router.post("/", tags=["Sessions"],
             response_model=None,
             description="CPO notifies the eMSP that a new Session has started.")
async def create_session(
        session: OCPISession,   
        session_service = Depends(get_session_service),
        db: AsyncSession = Depends(get_db),
        pubsub = Depends(get_pubsub)
    ) -> OCPIResponse:

    # Note: Assuming session.location is not None and has at least one EVSE/Connector
    # as per OCPI validation usually handled by Pydantic model
    location_id = session.location.id
    evse_id = session.location.evses[0].uid
    connector_id = session.location.evses[0].connectors[0].id

    try:
        request_id = await session_service.get_request_id(location_id, evse_id, connector_id)
        # Accociate this request_id with session.id
        await session_service.set_session_id(request_id, session.id)
        
        await session_service.save_session(session)
        session_model: SessionUpdate = await session_service.create_and_save_session_update(session, request_id)

        # Broadcast to anyone listening for this specific session ID
        await pubsub.publish(request_id, session_model)

    except Exception as e:
        logging.error(f"Error in create_session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return OCPIResponse(
        data=None,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )

@router.put("/{session_id}", tags=["Sessions"],
            description="CPO notifies the eMSP that a Session has updated.")
async def update_session(
        session: OCPISession,
        session_service = Depends(get_session_service),
        location_service = Depends(get_locations_service),
        tariff_service = Depends(get_tariff_service),
        db: AsyncSession = Depends(get_db),
        pubsub = Depends(get_pubsub)
    ) -> OCPIResponse:

    location_id = session.location.id
    evse_id = session.location.evses[0].uid
    connector_id = session.location.evses[0].connectors[0].id

    try:

        # Interpret PUT called to updated the EXISTING session
        # as POST called to create NEW session (following WEVO approach)
        session_id = await session_service.get_session_id_by_location(location_id, evse_id, connector_id)
        if not session_id:
            return await create_session(session, session_service, db, pubsub)
        else:    
            request_id = await session_service.get_request_id(location_id, evse_id, connector_id)

            session_id = session.id
            session_update: SessionUpdate = await session_service.create_and_save_session_update(session, request_id)

            # Broadcast to anyone listening for this specific session ID
            await pubsub.publish(request_id, session_update)

            location = session.location
            topic_id = f"{location_id}:{evse_id}"

            location_model: TargetLocation = await location_service.location_data_to_model(location, 
                                                                                           session, 
                                                                                           tariff_service)
            location_model.timestamp = session.last_updated

            await pubsub.publish(topic_id, location_model)     

    except Exception as e:
        logging.error(f"Error in update_session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return OCPIResponse(
        data=None,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    
# This endpoint is called by CPO by well-known URL defined in OCPI protocol
@router.get("/{session_request_id}", tags=["Sessions"],
            description="Returns the details of the session.")
async def get_session(
    session_request_id: str,
    session_service = Depends(get_session_service),
    db: AsyncSession = Depends(get_db)) -> SessionDetailsResponse:

    try:
        session_id = await session_service.get_session_id_by_request_id(session_request_id)
        if session_id is None:
            raise HTTPException(status_code=404, detail=f"Session Not Found Request id '{session_request_id}'")

        # SELECT * FROM public.ocpi_sessions s
        # JOIN ocpi_sessions_updates u
        # ON s.session_id = u.session_id
        # WHERE s.session_id = '<session_id>'
        # ORDER BY u.updated_at DESC
        # LIMIT 1

        stmt = (
            select(DbSessionsUpdatesModel, DbSessionModel.last_updated)
            .select_from(DbSessionModel)
            .join(DbSessionsUpdatesModel, DbSessionModel.session_id == DbSessionsUpdatesModel.session_id)
            .where(DbSessionModel.session_id == session_id)
            .order_by(DbSessionsUpdatesModel.updated_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.one_or_none()

        if not row:
            raise HTTPException(status_code=404, detail=f"Session Request id '{session_request_id}' not found")

        session, created_at = row  # created_at maps to DbSessionModel.last_updated (DB column "created_at")

        diff = datetime.now(timezone.utc) - session.updated_at
        total_seconds = int(diff.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        return SessionDetailsResponse(
            id=session.session_id,
            status = SessionStatus(session.status),
            delivered_kwh = session.kwh,
            total_cost = f"{session.total_cost}",
            duration = f"{hours:02}:{minutes:02}",
            start_datetime=created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))