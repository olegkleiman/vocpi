"""
src.app_services.session_service.py

Project: WEV (OCPI+ Server)
Author: Oleg Kleiman
Date: March, 2026

"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from aiocache import cached
from aiocache.serializers import PickleSerializer

from ..models.pydantic.models import SessionUpdate
from ..models.ocpi.models_ocpi import OCPISession, SessionStatus, OCPIAuthMethod
from ..models.sqlalchemy.models import DbSessionRequestModel,  OCPILocation, EVSEModel, OCPIPartnerModel, DbSessionModel, DbSessionsUpdatesModel
from ..exceptions import PartnerNotFoundError

class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def save_session(self, session: OCPISession):

        location_id = session.location.id
        evse_id = session.location.evses[0].uid
        connector_id = session.location.evses[0].connectors[0].id

        sessionModel = DbSessionModel(
            id = str(uuid.uuid4()), 
            session_id = session.id,
            auth_id = session.auth_id,
            auth_method = session.auth_method,
            location_id = location_id,
            evse_uid = evse_id,
            connector_id=connector_id,
            currency= session.currency,
            status = SessionStatus.ACTIVE.value,
            last_updated=datetime.now(timezone.utc)
        )

        self.db.add(sessionModel)
        await self.db.commit()

    async def create_and_save_session_update(self, 
                                             session: OCPISession, 
                                             session_request_id: str) -> SessionUpdate:
        session_model = DbSessionsUpdatesModel(
            id = str(uuid.uuid4()),
            session_id = session.id,
            kwh = session.kwh,
            total_cost = session.total_cost,
            updated_at = session.last_updated,
            status = session.status
        )
        
        self.db.add(session_model)
        await self.db.commit()

        update_response =  SessionUpdate(session_id = session_request_id, # Sic! This is where session (session_model.session_id) is substituted to session_request
                              kwh =session_model.kwh, 
                              total_cost=session_model.total_cost,
                              currency=session.currency,
                              updated_at=session_model.updated_at)

        return update_response

    async def get_request_id_by_session_id(
            self,
            session_id: str
    ) -> str | None:
        smt = (
            select(DbSessionRequestModel.request_id)
            .where(DbSessionRequestModel.session_id == session_id)
        )
        result = await self.db.execute(smt)
        request_id = result.scalar()
        return request_id          

    async def get_request_id(
            self,
            location_id: str,
            evse_id: str,
            connector_id: str
    ) -> str | None:
        smt = (
            select(DbSessionRequestModel.request_id)
            .where(DbSessionRequestModel.location_id == location_id
                   and DbSessionRequestModel.evse_id == evse_id
                   and DbSessionRequestModel.connector_id == connector_id)
        )
        result = await self.db.execute(smt)
        request_id = result.scalar()
        return request_id

    async def get_session_id(
            self,
            request_id: str
    ) -> str | None:
        smt = (
            select(DbSessionRequestModel.session_id)
            .where(DbSessionRequestModel.request_id == request_id)
        )
        result = await self.db.execute(smt)
        session_id = result.scalar()
        return session_id  

    async def get_session_id_by_location(self, location_id, evse_id, connector_id) -> str| None:
         smt = (
              select(DbSessionRequestModel.session_id)
              .where(DbSessionRequestModel.location_id == location_id,
                     DbSessionRequestModel.evse_id == evse_id,
                     DbSessionRequestModel.connector_id == connector_id)
         )
         result = await self.db.execute(smt)
        
         session_id = result.scalar()
         return session_id          
    
    # Associate existing request_id with passed session_id
    async def set_session_id(self,
                             request_id: str, 
                             session_id: str
    )-> None:
         stmt = select(DbSessionRequestModel).where(DbSessionRequestModel.request_id == request_id)
         result = await self.db.execute(stmt)
         record = result.scalar_one_or_none()

         if record:
            record.session_id = session_id
            
            await self.db.commit()
            await self.db.refresh(record)

    async def save_session_request(self,
                        request_id,
                        location_id: str,
                        evse_id: str,
                        connector_id: str):
                            
            session_request = DbSessionRequestModel(
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
            delete(DbSessionRequestModel)
            .where(DbSessionRequestModel.request_id == request_id)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()

    # async def get_partner_from_session_id(self,
    #                                       session_id:str):
    #     stmt = (
    #         select(
    #             OCPIPartnerModel.base_url, 
    #             OCPIPartnerModel.token, 
    #             OCPIPartnerModel.version
    #         )
    #         # Start from Sessions, join Partners
    #         .select_from(DbSessionModel) 
    #         .join(OCPIPartnerModel, DbSessionModel.party_id == OCPIPartnerModel.party_id)
    #         .where(DbSessionModel.session_id == session_id)
    #     )
    #     result = await self.db.execute(stmt)
    #     partner_data = result.first()
    #     return partner_data

    async def get_location_from_session_id(self,
                                          session_id:str):
        
        # SELECT s.location_id, s.evse_uid
        # FROM public.ocpi_sessions s
        # JOIN public.sessions_requests r
        # ON s.session_id = r.session_id
        # WHERE r.session_id = <session_id>
            
        stmt = (  
             select(OCPILocation.location_id, EVSEModel.evse_id)
             .select_from(DbSessionModel)
             .join(DbSessionRequestModel, DbSessionModel.session_id == DbSessionRequestModel.session_id)
             .where(DbSessionRequestModel.session_id == session_id)
        )
        result = await self.db.execute(stmt)
        location_data = result.first()

        return location_data           

    @cached(ttl=600, key="{location_id}:{evse_id}", serializer=PickleSerializer())
    async def get_partner(self,
                        location_id: str,
                        evse_id: str) :
                
            # select * from ocpi_partners p
            # JOIN ocpi_locations l 
            # ON p.id = l.partner_id 
            # JOIN ocpi_evses e
            # ON l.id = e.location_id
            # where l.location_id = <location_id>
            # and e.evse_id = <evse_id>

            stmt = (
                select(OCPIPartnerModel)
                .join(OCPILocation, OCPIPartnerModel.id == OCPILocation.partner_id)
                .join(EVSEModel, OCPILocation.id== EVSEModel.location_id)  
                .where(OCPILocation.location_id == location_id,
                    EVSEModel.evse_id == evse_id)
            )

            result = await self.db.execute(stmt)
            partner_row = result.first()

            if not partner_row:
                raise PartnerNotFoundError(f"Partner not found for location {location_id}, evse {evse_id}")

            partner_object = partner_row[0]
            return partner_object.base_url, partner_object.token, partner_object.version              
