from pydantic import BaseModel
from typing import Optional
from fastapi import Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from sqlalchemy import select
import http.client
import os

from ....router import router
from ....database import get_db, get_partner
from ....models import CommandResponseWrapper, StopSessionPayload
from ....models import OCPISessionModel, OCPIPartnerModel

CALLBACK_BASE_URL = os.getenv("CALLBACK_BASE_URL")

@router.post("/commands/stop_session", tags=["commands"],
            description="Sends a STOP_SESSION command to the CPO.",
            response_model=CommandResponseWrapper)
async def stop_session(
    payload: StopSessionPayload,
    request: Request,
    db: AsyncSession = Depends(get_db)):

    try:
        if not CALLBACK_BASE_URL:
             raise HTTPException(status_code=500, detail="Configuration error: CALLBACK_BASE_URL not set")

        stmt = (
            select(
                OCPIPartnerModel.base_url, 
                OCPIPartnerModel.token, 
                OCPIPartnerModel.version
            )
            # Start from Sessions, join Partners
            .select_from(OCPISessionModel) 
            .join(OCPIPartnerModel, OCPISessionModel.party_id == OCPIPartnerModel.party_id)
            .where(OCPISessionModel.session_id == payload.session_id)
        )
        result = await db.execute(stmt)
        partner_data = result.first()

        # partner_data = await get_partner(db, payload.session_id)
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
            responseWraper = response.json()
            responseWraper["status_code"] = response.status_code
            statusCode = responseWraper["status_code"]
            responseData = responseWraper["data"]
            responseResult = responseData["result"]
            if statusCode == 200 and responseResult == "ACCEPTED":
                # saveSessionHistory()
                print(f"save to history")
            
            return responseWraper
        

    except httpx.HTTPStatusError as e:
        await e.response.aread()
        detail = e.response.text or e.response.reason_phrase or http.client.responses.get(e.response.status_code, "Unknown Error")
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from CPO API: {detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send STOP_SESSION command: {e}")

    