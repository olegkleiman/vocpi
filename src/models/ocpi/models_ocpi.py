
"""
.src.models.ocpi.py

Project: WEV (OCPI+ Server)
Author: Oleg Kleiman
Date: Feb, 2026

"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, Any, List
from datetime import datetime, timezone

def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    INVALID = "INVALID"
    PENDING = "PENDING"
    RESERVATION = "RESERVATION"

class OCPIAuthMethod(str, Enum):
    AUTH_REQUEST    = "AUTH_REQUEST"
    WHITELIST       = "WHITELIST"
    COMMAND         = "COMMAND"

class LocationType(str, Enum):
    ON_STREET       = "ON_STREET"
    PARKING_GARAGE  = "PARKING_GARAGE"
    UNDERGROUND     = "UNDERGROUND_GARAGE"
    PARKING_LOT     = "PARKING_LOT"
    OTHER           = "OTHER"
    UNKNOWN         = "UNKNOWN"

class OCPIGeoLocation(BaseModel):
    latitude: str
    longitude: str

class OCPIConnectorStandard(str, Enum):
    IEC_62196_T2        = "IEC_62196_T2"
    IEC_62196_T2_COMBO  = "IEC_62196_T2_COMBO"
    CHADEMO             = "CHADEMO"
    DOMESTIC_A          = "DOMESTIC_A"

class OCPIConnectorFormat(str, Enum):
    SOCKET          = "SOCKET"
    CABLE           = "CABLE"

class OCPIPowerType(str, Enum):
    AC_1_PHASE      = "AC_1_PHASE"
    AC_3_PHASE      = "AC_3_PHASE"
    DC              = "DC"

class OCPIPriceComponentType(str, Enum):
    ENERGY          = "ENERGY"
    FLAT            = "FLAT"
    PARKING_TIME    = "PARKING_TIME"
    TIME            = "TIME"

class OCPIDimensionType(str, Enum):
    ENERGY          = "ENERGY"
    FLAT            = "FLAT"
    MAX_CURRENT     = "MAX_CURRENT"
    MIN_CURRENT     = "MIN_CURRENT"
    PARKING_TIME    = "PARKING_TIME"
    TIME            = "TIME"

class OCPICommandResponseType(str, Enum):
    ACCEPTED = "ACCEPTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    REJECTED = "REJECTED"
    UNKNOWN_SESSION = "UNKNOWN_SESSION"

class OCPIStatusCode(int, Enum):
    # Success
    SUCCESS                 = 1000
    # Client errors
    INVALID_PARAMETERS      = 2001
    NOT_ENOUGH_INFO         = 2002
    UNKNOWN_LOCATION        = 2003
    UNKNOWN_TOKEN           = 2004
    # Server errors
    SERVER_ERROR            = 3000
    UNABLE_TO_USE_CLIENT    = 3001

class OCPICommandResponse(BaseModel):
    result: OCPICommandResponseType
    timeout: int = 30

class SessionDetailsResponse(BaseModel):
    id: str
    status: SessionStatus
    delivered_kwh: float = 0.0
    total_cost: str
    duration: str

class OCPIResponse(BaseModel):
    data: Optional[Any] = None
    status_code: OCPIStatusCode =  OCPIStatusCode.SUCCESS
    status_message: str = "Success"
    timestamp: str = Field(default_factory=utc_now)

class OCPIConnector(BaseModel):
    id: str
    standard: OCPIConnectorStandard
    format: OCPIConnectorFormat
    power_type: OCPIPowerType
    max_voltage: Optional[int] = None
    voltage: Optional[int] = None      # Wevo sends this
    max_amperage: Optional[int] = None
    amperage: Optional[int] = None     # Wevo sends this
    max_electric_power: Optional[int] = None
    tariff_id: Optional[str] = None

    @property
    def effective_voltage(self) -> Optional[int]:
        return self.max_voltage or self.voltage

    @property
    def effective_amperage(self) -> Optional[int]:
        return self.max_amperage or self.amperage    

class OCPIEVSE(BaseModel):
    uid: str
    evse_id: Optional[str] = None
    status: str
    connectors: List[OCPIConnector]    

class OCPILocation(BaseModel):
    id: str
    type: LocationType
    name: Optional[str] = None
    address: str
    city: str
    postal_code: str
    country: str                        # ISO 3166-1 alpha-3
    coordinates: OCPIGeoLocation
    evses: List[OCPIEVSE]    

class OCPIPriceComponent(BaseModel):
    type: OCPIPriceComponentType
    price: float
    step_size: int

class OCPITariffElement(BaseModel):
    price_components: List[OCPIPriceComponent]

class OCPITariff(BaseModel):
    id: str
    currency: str                       # ISO 4217
    elements: List[OCPITariffElement]

class OCPIChargingDimension(BaseModel):
    type: OCPIDimensionType
    volume: float

class OCPIChargingPeriod(BaseModel):
    start_date_time: str
    dimensions: List[OCPIChargingDimension]

class OCPISession(BaseModel):
    id: str
    start_datetime: str
    end_datetime: Optional[str] = None          # None if session still ACTIVE
    kwh: Optional[float]                                  # energy delivered so far
    auth_id: str
    auth_method: OCPIAuthMethod
    location: OCPILocation
    meter_id: Optional[str] = None
    currency: str
    charging_periods: Optional[List[OCPIChargingPeriod]] = None
    total_cost: Optional[float] = None          # None if session still ACTIVE
    status: SessionStatus
    last_updated: datetime

class OCPICDR(BaseModel):
    id: str
    start_date_time: str
    stop_date_time: str
    auth_id: str
    auth_method: OCPIAuthMethod
    location: OCPILocation
    meter_id: Optional[str] = None
    currency: str
    tariffs: Optional[List[OCPITariff]] = None
    charging_periods: List[OCPIChargingPeriod]
    total_cost: float
    total_energy: float
    total_time: float
    total_parking_time: Optional[float] = None
    remark: Optional[str] = None
    last_updated: str = Field(default_factory=utc_now)      

  