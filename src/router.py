"""
src.router.py

Project: WEV (OCPI+ Server)
Author: Oleg Kleiman
Date: Feb, 2026

"""

from fastapi import APIRouter

router = APIRouter()
api_router = APIRouter()

from .routes.modules.config.config import api_router as config_router
api_router.include_router(config_router)

# Locations module exposes both Custom APIs (e.g. for SSE) and OCPI-defined endpoints, so we need to include both routers
from .routes.modules.locations.locations import router as locations_router, api_router as locations_api_router
router.include_router(locations_router)
api_router.include_router(locations_api_router)

# Sessions module exposes both Custom APIs (e.g. for SSE) and OCPI-defined endpoints, so we need to include both routers
from .routes.modules.sessions.sessions import router as sessions_router, api_router as sessions_api_router
router.include_router(sessions_router)
api_router.include_router(sessions_api_router)

from .routes.modules.commands.start_session import router as start_session_router, api_router as start_session_api_router
router.include_router(start_session_router)
api_router.include_router(start_session_api_router)

from .routes.modules.commands.stop_session  import router as stop_session_router, api_router as stop_session_api_router
api_router.include_router(stop_session_api_router)
router.include_router(stop_session_router)

from .routes.modules.cdrs.cdrs import router as cdrs_router, api_router as cdrs_api_router
router.include_router(cdrs_router)
api_router.include_router(cdrs_api_router)
