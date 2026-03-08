import logging
from fastapi import Depends, Request, HTTPException
from sqlalchemy import select

logger = logging.getLogger(__name__)
from ....router import router, api_router

from sqlalchemy.ext.asyncio import AsyncSession
from ....database import get_db
from ....models import CDRModel, CDRResponse

@api_router.get("/receipts/{session_id}", tags=["Custom API"])
async def get_receipt(request: Request,
                  session_id: str, # Actually, this is session_request_id.
                  db: AsyncSession = Depends(get_db)) -> CDRResponse:
    smt = (
        select(CDRModel)
        .where(CDRModel.session_request_id == session_id)
    )
    result = await db.execute(smt)
    cdr_row = (await db.execute(smt)).scalars().first()

    if not cdr_row:
        raise HTTPException(
            status_code=404, 
            detail=f"CDR for session_id '{session_id}' not found."
        )
    
    raw_json = cdr_row.cdr
    
    cdr = CDRResponse(
                      cdr_id = cdr_row.cdr_id,
                      session_id = session_id)
                      
    return cdr


