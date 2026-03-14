"""
src.app_services.drs_service.py

Project: WEV (OCPI+ Server)
Author: Oleg Kleiman
Date: Feb, 2026

"""

import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from ..models.pydantic.models import CDRResponse
from ..models.sqlalchemy.models import CDRModel
from ..models.ocpi.models_ocpi import OCPICDR

class CDRService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def cdr_id_to_session_id(self, cdr_id: str) -> str:
        return cdr_id

    async def save_cdr(self, 
                       session_id: str,
                       session_request_id,
                       cdr: OCPICDR):
        
        # total_cost = cdr.total_cost
        # currency = cdr.currency
        # total_energy = cdr.total_energy
        # total_time = cdr.total_time
        
        cdr_model = CDRModel(
            session_id = session_id,
            session_request_id = session_request_id,
            cdr_id = cdr.id,
            cdr_json = cdr.model_dump()
        )
        self.db.add(cdr_model)
        await self.db.commit()

    async def get_cdr(self, session_id: str, db: AsyncSession):
        smt = (
            select(CDRModel)
            .where(CDRModel.session_request_id == session_id)
        )
        cdr_row = (await db.execute(smt)).scalars().first()

        if not cdr_row:
            return None
        
        raw_json = cdr_row.cdr_json or {}
        
        # Use model_validate to correctly parse the raw JSON from the database,
        # which has a different structure (from OCPICDR) than the target CDRResponse.
        # The validation logic is now handled within the CDRResponse model itself.
        cdr = CDRResponse.model_validate({
            "cdr_id": cdr_row.cdr_id,
            "session_id": session_id,
            **raw_json
        })
                        
        return cdr
