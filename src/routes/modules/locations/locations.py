from ....router import router

@router.get("/locations/{location_id}", tags=["locations"])
async def get_locations(location_id: str):
    return {"location_id": location_id}