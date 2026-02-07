from ....router import router

@router.get("/cpo/2.1.1/locations", tags=["locations"])
async def get_locations():
    return {"locations": []}