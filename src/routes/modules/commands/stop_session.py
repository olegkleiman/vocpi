from pydantic import BaseModel
from typing import Optional
from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from sqlalchemy import select
import http.client
import os

from ....router import router, api_router
from ....database import get_db
from ....dependencies import get_session_db_service
from ....models import CommandResponseWrapper, CommandResponseType, StopSessionPayload, FinishSesionPayload

CALLBACK_BASE_URL = os.getenv("CALLBACK_BASE_URL")

@api_router.post("/finish_session", tags=["Custom API"],
             status_code=status.HTTP_202_ACCEPTED,
            description="Ends the current session.")
async def finish_session(payload: FinishSesionPayload,
                         session_service = Depends(get_session_db_service)):
    try:
        session_id = await session_service.get_session_id(payload.session_request_id)
        if session_id is None:
            raise HTTPException(status_code=404, detail="Session not found")

        payload = StopSessionPayload(session_id=session_id)
        response: CommandResponseWrapper = await stop_session(payload = payload, session_service = session_service)
        if response.data.result != CommandResponseType.ACCEPTED:
            raise HTTPException(status_code=404)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to finish session: {e}")


@router.post("/commands/stop_session", tags=["Commands"],
            description="Sends a STOP_SESSION command to the CPO.",
            response_model=CommandResponseWrapper)
async def stop_session(
    payload: StopSessionPayload,
    session_service = Depends(get_session_db_service),
    db: AsyncSession = Depends(get_db)):

    try:
        if not CALLBACK_BASE_URL:
             raise HTTPException(status_code=500, detail="Configuration error: CALLBACK_BASE_URL not set")

        partner_data = await session_service.get_partner_from_session_id(payload.session_id)
        partner_base_url, token, version = partner_data

        headers = {
            "Authorization": f"Token {token}",
        }

        command_payload = {
            "response_url" : f"{CALLBACK_BASE_URL}/commands/callback/stop_session/",
            "session_id": payload.session_id
        }

        url = f"{partner_base_url}/receiver/{version}/commands/STOP_SESSION"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=command_payload, timeout=30.0)
            response.raise_for_status()
            json_response = response.json()
            return CommandResponseWrapper.model_validate(json_response)

    except httpx.HTTPStatusError as e:
        await e.response.aread()
        detail = e.response.text or e.response.reason_phrase or http.client.responses.get(e.response.status_code, "Unknown Error")
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from CPO API: {detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send STOP_SESSION command: {e}")

    