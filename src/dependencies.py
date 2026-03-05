
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .app_services.session_service import SessionService
from .pubsub import OCPIPubSub

pubsub_manager = OCPIPubSub()

def get_pubsub() -> OCPIPubSub:
    return pubsub_manager

async def get_session_service(db: AsyncSession = Depends(get_db)) -> SessionService:
    return SessionService(db)

