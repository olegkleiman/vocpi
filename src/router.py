from fastapi import APIRouter

router = APIRouter()

from .routes.modules.tokens.validate import validate_token # This registers the @router.post("/tokens/validate") decorator
from .routes.modules.locations.locations import get_locations