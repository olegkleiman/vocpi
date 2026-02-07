from ....router import router
from pydantic import BaseModel
from typing import Optional

import psycopg2
import boto3
import os

pg_password = os.getenv("PG_PASSWORD")
pg_username = os.getenv("PG_USERNAME")

class TokenValidateRequest(BaseModel):
    uid: str # The token ID (RFID UID, app user ID)
    type: str # Type of token: RFID, APP_USER, AD_HOC
    auth_id: Optional[str] = None # The ID of the party that issued the token (e.g. the operator or a third-party provider)
    location_id: str # The ID of the location where the token is being validated (e.g. the charging station or a specific connector)
    evse_uid: str # The unique identifier of the EVSE (Electric Vehicle Supply Equipment) where the token is being validated
    connector_id: str # Connector at that EVSE
    authorization_reference: str # A reference string that can be used for authorization purposes (e.g. a session ID or transaction ID)
    requested_energy: float # The amount of energy (in kWh) that the user intends to consume during the charging session

@router.post("/tokens/validate", tags=["tokens"], 
             description="Do a 'real-time' authorization request to the eMSP system, validating if a Token might be used (at the optionally given Location).")
async def validate_token(request: TokenValidateRequest):

    conn = None
    try:
        conn = psycopg2.connect(
            host='voicp-instance.c2niqycso7s9.us-east-1.rds.amazonaws.com',
            port=5432,
            database='postgres',
            user=pg_username,
            password=pg_password,
            sslmode='require',
        )
        cur = conn.cursor()
        cur.execute('SELECT version();')
        print(cur.fetchone()[0])

        token_uid = "c3c3c6a6-5f1a-4f6d-bc8b-6b6f4b1e8d91"
        query = """
            SELECT * 
            FROM ocpi_tokens WHERE uid = %s     
        """
        cur.execute(query, (token_uid,))
        rows = cur.fetchall()
        for row in rows:
            print(row)

        cur.close()
    except Exception as e:
        print(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

    return {"valid": True}
