from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from aiocache import cached
from aiocache.serializers import PickleSerializer

from ..models import SessionRequestModel,  OCPILocation, EVSE, OCPIPartnerModel, OCPISessionModel
from ..exceptions import PartnerNotFoundError

class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_request_id(
            self,
            location_id: str,
            evse_id: str,
            connector_id: str
    ) -> str | None:
        smt = (
            select(SessionRequestModel.request_id)
            .where(SessionRequestModel.location_id == location_id
                   and SessionRequestModel.evse_id == evse_id
                   and SessionRequestModel.connector_id == connector_id)
        )
        result = await self.db.execute(smt)
        request_id = result.scalar()
        return request_id
    

    async def get_session_id(
            self,
            request_id: str
    ) -> str | None:
        smt = (
            select(SessionRequestModel.session_id)
            .where(SessionRequestModel.request_id == request_id)
        )
        result = await self.db.execute(smt)
        session_id = result.scalar()
        return session_id    

    # Associate existing request_id with passed session_id
    async def set_session_id(self,
                             request_id: str, 
                             session_id: str
    )-> None:
         stmt = select(SessionRequestModel).where(SessionRequestModel.request_id == request_id)
         result = await self.db.execute(stmt)
         record = result.scalar_one_or_none()

         if record:
            record.session_id = session_id
            
            await self.db.commit()
            await self.db.refresh(record)

    async def save_session(self,
                             request_id,
                            location_id: str,
                            evse_id: str,
                            connector_id: str):
                            
            session_request = SessionRequestModel(
                request_id = request_id,
                location_id = location_id,
                evse_id = evse_id,
                connector_id = connector_id,
            )

            self.db.add(session_request)
            await self.db.commit()
            await self.db.refresh(session_request)

    async def delete_session(self,
                             request_id: str):
        stmt = (
            delete(SessionRequestModel)
            .where(SessionRequestModel.request_id == request_id)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()

    async def get_partner_from_session_id(self,
                                          session_id:str):
        stmt = (
            select(
                OCPIPartnerModel.base_url, 
                OCPIPartnerModel.token, 
                OCPIPartnerModel.version
            )
            # Start from Sessions, join Partners
            .select_from(OCPISessionModel) 
            .join(OCPIPartnerModel, OCPISessionModel.party_id == OCPIPartnerModel.party_id)
            .where(OCPISessionModel.session_id == session_id)
        )
        result = await self.db.execute(stmt)
        partner_data = result.first()
        return partner_data

    @cached(ttl=600, key="{location_id}:{evse_id}", serializer=PickleSerializer())
    async def get_partner(self,
                        location_id: str,
                        evse_id: str) :
                
            # select * from ocpi_partners p
            # JOIN ocpi_locations l 
            # ON p.id = l.partner_id 
            # JOIN ocpi_evses e
            # ON l.id = e.location_id
            # where l.location_id = 'xxx'
            # and e.evse_id = 'yyy'

            stmt = (
                select(OCPIPartnerModel)
                .join(OCPILocation, OCPIPartnerModel.id == OCPILocation.partner_id)
                .join(EVSE, OCPILocation.id== EVSE.location_id)  
                .where(OCPILocation.location_id == location_id,
                    EVSE.evse_id == evse_id)
            )

            result = await self.db.execute(stmt)
            partner_row = result.first()

            if not partner_row:
                raise PartnerNotFoundError(f"Partner not found for location {location_id}, evse {evse_id}")

            partner_object = partner_row[0]
            return partner_object.base_url, partner_object.token, partner_object.version              
