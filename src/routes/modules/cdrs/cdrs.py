"""
cdrs.py

Author: Oleg Kleiman
Date: Feb, 2026

"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import select
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from ....database import get_db
from ....models.pydantic.models import CDRResponse
from ....models.ocpi.models_ocpi import OCPICDR, OCPIResponse, OCPIStatusCode

logger = logging.getLogger(__name__)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger.setLevel(LOG_LEVEL)
console_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(console_handler)

from ....dependencies import get_cdr_service, get_session_service

router = APIRouter()
api_router = APIRouter()

cdr_waiters: dict = {}

@api_router.get("/cdrs/updates/{session_id}", tags=["Custom API"], response_model=CDRResponse)
async def get_receipt(request: Request,
                  session_id: str, # Actually this is session_request_id
                  cdr_service = Depends(get_cdr_service),
                  db: AsyncSession = Depends(get_db)):
 
    http_version = request.scope.get("http_version")
    logging.debug(http_version)

    timeout = 10
    keep_alive = request.headers.get("keep-alive")
    if keep_alive:
        # "timeout=10, max=1000" → 5
        for part in keep_alive.split(","):
            key, _, value = part.strip().partition("=")
            if key.strip() == "timeout":
                timeout = int(value)

    receipt = await cdr_service.get_cdr(session_id=session_id, db=db)

    if receipt:
        return receipt

    event = asyncio.Event()
    cdr_waiters[session_id] = event

    try:
        # Wait for the event to be set, with a timeout.
        await asyncio.wait_for(event.wait(), timeout=timeout)
        # After waiting, try to get the receipt again.
        receipt = await cdr_service.get_cdr(session_id=session_id, db=db)

        if receipt:
            return receipt
        else:
            # This case can happen if the event was triggered but the CDR is still not in the DB.
            raise HTTPException(status_code=404, detail=f"CDR for session '{session_id}' not found after wait.")

    except asyncio.TimeoutError:
        # If the wait times out, return a 408 Request Timeout.
        raise HTTPException(status_code=408, detail=f"Request timed out waiting for CDR for session '{session_id}'.")
    
    finally:
        # Clean up the event from the dictionary.
        cdr_waiters.pop(session_id, None)

@router.post("/cdrs", tags=["CDRs"])
async def receive_cdr(cdr: OCPICDR,
                      cdr_service = Depends(get_cdr_service),
                      session_service = Depends(get_session_service)):

    session_id = cdr_service.cdr_id_to_session_id(cdr.id)
    session_request_id = await session_service.get_request_id_by_session_id(session_id)

    if session_request_id:

        await cdr_service.save_cdr(session_id, session_request_id, cdr)

        event = cdr_waiters.get(session_request_id)
        if event:
            logger.debug(f"Notifying waiter for session: {session_request_id}")
            event.set()

    response = OCPIResponse(
        status_code = OCPIStatusCode.SUCCESS,
        status_message="OK",
        data=None,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    return response
