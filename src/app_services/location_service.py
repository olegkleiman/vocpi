"""
src.app_services.location_service.py

Author: Oleg Kleiman
Date: Feb, 2026

"""

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError
from .tariff_service import TariffService
import httpx
import logging
from datetime import datetime, timezone

from ..database import get_partner
from ..models.pydantic.models import TargetConnector, TargetLocation
from ..models.ocpi.models_ocpi import OCPIResponse, OCPILocation

logger = logging.getLogger(__name__)

class LocationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_location_details(self, 
                                   tariff_service: TariffService,
                                   location_id: str, 
                                   evse_id: str):
        
        partner_data = await get_partner(self.db, location_id, evse_id)
        partner_base_url, token, version = partner_data

        async with httpx.AsyncClient() as client:

            headers = {
                "Authorization": f"Token {token}"
            }
            url = f"{partner_base_url}/sender/{version}/locations/{location_id}"#/{evse_id}"

            response = await client.get(url, headers=headers)
            response.raise_for_status()

            try:
                cpo_resp = OCPIResponse.model_validate(response.json())
                loc_data: OCPILocation = OCPILocation.model_validate(cpo_resp.data)
                currency = ""

                target_connectors = []
                currency = ""
                for evse in loc_data.evses:
                    for conn in evse.connectors:
                        tarif_id = conn.tariff_id

                        tariff = None
                        if tarif_id:
                            tariff = await tariff_service.get_tariff(
                                location_id, evse_id, tarif_id
                            )
                        if not currency and tariff and hasattr(tariff, 'currency'):
                            currency = str(tariff.currency)
 
                        # tariff_elements = tariff.elements

                        today = datetime.now(timezone.utc).strftime("%A").upper()
                        if today in ["SUNDAY", "MONDAY", "WEDNESDAY"]:
                            print(f"{today} is in the list!")
                        else:
                            print(f"{today} is not in the list.")                        

                        new_conn = TargetConnector(
                                        name=f"Connector {conn.id}", 
                                        type=conn.power_type,
                                        standard=conn.standard,
                                        status=evse.status  # Inherited from parent EVSE
                        )
                        target_connectors.append(new_conn)

                target_location = TargetLocation(
                    name=loc_data.name or loc_data.address,
                    address=loc_data.address,
                    city = loc_data.city,
                    currency = currency,
                    connectors = target_connectors                    
                )
                return target_location.model_dump()
            
            except ValidationError as e:
                logger.error(f"Location Service Exception. Details: {e.json()}")

            return response.json()
