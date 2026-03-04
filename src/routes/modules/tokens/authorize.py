from ....router import router
from pydantic import BaseModel
from typing import Optional
from fastapi import Depends
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
import httpx
from enum import Enum
import uuid
import logging

from ....database import get_db
from ....models import Token, TokenAuthorization, OCPIPartnerModel

class TokenAuthorizePayload(BaseModel):
    location_id: Optional[str] = None
    evse_uid: Optional[str] = None
    connector_id: Optional[str] = None

class AuthorizationStatus(str, Enum):
    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    NOT_FOUND = "NOT_FOUND"

class TokenAuthorizeResponse(BaseModel):
    status: AuthorizationStatus
    expiry_date: str | None = None
    location_id: str | None = None
    info: str | None = None


@router.post("/tokens/{token_uid}/authorize", tags=["Tokens"], 
             description="Do a 'real-time' authorization request to the eMSP system, validating if a Token might be used (at the optionally given Location).")
async def authorize_token(
    token_uid: str,
    payload: TokenAuthorizePayload,
    db: AsyncSession = Depends(get_db)
) -> TokenAuthorizeResponse:

    try:
        requested_at = datetime.now(timezone.utc)

        # cache_key = f"ocpi:token:{token_uid}"
        # if cache:
        #     cached = await cache.get(cache_key)
        #     if cached:
        #         return TokenAuthorizeResponse(status=AuthorizationStatus.ALLOWED)

        # fallback → DB
        stmt = (
            select(Token)
            .join(Token.partner)
            .where(
                Token.uid == token_uid,
                OCPIPartnerModel.country_code == "IL",
            )
            .options(selectinload(Token.partner))
        )

        result = await db.execute(
            stmt
        )
        token = result.scalar_one_or_none()
        
        status = AuthorizationStatus.BLOCKED 

        if token:
            base_url = token.partner.base_url

            status = AuthorizationStatus.ALLOWED
            # if cache:
                # await cache.set(cache_key, str(token.uid))
                # await cache.expire(cache_key, 60)
        
            auth_record = TokenAuthorization(
                id=str(uuid.uuid4()),
                token_uid=token.uid,
                location_id=payload.location_id,
                evse_uid=payload.evse_uid,
                connector_id=payload.connector_id,
                result=status.value,
                requested_at=requested_at
            )
            db.add(auth_record)
            await db.commit()
    
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{base_url}/ocpi/2.2.1/sessions", json={     
                    "location_id": payload.location_id,
                    "evse_uid": payload.evse_uid,
                    "connector_id": payload.connector_id,
                    "kwh": 10.7
                })
                response.raise_for_status()
        else:
            status = AuthorizationStatus.NOT_FOUND

        return TokenAuthorizeResponse(status=status)
    
    except Exception as e:
        logging.error(f"Authorization error: {e}")
        return TokenAuthorizeResponse(status=AuthorizationStatus.FAILED)
