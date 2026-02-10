from ....router import router
from pydantic import BaseModel
from typing import Optional
from fastapi import Depends
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import relationship, sessionmaker, DeclarativeBase, Session, selectinload, Mapped, mapped_column
from sqlalchemy import select, Table, MetaData, Column, String, DateTime, Boolean
import httpx
from enum import Enum
import uuid

import redis
# from glide import GlideClient

from ....cache import get_redis

from ....database import get_db
from ....models import Token, Partner, TokenAuthorization

class TokenAuthorizeRequest(BaseModel):
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


@router.post("/tokens/{token_uid}/authorize", tags=["tokens"], 
             description="Do a 'real-time' authorization request to the eMSP system, validating if a Token might be used (at the optionally given Location).")
async def authorize_token(
    token_uid: str,
    request: TokenAuthorizeRequest,
    db: AsyncSession = Depends(get_db),
    cache: redis.Redis = Depends(get_redis)
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
                Partner.country_code == "IL",
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
                location_id=request.location_id,
                evse_uid=request.evse_uid,
                connector_id=request.connector_id,
                result=status.value,
                requested_at=requested_at
            )
            db.add(auth_record)
            await db.commit()
    
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{base_url}/ocpi/2.2.1/sessions", json={     
                    "location_id": request.location_id,
                    "evse_uid": request.evse_uid,
                    "connector_id": request.connector_id,
                    "kwh": 10.7
                })
                response.raise_for_status()
        else:
            status = AuthorizationStatus.NOT_FOUND

        return TokenAuthorizeResponse(status=status)
    
    except Exception as e:
        print(f"Authorization error: {e}")
        return TokenAuthorizeResponse(status=AuthorizationStatus.FAILED)
