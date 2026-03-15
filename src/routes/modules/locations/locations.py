import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
import os
import sys
import httpx
import json
from datetime import datetime
from ....router import router

from fastapi import Depends, Request, HTTPException
from fastapi.encoders import jsonable_encoder
from sse_starlette.sse import EventSourceResponse

from ....exceptions import PartnerNotFoundError
from ....dependencies import get_location_service, get_tariff_service

logger = logging.getLogger(__name__)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger.setLevel(LOG_LEVEL)
console_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(console_handler)

def has_location_changed(new_data: dict, old_data: dict | None) -> bool:
    if old_data is None:
        return True

    # Make copies to compare, excluding the timestamp field.
    current_comp = new_data.copy()
    last_comp = old_data.copy()
    # exclude 'timestamp' from comparison
    current_comp.pop('timestamp', None)
    last_comp.pop('timestamp', None)
    return current_comp != last_comp

@router.get("/locations/updates/{location_id}/{evse_id}", tags=["Locations"],
            description="SSE endpoint for real-time location/evse updates")
async def location_updates(request: Request, 
                           location_id: str,
                           evse_id: str,
                           location_service = Depends(get_location_service),
                           tariff_service = Depends(get_tariff_service)):
        
    if not location_id or not evse_id:
        raise HTTPException(status_code=400, detail="location_id and evse_id are required")

    try:
        # Default to 3 seconds if missing/invalid
        delay = float(os.getenv("LOCATION_REFRESH_DELAY_SEC", "3.0")) 
    except (ValueError, TypeError):
        delay = 3.0

    logger.info(f"\t== Subscription to location updates for {location_id}:{evse_id}")

    async def event_generator():
        last_data = None
        # Reuse client for the duration of the SSE connection
        async with httpx.AsyncClient() as client:
            while True:

                if await request.is_disconnected():
                    logger.info(f"Location {location_id}:{evse_id} disconnected")
                    break

                try:
                    location_data = await location_service.get_location_details(tariff_service, location_id, evse_id)

                    if has_location_changed(location_data, last_data):
                        last_data = location_data
                        yield {
                            "event": "update", # SSE usually needs an event name
                            "id": f"{location_id}:{evse_id}", # str(uuid.uuid4()), # Unique ID for each event
                            "data" :json.dumps(jsonable_encoder(location_data)),
                        }
                    else: 
                        logger.debug(f"{datetime.now()} Pulled location data is the same for '{location_id}:{evse_id}' - skipping publishing to SSE")
                        
                except asyncio.TimeoutError:
                    # Send a 'heartbeat' comment if no message arrived
                    yield ": heartbeat\n\n"                        
                except Exception as e:
                    logger.error(f"Error in SSE locations loop for {location_id}:{evse_id}: {e}")
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": str(e)})
                    }

                await asyncio.sleep(delay)
  
    return EventSourceResponse(event_generator())

@router.get("/locations/{location_id}/{evse_id}", tags=["Locations"])
async def get_location(location_id: str,
                        evse_id: str,
                        location_service = Depends(get_location_service)) -> dict:
    
    try:

        if not location_id or not evse_id:
            raise HTTPException(status_code=400, detail="location_id and evse_id are required")

        return await location_service.get_location_details(location_id, evse_id)

    except Exception as e:
        logger.error(f"Error retrieving location: {e}")
        raise HTTPException(status_code=500, detail=str(e))
