from enum import Enum
from fastapi import FastAPI
import uvicorn

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

from .router import router

app = FastAPI(
    title=OCPI_PREFIX,
    version="1.0.0",
    description="Implementation of OCPI (Open Charge Point Interface) for electric vehicle charging stations in Israel.",
)

prefix = f"/{OCPI_PREFIX}/{VersionNumber.v_2_2_1.value}"
app.include_router(router, prefix=prefix)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=1
    )