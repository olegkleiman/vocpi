
"""
routes.config.config.py

Author: Oleg Kleiman
Date: Feb, 2026
Last edited: April, 2026

"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException

# from ....router import router

from ....models.sqlalchemy.models import DbTerminalConfigurationModel, OCPILocation, EVSEModel
from ....database import get_db

api_router = APIRouter()

logger = logging.getLogger(__name__)

@api_router.get("/terminal/{sn}", tags=["Custom API", "Configuration"])
async def app_config(sn: str,
                     db: AsyncSession = Depends(get_db) ):
    logger.info(f"Config endpoint called for serial number: {sn}")

    try:
        stmt = (
            select(DbTerminalConfigurationModel)
            .join(OCPILocation, DbTerminalConfigurationModel.location_id == OCPILocation.id)
            .join(EVSEModel, DbTerminalConfigurationModel.evse_id == EVSEModel.id)  
            .where(DbTerminalConfigurationModel.serial_number == sn)
        )

        result = await db.execute(stmt)
        config_row = result.first()

        if config_row:
            # The result is a Row containing the TerminalConfiguration object.
            # We access it by index and then create a dictionary from its attributes
            # to make it JSON serializable.
            config_object = config_row[0]
            return {
                "location_id": config_object.location_id,
                "evse_id": config_object.evse_id,
                "terminal_id": config_object.terminal_id,
                "user_name": config_object.user_name,
                "user_password": config_object.user_password
            }
        raise HTTPException(status_code=404, detail="Configuration not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))
