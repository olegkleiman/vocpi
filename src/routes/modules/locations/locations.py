import httpx
from ....router import router

@router.get("/locations/{location_id}", tags=["locations"])
async def get_locations(location_id: str,
                        evse_id: str):

    headers = {
        "Authorization": "Token 8f9e8b9f-eb94-4471-a029-20c089dd23b6"
    }

    async with httpx.AsyncClient(headers=headers) as client:
        response = await client.get(f"http://dev-api.wevo.energy/ocpi/sender/2.1.1/locations/{location_id}/{evse_id}")
        response.raise_for_status()
        print(response.json()) 
    # 

    return {"location_id": location_id}