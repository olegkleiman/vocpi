from ....router import router
from pydantic import BaseModel
from typing import Optional
from fastapi import Depends
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import relationship, sessionmaker, DeclarativeBase, Session, selectinload, Mapped, mapped_column
from sqlalchemy import select, Table, MetaData, Column, String, DateTime, Boolean
import os
from enum import Enum

import sqlalchemy as sa
from glide import GlideClient

from ....valkey import get_valkey

# r = redis.Redis(
#     host="my-redis.xxxxxx.0001.use1.cache.amazonaws.com",
#     port=6379,
#     password="YOUR_PASSWORD",  # если установлен
#     decode_responses=True      # возвращать строки, а не байты
# )


pg_password = os.getenv("PG_PASSWORD")
pg_username = os.getenv("PG_USERNAME")

DATABASE_URL = f"postgresql+asyncpg://{pg_username}:{pg_password}@voicp-instance.c2niqycso7s9.us-east-1.rds.amazonaws.com:5432/postgres"

engine = create_async_engine(DATABASE_URL)
# It's more like session factory, not a session itself. You need to call it to get a session instance.
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with SessionLocal() as session:
        yield session

class Base(DeclarativeBase):
    pass

class Partner(Base):
    __tablename__ = "ocpi_partners"

    # id = sa.Column(sa.UUID(as_uuid=True), primary_key=True)
    id: Mapped[sa.UUID] = sa.Column(primary_key=True)
    # country_code = sa.Column(sa.String(2), nullable=False)
    country_code : Mapped[str] = mapped_column(String(2))
    # party_id = sa.Column(sa.String(3), nullable=False)
    party_id : Mapped[str] = mapped_column(String(3))
    # role = sa.Column(sa.String(10), nullable=False)
    role : Mapped[str] = mapped_column(String(10))
    # base_url = sa.Column(sa.String, nullable=False)
    base_url : Mapped[str] = mapped_column(String)

    # tokens = relationship("Token", back_populates="partner")
    tokens: Mapped["Token"] = relationship(back_populates="partner")

    def __repr__(self):
        return f"Partner(id={self.id}, country_code={self.country_code}, party_id={self.party_id}, role={self.role}, base_url={self.base_url})"

class Token(Base):
    __tablename__ = "ocpi_tokens"

    # sa.Column(sa.String, primary_key=True)
    uid: Mapped[sa.UUID] = sa.Column(primary_key=True) # mapped_column(primary_key=True)
    partner_id : Mapped[sa.UUID] = mapped_column(sa.ForeignKey("ocpi_partners.id"))

    type = sa.Column(sa.String(20), nullable=False)
    contract_id = sa.Column(sa.String, nullable=False)
    issuer = sa.Column(sa.String, nullable=False)
    valid = sa.Column(sa.Boolean, nullable=False)
    whitelist = sa.Column(sa.String(20), nullable=False)
    # sa.Column(sa.DateTime, nullable=False)
    last_updated = Mapped[Optional[datetime]] 

    # partner = relationship("Partner", back_populates="tokens")
    partner: Mapped[list["Partner"]] = relationship(back_populates="tokens")


    def __repr__(self):
        return f"Token(uid={self.uid}, type={self.type}, contract_id={self.contract_id}, issuer={self.issuer}, valid={self.valid}, whitelist={self.whitelist}, last_updated={self.last_updated})"

class TokenAuthorization(Base):
    __tablename__ = "ocpi_token_authorizations"

    id: Mapped[sa.UUID] = sa.Column(primary_key=True, default=sa.text("gen_random_uuid()"))
    token_uid: Mapped[sa.UUID] = sa.Column(sa.ForeignKey("ocpi_tokens.uid"), nullable=False)
    location_id: Mapped[Optional[str]] = sa.Column(sa.String, nullable=True)
    evse_uid: Mapped[Optional[str]] = sa.Column(sa.String, nullable=True)
    connector_id: Mapped[Optional[str]] = sa.Column(sa.String, nullable=True)
    result: Mapped[str] = sa.Column(sa.String(20), nullable=False)
    requested_at: Mapped[datetime] = sa.Column(DateTime(timezone=True), nullable=False)

    def __repr__(self):
        return f"TokenAuthorization(id={self.id}, token_uid={self.token_uid}, location_id={self.location_id}, evse_uid={self.evse_uid}, connector_id={self.connector_id}, status={self.status}, requested_at={self.requested_at})"

class TokenAuthorizeRequest(BaseModel):
    location_id: Optional[str] = None
    evse_uid: Optional[str] = None
    connector_id: Optional[str] = None

class AuthorizationStatus(str, Enum):
    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"

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
    valkey: GlideClient = Depends(get_valkey)
) -> TokenAuthorizeResponse:

    try:
        requested_at = datetime.now(timezone.utc)

        cache_key = f"ocpi:token:{token_uid}"
        if valkey:
            cached = await valkey.get(cache_key)
            if cached:
                return TokenAuthorizeResponse(status=AuthorizationStatus.ALLOWED)

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
        base_url = token.partner.base_url
        
        status = AuthorizationStatus.BLOCKED 

        if token:
            status = AuthorizationStatus.ALLOWED
            if valkey:
                await valkey.set(cache_key, str(token.uid))
                await valkey.expire(cache_key, 60)
        
        auth_record = TokenAuthorization(
            token_uid=token.uid,
            location_id=request.location_id,
            evse_uid=request.evse_uid,
            connector_id=request.connector_id,
            result=status.value,
            requested_at=requested_at
        )
        db.add(auth_record)
        await db.commit()
        
        return TokenAuthorizeResponse(status=status)
    
    except Exception as e:
        
        return TokenAuthorizeResponse(status=AuthorizationStatus.FAILED)

    finally:
        await db.close()
