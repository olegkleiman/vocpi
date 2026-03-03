from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Request, HTTPException

import httpx
import http.client
import json
import os
import logging

from ....router import router
from ....database import get_db, get_partner
from .models import CommandResponseWrapper, StartSessionPayload
from ..tokens.token_payload import TokenPayload

rfid_token_file_path = os.getenv("RFID_FAKE_TOKEN_FILE_PATH")
CALLBACK_BASE_URL = os.getenv("CALLBACK_BASE_URL")
logger = logging.getLogger(__name__)

@router.post("/commands/start_session", tags=["commands"],
            description="Sends a START_SESSION command to the CPO.",
            response_model=CommandResponseWrapper)
async def start_session(
    payload: StartSessionPayload,
    request: Request,
    db: AsyncSession = Depends(get_db)):

    try:
        partner_data = await get_partner(db, payload.location_id, payload.evse_uid)
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
            jsonResponse: CommandResponseWrapper = response.json()
            logger.debug(json.dumps(jsonResponse))
            return jsonResponse
        
    except httpx.HTTPStatusError as e:
        await e.response.aread()
        detail = e.response.text or e.response.reason_phrase or http.client.responses.get(e.response.status_code, "Unknown Error")
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from CPO API: {detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send START_SESSION command: {e}")
    
