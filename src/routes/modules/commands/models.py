from pydantic import BaseModel
from enum import Enum
from typing import Optional

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