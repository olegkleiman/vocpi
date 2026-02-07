from fastapi import APIRouter

router = APIRouter()

from .routes.modules.tokens.authorize import authorize_token # This registers the @router.post("/tokens/authorize") decorator
from .routes.modules.locations.locations import get_locations