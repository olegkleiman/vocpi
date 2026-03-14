from typing import Optional
from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

import http.client
import os

from ....router import router, api_router
from ....dependencies import get_session_service
from ....models.pydantic.models import CommandResponseType, StopSessionPayload, EndSessionPayload
from ....models.ocpi.models_ocpi import OCPIResponse

CALLBACK_BASE_URL = os.getenv("CALLBACK_BASE_URL")

@api_router.post("/end_session", tags=["Custom API"],
             status_code=status.HTTP_202_ACCEPTED,
            description="Ends the current session.")
async def end_session(payload: EndSessionPayload,
                     session_service = Depends(get_session_service)):
    try:
        session_id = await session_service.get_session_id(payload.session_id)
        if session_id is None:
            raise HTTPException(status_code=404, detail="Session not found")
   
        stop_payload = StopSessionPayload(session_id=session_id)
        response: OCPIResponse = await stop_session(payload = stop_payload, session_service = session_service)

        # Delete session from Db.
        # It is referenced by payload.session_id, but actually it is request_id as it was saved initially
        await session_service.delete_session(request_id = payload.session_id)

        return response
    except HTTPException:
        # Re-raise HTTPExceptions so FastAPI can handle them (404, 400, etc.)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to finish session: {e}")


@router.post("/commands/stop_session", tags=["Commands"],
            description="Sends a STOP_SESSION command to the CPO.",
            response_model=OCPIResponse)
async def stop_session(
    payload: StopSessionPayload,
    session_service = Depends(get_session_service)):

    try:
        if not CALLBACK_BASE_URL:
             raise HTTPException(status_code=500, detail="Configuration error: CALLBACK_BASE_URL not set")

        location_id, evse_id = await session_service.get_location_from_session_id(payload.session_id)
        partner_data = await session_service.get_partner(location_id, evse_id)
        if not partner_data:
            raise HTTPException(status_code=404, detail="Couldn't find partner for session")

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
            return OCPIResponse.model_validate(json_response)

    except httpx.HTTPStatusError as e:
        await e.response.aread()
        detail = e.response.text or e.response.reason_phrase or http.client.responses.get(e.response.status_code, "Unknown Error")
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from CPO API: {detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send STOP_SESSION command: {e}")

    