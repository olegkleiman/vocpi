
"""
.models.sqlalchemy..py

Author: Oleg Kleiman
Date: Feb, 2026

"""

#== SqlAlchemy models
import uuid
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy import String, Column, DateTime, Boolean, UUID, Text, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import JSONB

import sqlalchemy as sa
from sqlalchemy.sql import func
from typing import Optional

class Base(DeclarativeBase):
    pass

class DbTerminalConfigurationModel(Base):
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

    tokens: Mapped[list["TokenModel"]] = relationship(back_populates="partner")
    

class TokenModel(Base):
    __tablename__ = "ocpi_tokens"

    uid: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True)
    partner_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("ocpi_partners.id"))
    type: Mapped[str] = mapped_column(sa.String(20))
    contract_id: Mapped[str] = mapped_column(sa.String)
    issuer: Mapped[str] = mapped_column(sa.String)
    valid: Mapped[bool] = mapped_column(sa.Boolean)
    whitelist: Mapped[str] = mapped_column(sa.String(20))
    last_updated: Mapped[Optional[datetime]] = mapped_column()
    partner: Mapped["OCPIPartnerModel"] = relationship(back_populates="tokens")

class TokenAuthorization(Base):
    __tablename__ = "ocpi_token_authorizations"

    id: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True, server_default=sa.text("gen_random_uuid()"))
    token_uid: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("ocpi_tokens.uid"))
    location_id: Mapped[Optional[str]] = mapped_column(sa.String)
    evse_uid: Mapped[Optional[str]] = mapped_column(sa.String)
    connector_id: Mapped[Optional[str]] = mapped_column(sa.String)
    result: Mapped[str] = mapped_column(sa.String(20))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class DbSessionRequestModel(Base):
    __tablename__ = "sessions_requests"

    id: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(Text, nullable=True)
    request_id: Mapped[str] = mapped_column(Text, nullable=True)
    location_id: Mapped[str] = mapped_column(Text, nullable=True)
    evse_id: Mapped[str] = mapped_column(Text, nullable=True)
    connector_id: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class DbSessionModel(Base):    
    __tablename__ = "ocpi_sessions"

    id: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True)
    session_id: Mapped[str] = mapped_column(sa.String)
    auth_id: Mapped[str] = mapped_column(sa.String)
    auth_method: Mapped[str] = mapped_column(sa.String(20))
    status: Mapped[str] = mapped_column(sa.String(20))
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

class DbSessionsUpdatesModel(Base):
    __tablename__ = "ocpi_sessions_updates"

    id: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True)
    session_id: Mapped[str] = mapped_column(sa.String)
    kwh: Mapped[float] = mapped_column(sa.Numeric(10, 3))
    total_cost: Mapped[float] = mapped_column(sa.Numeric(20, 4))
    status: Mapped[str] = mapped_column(sa.String(20))
    updated_at: Mapped[datetime] = mapped_column(
        "updated_at",
        DateTime(timezone=True),
        server_default=func.now()
    )

class DbTariffModel(Base):
    __tablename__ = "ocpi_tariffs"

    # Internal DB ID
    id: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True, default=uuid.uuid4)
    # The actual OCPI ID (e.g., "381_8") - mark as unique for indexing
    tariff_id: Mapped[str] = mapped_column(sa.String, unique=True, index=True)
    currency: Mapped[str] = mapped_column(String(3))

    elements = relationship(
                    "DbTariffElementModel", 
                    back_populates="tariff", 
                    cascade="all, delete-orphan",
                    lazy="selectin" 
                )

class DbTariffElementModel(Base):
    __tablename__ = "ocpi_tariff_elements"

    id: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True, default=uuid.uuid4)
    tariff_id: Mapped[str] = mapped_column(
        sa.ForeignKey("ocpi_tariffs.tariff_id", ondelete="CASCADE"), 
        nullable=False
    )
    restrictions: Mapped[Optional[dict]] = mapped_column(JSON)
    price_components: Mapped[Optional[dict]] = mapped_column(JSON)

    tariff = relationship(
                    "DbTariffModel", 
                    back_populates="elements",
                    lazy="selectin"
            )

class CDRModel(Base):
    __tablename__ = "ocpi_cdrs"

    id: Mapped[uuid.UUID] = mapped_column(sa.UUID, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(sa.String)
    session_request_id: Mapped[str] = mapped_column(
        sa.ForeignKey("sessions_requests.request_id", ondelete="CASCADE"), 
        nullable=False
    )
    cdr_id: Mapped[str] = mapped_column(sa.String, unique=True, index=True)
    cdr_json: Mapped[Optional[dict]] = mapped_column(JSONB)
