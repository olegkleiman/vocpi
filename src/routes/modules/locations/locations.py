import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
import os
import sys
import httpx
import json
from datetime import datetime, timezone
import hashlib

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.encoders import jsonable_encoder
from sse_starlette.sse import EventSourceResponse

from ....models.ocpi.models_ocpi import OCPIResponse, OCPIStatusCode
from ....models.pydantic.models import TargetConnector, TargetLocation
from ....dependencies import get_pubsub
from ....pubsub import OCPIPubSub
from ....dependencies import get_locations_service, get_tariff_service

logger = logging.getLogger(__name__)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger.setLevel(LOG_LEVEL)
console_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(console_handler)

router = APIRouter()

current_location = {}

def has_location_changed(new_data: TargetLocation, old_data: TargetLocation | None) -> bool:
    if old_data is None:
        return True
    
    if new_data.timestamp != old_data.timestamp:
        return True
    
    return False


@router.get("/locations/updates/{location_id}/{evse_id}", tags=["Locations"],
            description="SSE endpoint for real-time location/evse updates")
async def location_updates(request: Request, 
                           location_id: str,
                           evse_id: str,
                           location_service = Depends(get_locations_service),
                           tariff_service = Depends(get_tariff_service),
                           pubsub = Depends(get_pubsub)):
        
    if not location_id or not evse_id:
        raise HTTPException(status_code=400, detail="location_id and evse_id are required")

    _current_location_id = f"{location_id}:{evse_id}"
    current_location_hash = hashlib.sha256(_current_location_id.encode()).hexdigest()
    queue = await pubsub.subscribe(current_location_hash)

    try:
        # Default to 3 seconds if missing/invalid
        delay = float(os.getenv("LOCATION_REFRESH_DELAY_SEC", "3.0")) 
    except (ValueError, TypeError):
        delay = 3.0

    logger.info(f"\t== Subscription to location updates for {location_id}:{evse_id}")

    async def event_generator():

        # Force to get location for initialization step 
        _location_data = await location_service.get_location_details(tariff_service, location_id, evse_id)
        yield {
            "event": "update", # SSE needs an event name
            "id": f"{location_id}:{evse_id}", # str(uuid.uuid4()), # Unique ID for each event
            "data" :json.dumps(jsonable_encoder(_location_data)),
        }

        last_data = None
        # Reuse client for the duration of the SSE connection
        async with httpx.AsyncClient() as client:
            while True:

                if await request.is_disconnected():
                    logger.info(f"Location {location_id}:{evse_id} disconnected")
                    break

                try:
                    # location_data = await asyncio.wait_for(queue.get(), timeout=delay)
                    location_data = await queue.get()

                    # if has_location_changed(location_data, last_data):
                    last_data = location_data
                    yield {
                        "event": "update", # SSE needs an event name
                        "id": f"{location_id}:{evse_id}", # str(uuid.uuid4()), # Unique ID for each event
                        "data" :json.dumps(jsonable_encoder(location_data)),
                    }
                    # else: 
                    #     logger.debug(f"{datetime.now()} Pulled location data is the same for '{location_id}:{evse_id}' - skipping publishing to SSE")
                        
                # except asyncio.TimeoutError:
                #     location_data = await location_service.get_location_details(tariff_service, location_id, evse_id)
                #     location_data = last_sessions_kv[current_location_hash]
                #     yield {
                #         "event": "erro",
                #         "id": f"{location_id}:{evse_id}", # str(uuid.uuid4()) -> Unique ID for each event
                #         "data" : "",
                #     }

                except Exception as e:
                    logger.error(f"Error in SSE locations loop for {location_id}:{evse_id}: {e}")
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": str(e)})
                    }

                # await asyncio.sleep(delay)
  
    return EventSourceResponse(event_generator())

# According to OCPI 2.1.1 only PUT is used - POST (TBD: Why?) for locations
@router.put("/locations/{location_id}/{evse_id}", tags=["Locations"],
            description="Endpoint for CPO to push location updates.",
            response_model=OCPIResponse)
async def push_location_update(
    location_id: str,
    evse_id: str,
    location_data: dict, # Or a specific Pydantic model for location data
    pubsub: OCPIPubSub = Depends(get_pubsub)
):
    topic_id = f"{location_id}:{evse_id}"
    logger.info(f"Publishing location update for topic: {topic_id}")
    
    # You can add logic here to check if the location data has actually changed
    # before publishing, using your `has_location_changed` function.
    # This would prevent sending unnecessary SSE events if the data is identical.
    # For now, we'll publish every time this endpoint is called.

    await pubsub.publish(topic_id, location_data)

    return OCPIResponse(
        status_code=OCPIStatusCode.SUCCESS,
        status_message="Location update published.",
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )

# @router.get("/locations/{location_id}/{evse_id}", tags=["Locations"])
# async def get_location(location_id: str,
#                         evse_id: str,
#                         location_service = Depends(get_locations_service)) -> dict:
    
#     try:

#         if not location_id or not evse_id:
#             raise HTTPException(status_code=400, detail="location_id and evse_id are required")

#         return await location_service.get_location_details(location_id, evse_id)

#     except Exception as e:
#         logger.error(f"Error retrieving location: {e}")
#         raise HTTPException(status_code=500, detail=str(e))
