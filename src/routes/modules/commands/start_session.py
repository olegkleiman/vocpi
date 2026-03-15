"""
src.routes.modules.commands.start_session.py

Project: WEV (OCPI+ Server)
Author: Oleg Kleiman
Date: Feb, 2026

"""
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Request, HTTPException

import httpx
import http.client
import json
import os
import logging
import secrets

from ....router import router, api_router
from ....dependencies import get_session_service
from ....models.pydantic.models import StartSessionPayload, BeginSessionResponse
from ....models.ocpi.models_ocpi import OCPIResponse
from ..tokens.token_payload import TokenPayload

rfid_token_file_path = os.getenv("RFID_FAKE_TOKEN_FILE_PATH")
CALLBACK_BASE_URL = os.getenv("CALLBACK_BASE_URL")
logger = logging.getLogger(__name__)

@api_router.post("/begin_session", tags=["Custom API"],
            description="Begins a new session with the CPO.",
            response_model = BeginSessionResponse)
async def begin_session(payload: StartSessionPayload,
                        session_service = Depends(get_session_service)):
    try:

        location_id = payload.location_id
        evse_id = payload.evse_uid
        connector_id = payload.connector_id

        request_id = await session_service.get_request_id(location_id, evse_id, connector_id)
        if not request_id:
             random_req_id = secrets.token_hex(8)
             request_id = random_req_id
             await session_service.save_session_request(random_req_id,
                                                location_id = payload.location_id,
                                                evse_id = payload.evse_uid,
                                                connector_id = payload.connector_id)
        
        payload = StartSessionPayload(location_id=location_id,
                                          evse_uid=evse_id,
                                          connector_id=connector_id)
        response = await start_session(payload = payload, session_service = session_service)
        return { "session_id":  request_id }

    except Exception as e:
        msg = f"Failed to begin session: {e}"
        logger.error(msg)
        raise HTTPException(status_code=500, detail=msg)

@router.post("/commands/start_session", tags=["Commands"],
            description="Sends a START_SESSION command to the CPO.",
            response_model=OCPIResponse)
async def start_session(
    payload: StartSessionPayload,
    session_service = Depends(get_session_service)):

    try:
        if not rfid_token_file_path:
            raise HTTPException(status_code=500, detail="Configuration error: RFID_FAKE_TOKEN_FILE_PATH not set")

        partner_data = await session_service.get_partner(payload.location_id, payload.evse_uid)
        partner_base_url, auth_token, version = partner_data

        headers = {
            "Authorization": f"Token {auth_token}"
        }

        rfid_token = TokenPayload.from_json_file(rfid_token_file_path)

        if not CALLBACK_BASE_URL:
             raise HTTPException(status_code=500, detail="Configuration error: CALLBACK_BASE_URL not set")

        command_payload = {
            "response_url": f"{CALLBACK_BASE_URL}/commands/callback/start_session/",
            "token": rfid_token.model_dump(),
            "location_id": payload.location_id,
            "evse_uid": payload.evse_uid,
            "connector_id": payload.connector_id,
        }

        url = f"{partner_base_url}/receiver/{version}/commands/START_SESSION"

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=command_payload, timeout=30.0)
            response.raise_for_status()
            jsonResponse: OCPIResponse = response.json()

            logger.debug(json.dumps(jsonResponse))
            return jsonResponse
        
    except httpx.HTTPStatusError as e:
        await e.response.aread()
        detail = e.response.text or e.response.reason_phrase or http.client.responses.get(e.response.status_code, "Unknown Error")
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from CPO API: {detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send START_SESSION command: {e}")
    
