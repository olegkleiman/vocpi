from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy import String, Column, DateTime, Boolean, UUID, Text, ForeignKey, JSON, Integer
from datetime import datetime
from typing import Optional, List

import uuid
from enum import Enum
import sqlalchemy as sa
from sqlalchemy.sql import func

from pydantic import BaseModel, Field, ConfigDict, AliasPath
from datetime import datetime

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

class EndSessionPayload(BaseModel):
    session_id: str

class BeginSessionResponse(BaseModel):
    session_id: str

# == Location

class TargetConnector(BaseModel):
    name: str  # Map from Connector.id
    type: str  # Map from Connector.power_type
    standard: str
    status: str  # Map from EVSE.status
    price_per_kwh: float = 1.23 # Default as per your example
    price_per_minute: float = 0.45

class TargetLocation(BaseModel):
    name: str
    address: str
    city: str
    currency: str
    connectors: List[TargetConnector]

class CPOConnector(BaseModel):
    id: str
    standard: str
    power_type: str
    tariff_id: str


class EVSE(BaseModel):
    status: str
    evse_id: str
    connectors: List[CPOConnector]

class LocationData(BaseModel):
    name: str
    city: str
    address: str
    evses: List[EVSE]


class CPOLocationResponse(BaseModel):
    data: LocationData

    
class CDRResponse(BaseModel):
    session_id: Optional[str] = None
    cdr_id: str
    currency: Optional[str] = None

    total_energy_kwh: Optional[float] = None
    total_cost: Optional[float] = None
    duration: Optional[str] = None
    
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    
    location: Optional[str] = None

#== SqlAlchemy models

class Base(DeclarativeBase):
    pass

class TerminalConfiguration(Base):
    __tablename__ = "ocpi_terminals"
        
    # Primary key using UUID
    id: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True)

    serial_number: Mapped[str] = mapped_column(String)
    location_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("ocpi_locations.id"))
    evse_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("ocpi_evses.id"))
    terminal_id: Mapped[str] = mapped_column(String)
    user_name: Mapped[str] = mapped_column(String)
    user_password: Mapped[str] = mapped_column(String)

class OCPILocation(Base):
    __tablename__ = "ocpi_locations"

    id: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True)
    location_id: Mapped[str] = mapped_column(String, unique=True)
    partner_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("ocpi_partners.id"))
    description: Mapped[str] = mapped_column(String)
    address: Mapped[str] = mapped_column(String)

class EVSEModel(Base):
    __tablename__ = "ocpi_evses"

    id: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True)
    evse_id: Mapped[str] = mapped_column(String, unique=True)
    location_id: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)

class OCPIPartnerModel(Base):
    __tablename__ = "ocpi_partners"
    
    id: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True)
    country_code: Mapped[str] = mapped_column(String(2))
    party_id: Mapped[str] = mapped_column(String(3))
    role: Mapped[str] = mapped_column(String(10))
    base_url: Mapped[str] = mapped_column(String)
    token: Mapped[str] = mapped_column(String)
    version: Mapped[str] = mapped_column(String)
    

class Token(Base):
    __tablename__ = "ocpi_tokens"

    uid: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True)
    partner_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("ocpi_partners.id"))
    type: Mapped[str] = mapped_column(sa.String(20))
    contract_id: Mapped[str] = mapped_column(sa.String)
    issuer: Mapped[str] = mapped_column(sa.String)
    valid: Mapped[bool] = mapped_column(sa.Boolean)
    whitelist: Mapped[str] = mapped_column(sa.String(20))
    last_updated: Mapped[Optional[datetime]] = mapped_column()
    # partner: Mapped[list["Partner"]] = relationship(back_populates="tokens")

class TokenAuthorization(Base):
    __tablename__ = "ocpi_token_authorizations"

    id: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True, server_default=sa.text("gen_random_uuid()"))
    token_uid: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("ocpi_tokens.uid"))
    location_id: Mapped[Optional[str]] = mapped_column(sa.String)
    evse_uid: Mapped[Optional[str]] = mapped_column(sa.String)
    connector_id: Mapped[Optional[str]] = mapped_column(sa.String)
    result: Mapped[str] = mapped_column(sa.String(20))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class SessionRequestModel(Base):
    __tablename__ = "sessions_requests"

    id: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(Text, nullable=True)
    request_id: Mapped[str] = mapped_column(Text, nullable=True)
    location_id: Mapped[str] = mapped_column(Text, nullable=True)
    evse_id: Mapped[str] = mapped_column(Text, nullable=True)
    connector_id: Mapped[str] = mapped_column(Text, nullable=True)

class OCPISessionModel(Base):    
    __tablename__ = "ocpi_sessions"

    id: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True)
    session_id: Mapped[str] = mapped_column(sa.String)
    auth_id: Mapped[str] = mapped_column(sa.String)
    auth_method: Mapped[str] = mapped_column(sa.String(20))
    status: Mapped[str] = mapped_column(sa.String(20))
    party_id: Mapped[str] = mapped_column(sa.String(3))

    # total_cost: Mapped[float] = sa.Column(sa.DECIMAL, nullable=False) # In OCPI prices can have more than 2 decimals
    # kwh: Mapped[float] = sa.Column(sa.Numeric(10, 3), nullable=False)
    location_id: Mapped[str] = mapped_column(sa.String)
    evse_uid: Mapped[str] = mapped_column(sa.String)
    connector_id: Mapped[str] = mapped_column(sa.String)
    currency: Mapped[str] = mapped_column(sa.String(3))
    # start_date_time: Mapped[datetime] = sa.Column(DateTime(timezone=True), nullable=False)
    # end_date_time: Mapped[Optional[datetime]] = sa.Column(DateTime(timezone=True), nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now()
   )

class OCPISessionsUpdatesModel(Base):
    __tablename__ = "ocpi_sessions_updates"

    id: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True)
    session_id: Mapped[str] = mapped_column(sa.String)
    kwh: Mapped[float] = mapped_column(sa.Numeric(10, 3))
    total_cost: Mapped[float] = mapped_column(sa.DECIMAL)
    status: Mapped[str] = mapped_column(sa.String(20))
    updated_at: Mapped[datetime] = mapped_column(
        "updated_at",
        DateTime(timezone=True),
        server_default=func.now()
    )

class TariffModel(Base):
    __tablename__ = "ocpi_tariffs"

    # Internal DB ID
    id: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True, default=uuid.uuid4)
    # The actual OCPI ID (e.g., "381_8") - mark as unique for indexing
    tariff_id: Mapped[str] = mapped_column(sa.String, unique=True, index=True)
    currency: Mapped[str] = mapped_column(String(3))

    elements = relationship("TariffElementModel", back_populates="tariff", cascade="all, delete-orphan")

class TariffElementModel(Base):
    __tablename__ = "ocpi_tariff_elements"

    id: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True, default=uuid.uuid4)
    tariff_id: Mapped[str] = mapped_column(
        sa.ForeignKey("ocpi_tariffs.tariff_id", ondelete="CASCADE"), 
        nullable=False
    )
    restrictions: Mapped[Optional[dict]] = mapped_column(JSON)
    price_components: Mapped[Optional[dict]] = mapped_column(JSON)

    tariff = relationship("TariffModel", back_populates="elements")

class CDRModel(Base):
    __tablename__ = "ocpi_cdrs"

    id: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True, default=uuid.uuid4)
    session_request_id: Mapped[str] = mapped_column(
        sa.ForeignKey("sessions_requests.request_id", ondelete="CASCADE"), 
        nullable=False
    )
    cdr_id: Mapped[str] = mapped_column(sa.String, unique=True, index=True)
    cdr: Mapped[Optional[dict]] = mapped_column(JSON)
