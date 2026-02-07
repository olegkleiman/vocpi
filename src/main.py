from fastapi import FastAPI

from py_ocpi import get_application
from py_ocpi.core.enums import RoleEnum, ModuleID
from py_ocpi.modules.versions.enums import VersionNumber
from py_ocpi.core.config import settings

from .router import router

# from .auth import ClientAuthenticator
# from .crud import AppCrud

# app = get_application(
#     version_numbers=[VersionNumber.v_2_2_1],
#     roles=[RoleEnum.cpo, RoleEnum.emsp],
#     # modules=[ModuleID.locations, ModuleID.tokens, ModuleID.sessions],
#     # authenticator=ClientAuthenticator,
#     crud=AppCrud,
# )

app = FastAPI(
    title=settings.OCPI_PREFIX,
    version="1.0.0",
    description="Implementation of OCPI (Open Charge Point Interface) for electric vehicle charging stations in Israel.",
)

app.include_router(prefix="/ocpi/2.2.1", router=router)

# app.include_router(#prefix=settings.OCPI_PREFIX,
#                    "/ocpi/2.2.1", 
#                    router)


