from ....router import router
from pydantic import BaseModel
from typing import Optional

class TokenValidateRequest(BaseModel):
    uid: str # The token ID (RFID UID, app user ID)
    type: str # Type of token: RFID, APP_USER, AD_HOC
    auth_id: Optional[str] = None # The ID of the party that issued the token (e.g. the operator or a third-party provider)
    location_id: str # The ID of the location where the token is being validated (e.g. the charging station or a specific connector)
    evse_uid: str # The unique identifier of the EVSE (Electric Vehicle Supply Equipment) where the token is being validated
    connector_id: str # Connector at that EVSE
    authorization_reference: str # A reference string that can be used for authorization purposes (e.g. a session ID or transaction ID)
    requested_energy: float # The amount of energy (in kWh) that the user intends to consume during the charging session

@router.post("/tokens/validate", tags=["tokens"])
async def validate_token(request: TokenValidateRequest):
    return {"valid": True}
