from fastapi import APIRouter

router = APIRouter()
api_router = APIRouter()

from .routes.modules.tokens.authorize import authorize_token
from .routes.modules.locations.locations import get_location
from .routes.modules.sessions.sessions import create_session
from .routes.modules.config.config import app_config
from .routes.modules.commands.start_session import start_session, begin_session
from .routes.modules.commands.stop_session  import stop_session


