from fastapi import FastAPI
from .router import router

app = FastAPI(
    title="OCPI",
    version="1.0.0",
    description="Implementation of OCPI (Open Charge Point Interface) for electric vehicle charging stations in Israel.",
)

app.include_router(prefix="/ocpi/2.2.1", router=router)

