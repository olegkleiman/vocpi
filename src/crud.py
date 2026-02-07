from typing import Any, Tuple

# from py_ocpi.core.config import logger
from py_ocpi.core.crud import Crud
from py_ocpi.core.enums import ModuleID, RoleEnum, Action

from .db import DbInterface

class AppCrud(Crud):
    """Class contains crud business logic."""

    @classmethod
    async def get(
        cls, module: ModuleID, role: RoleEnum, id, *args, **kwargs
    ) -> dict | None:
        """Return single obj from db."""
        # logger.info(
        #     'Get single obj -> module - `%s`, role - `%s`, version - `%s`'
        #     % (module, role, kwargs.get("version", ""))
        # )
        return await DbInterface.get(module, id, *args, **kwargs)
    
    @classmethod
    async def list(
        cls, module: ModuleID, role: RoleEnum, filters: dict, *args, **kwargs
    ) -> tuple[list[dict], int, bool]:
        """Return list of obj from db."""
        # logger.info(
        #     'Get list of objs -> module - `%s`, role - `%s`, version - `%s`'
        #     % (module, role, kwargs.get("version", ""))
        # )
        data_list, total, is_last_page = await DbInterface.get_all(
            module, filters, *args, **kwargs
        )
        return data_list, total, is_last_page    