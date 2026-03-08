from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import logging

from ..models import TariffModel, TariffElementModel
from ..database import get_partner

logger = logging.getLogger(__name__)

class TariffService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_existing_tariff(self, 
                        tariff_id: str) -> bool:
            # if passed tariff is already stored in Db => just return it
            stmt = (
                select(TariffModel)
                .where(TariffModel.tariff_id == tariff_id)
            )
            result = await self.db.execute(stmt)
            tariff_row = result.first()

            if tariff_row:
                return tariff_row[0]

    async def get_tariff(self,
                         location_id: str, 
                         evse_id: str,
                         tariff_id: str) -> TariffModel:
        
        try:
            tariff = await self.get_existing_tariff(tariff_id)
            if tariff:
                return tariff

            # If no tariff stored => request it from CPO and store in Db
            # Then return it (after commit)
            partner_data = await get_partner(self.db, location_id, evse_id)
            partner_base_url, token, version = partner_data

            headers = {
                "Authorization": f"Token {token}"
            }
            url = f"{partner_base_url}/sender/{version}/tariffs"     

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status() 

                rawJson = response.json()
                tariff_data = rawJson["data"]
                tariff_dict = next((t for t in tariff_data if t["id"] == tariff_id), None)

                if not tariff_dict:
                    return

                elements = []
                for el in tariff_dict.get("elements", []):
                    elements.append(TariffElementModel(
                            restrictions=el.get("restrictions"),
                            price_components=el.get("price_components"),
                            tariff_id = tariff_dict["id"]                         
                    ))

                tariff = TariffModel(
                    tariff_id = tariff_dict["id"],
                    currency = tariff_dict["currency"],
                    elements = elements
                )
                self.db.add(tariff)
                await self.db.commit()

                return tariff

        except Exception as e:
            logger.error(f"Tariff Service. Details: {e}")
            raise e

        