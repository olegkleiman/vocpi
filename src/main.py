from enum import Enum
import logging
import os
import sys
from fastapi import FastAPI, Request
from sqlalchemy.exc import OperationalError
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

from .router import router, api_router

logger = logging.getLogger(__name__)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger.setLevel(LOG_LEVEL)
console_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(console_handler)

import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

class VersionNumber(str, Enum):
    """
    https://github.com/ocpi/ocpi/blob/2.2.1/version_information_endpoint.asciidoc#125-versionnumber-enum
    """
    v_2_0 = '2.0'
    v_2_1 = '2.1'
    v_2_1_1 = '2.1.1'
    v_2_2 = '2.2'
    v_2_2_1 = '2.2.1'        
    v_2_2_2 = '2.2.2'
    latest = '2.2.1'

OCPI_PREFIX: str = 'ocpi'

class DatabaseTimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:

            logger.info(f"=== Incoming Request: {request.method} {request.url} ===")
            for key, value in request.headers.items():
                logger.info(f"  {key}: {value}")

            auth_header = request.headers["Authorization"]
            if auth_header:
                token = auth_header.split("Token")
                logger.info(f"Token: {token}")

            response = await call_next(request)

            # Log response headers
            logger.info(f"=== Response: {response.status_code} ===")
            for key, value in response.headers.items():
                logger.info(f"  {key}: {value}")

            return response
        except OperationalError as exc:
            if "connection timeout expired" in str(exc):
                return JSONResponse(
                    status_code=504,
                    content={"detail": "Database connection timed out (Check VPN/Firewall)"}
                )
            raise exc

app = FastAPI(
    title=OCPI_PREFIX,
    version="1.0.0",
    description="Implementation of OCPI (Open Charge Point Interface) for electric vehicle charging stations in Israel.",
)
app.add_middleware(DatabaseTimeoutMiddleware)

@app.exception_handler(Exception) #OperationalError)
async def handle_operational_error(request: Request, 
                                   exc: OperationalError):
    pass

prefix = f"/{OCPI_PREFIX}/{VersionNumber.v_2_2_1.value}"
app.include_router(router, prefix=prefix)
app.include_router(api_router, prefix="/api", tags=["Custom API"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=1
    )