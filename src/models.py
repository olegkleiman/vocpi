from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy import String, Column, DateTime, Boolean, UUID, Text
from datetime import datetime
from typing import Optional
import uuid
from enum import Enum
import sqlalchemy as sa
from sqlalchemy.sql import func

from pydantic import BaseModel

#== Pydantic models

class CommandResponseType(str, Enum):
    ACCEPTED = "ACCEPTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    REJECTED = "REJECTED"
    UNKNOWN_SESSION = "UNKNOWN_SESSION"

class CommandResponse(BaseModel):
    result: CommandResponseType

class CommandResponseWrapper(BaseModel):
    status_code: int
    status_message: str
    timestamp: str
    data: Optional[CommandResponse] = None

class StartSessionPayload(BaseModel):
    location_id: Optional[str] = None
    evse_uid: Optional[str] = None
    connector_id: Optional[str] = None

class StopSessionPayload(BaseModel):
    session_id: str    

class FinishSesionPayload(BaseModel):
    session_request_id: str

class BeginSessionResponse(BaseModel):
    request_id: str


#== SqlAlchemy models

class Base(DeclarativeBase):
    pass

class TerminalConfiguration(Base):
    __tablename__ = "ocpi_terminals"
        
    # Primary key using UUID
    id: Mapped[sa.UUID] = sa.Column(primary_key=True)

    serial_number: Mapped[str] = mapped_column(String)
    location_id = sa.Column(sa.UUID, sa.ForeignKey("ocpi_locations.id"), nullable=False)
    evse_id = sa.Column(sa.UUID, sa.ForeignKey("ocpi_evse.id"), nullable=False)
    terminal_id = mapped_column(String)
    user_name = mapped_column(String)
    user_password = mapped_column(String)

class OCPILocation(Base):
    __tablename__ = "ocpi_locations"

    id: Mapped[sa.UUID] = sa.Column(primary_key=True)
    location_id: Mapped[str] = mapped_column(String, unique=True)
    partner_id = sa.Column(sa.UUID, sa.ForeignKey("ocpi_partners.id"), nullable=False)
    description: Mapped[str] = mapped_column(String)
    address: Mapped[str] = mapped_column(String)

class EVSE(Base):
    __tablename__ = "ocpi_evses"

    id: Mapped[sa.UUID] = sa.Column(primary_key=True)
    evse_id: Mapped[str] = mapped_column(String, unique=True)
    location_id: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)

class OCPIPartnerModel(Base):
    __tablename__ = "ocpi_partners"
    
    id: Mapped[sa.UUID] = sa.Column(primary_key=True)
    country_code: Mapped[str] = mapped_column(String(2))
    party_id: Mapped[str] = mapped_column(String(3))
    role: Mapped[str] = mapped_column(String(10))
    base_url: Mapped[str] = mapped_column(String)
    token: Mapped[str] = mapped_column(String)
    version: Mapped[str] = mapped_column(String)
    

class Token(Base):
    __tablename__ = "ocpi_tokens"

    uid: Mapped[sa.UUID] = sa.Column(primary_key=True)
    partner_id: Mapped[sa.UUID] = mapped_column(sa.ForeignKey("ocpi_partners.id"))
    type = sa.Column(sa.String(20), nullable=False)
    contract_id = sa.Column(sa.String, nullable=False)
    issuer = sa.Column(sa.String, nullable=False)
    valid = sa.Column(sa.Boolean, nullable=False)
    whitelist = sa.Column(sa.String(20), nullable=False)
    last_updated = Mapped[Optional[datetime]]
    # partner: Mapped[list["Partner"]] = relationship(back_populates="tokens")

class TokenAuthorization(Base):
    __tablename__ = "ocpi_token_authorizations"

    id: Mapped[sa.UUID] = sa.Column(primary_key=True, server_default=sa.text("gen_random_uuid()"))
    token_uid: Mapped[sa.UUID] = sa.Column(sa.ForeignKey("ocpi_tokens.uid"), nullable=False)
    location_id: Mapped[Optional[str]] = sa.Column(sa.String, nullable=True)
    evse_uid: Mapped[Optional[str]] = sa.Column(sa.String, nullable=True)
    connector_id: Mapped[Optional[str]] = sa.Column(sa.String, nullable=True)
    result: Mapped[str] = sa.Column(sa.String(20), nullable=False)
    requested_at: Mapped[datetime] = sa.Column(DateTime(timezone=True), nullable=False)

class SessionRequestModel(Base):
    __tablename__ = "sessions_requests"

    id: Mapped[sa.UUID] = sa.Column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(Text, nullable=True)
    request_id: Mapped[str] = mapped_column(Text, nullable=True)
    location_id: Mapped[str] = mapped_column(Text, nullable=True)
    evse_id: Mapped[str] = mapped_column(Text, nullable=True)
    connector_id: Mapped[str] = mapped_column(Text, nullable=True)

class OCPISessionModel(Base):    
    __tablename__ = "ocpi_sessions"

    id: Mapped[sa.UUID] = sa.Column(primary_key=True)
    session_id: Mapped[str] = sa.Column(sa.String, nullable=False)
    auth_id: Mapped[str] = sa.Column(sa.String, nullable=False)
    auth_method: Mapped[str] = sa.Column(sa.String(20), nullable=False)
    status: Mapped[str] = sa.Column(sa.String(20), nullable=False)
    party_id: Mapped[str] = sa.Column(sa.String(3), nullable=False)

    total_cost: Mapped[float] = sa.Column(sa.DECIMAL, nullable=False) # In OCPI prices can have more than 2 decimals
    kwh: Mapped[float] = sa.Column(sa.Numeric(10, 3), nullable=False)
    location_id: Mapped[str] = sa.Column(sa.String, nullable=False)
    evse_uid: Mapped[str] = sa.Column(sa.String, nullable=False)
    connector_id: Mapped[str] = sa.Column(sa.String, nullable=False)
    currency: Mapped[str] = sa.Column(sa.String(3), nullable=False)
    # start_date_time: Mapped[datetime] = sa.Column(DateTime(timezone=True), nullable=False)
    # end_date_time: Mapped[Optional[datetime]] = sa.Column(DateTime(timezone=True), nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now()
   )

class OCPISessionsUpdatesModel(Base):
    __tablename__ = "ocpi_sessions_updates"

    id: Mapped[sa.UUID] = sa.Column(primary_key=True)
    session_id: Mapped[str] = sa.Column(sa.String, nullable=False)
    kwh: Mapped[float] = sa.Column(sa.Numeric(10, 3), nullable=False)
    total_cost: Mapped[float] = sa.Column(sa.DECIMAL, nullable=False)
    status: Mapped[str] = sa.Column(sa.String(20), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        "updated_at",
        DateTime(timezone=True),
        server_default=func.now()
    )
