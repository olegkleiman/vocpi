from fastapi import APIRouter

router = APIRouter()

from .routes.modules.tokens.validate import validate_token