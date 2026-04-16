import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
import os
import sys
import httpx
import json
from datetime import datetime, timezone

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
api_router = APIRouter()

def has_location_changed(new_data: TargetLocation, old_data: TargetLocation | None) -> bool:
    if old_data is None:
        return True
    
    if new_data.timestamp != old_data.timestamp:
        return True
    
    return False

@api_router.get("/locations/updates/{location_id}/{evse_id}", tags=["Locations"],
            description="SSE endpoint for real-time location/evse updates")
async def location_updates(request: Request, 
                           location_id: str,
                           evse_id: str,
                           location_service = Depends(get_locations_service),
                           tariff_service = Depends(get_tariff_service),
                           pubsub = Depends(get_pubsub)):
        
    if not location_id or not evse_id:
        raise HTTPException(status_code=400, detail="location_id and evse_id are required")

    topic_id = f"{location_id}:{evse_id}"
    queue = await pubsub.subscribe(topic_id)

    try:
        # Default to 3 seconds if missing/invalid
        timeout = float(os.getenv("LOCATION_REFRESH_TIMEOUT_SEC", "30.0")) 
    except (ValueError, TypeError):
        timeout = 30.0

    logger.info(f"\t== Subscription to location updates for {location_id}:{evse_id}")

    async def event_generator():

        # Flush headers immediately so client onopen fires without waiting for first message
        yield {"event": "ping", "data": ""}

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
                    location_data = await asyncio.wait_for(queue.get(), timeout=timeout)
                    # location_data = await queue.get()

                    last_data = location_data
                    yield {
                        "event": "update", # SSE needs an event name
                        "id": f"{location_id}:{evse_id}", # str(uuid.uuid4()), # Unique ID for each event
                        "data" :json.dumps(jsonable_encoder(location_data)),
                    }
                        
                except asyncio.TimeoutError:
                    location_data = await location_service.get_location_details(tariff_service, location_id, evse_id)
                    yield {
                        "event": "update",
                        "id": f"{location_id}:{evse_id}", # str(uuid.uuid4()) -> Unique ID for each event
                        "data" :json.dumps(jsonable_encoder(location_data)),
                    }

                except Exception as e:
                    logger.error(f"Error in SSE locations loop for {location_id}:{evse_id}: {e}")
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": str(e)})
                    }
  
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
