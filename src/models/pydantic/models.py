
"""
pydantic.models.py

Author: Oleg Kleiman
Date: Feb, 2026

"""

from typing import Optional, List, Any

from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, AliasPath, model_validator
from datetime import datetime

#== Pydantic models

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

class SessionUpdate(BaseModel):
    session_id: str
    kwh: float
    total_cost: float
    currency: str
    updated_at: datetime

class CDRResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: Optional[str] = None
    cdr_id: str
    currency: Optional[str] = None

    total_energy_kwh: Optional[float] = Field(default=None, alias='total_energy')
    total_cost: Optional[float] = None
    duration: Optional[str] = None
    
    started_at: Optional[str] = Field(default=None, alias='start_date_time')
    ended_at: Optional[str] = Field(default=None, alias='stop_date_time')
    
    location: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def transform_input(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Handle location object to string transformation
            location_data = data.get("location")
            if isinstance(location_data, dict):
                data['location'] = location_data.get("name") or location_data.get("address")

            # Handle duration calculation from total_time (in hours)
            total_time_hours = data.get("total_time")
            if isinstance(total_time_hours, (int, float)):
                hours = int(total_time_hours)
                minutes = int((total_time_hours * 60) % 60)
                data['duration'] = f"{hours:02}:{minutes:02}"

        return data
