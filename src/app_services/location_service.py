from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from ..database import get_partner

class LocationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_location_details(self, 
                                   location_id: str, 
                                   evse_id: str):
        async with httpx.AsyncClient() as client:
            partner_data = await get_partner(self.db, location_id, evse_id)
            partner_base_url, token, version = partner_data

            headers = {
                "Authorization": f"Token {token}"
            }
            url = f"{partner_base_url}/sender/{version}/locations/{location_id}/{evse_id}"

            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
