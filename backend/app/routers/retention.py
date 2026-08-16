from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.services.retention import prune_old_data, summarize_messages_older_than_retention

router = APIRouter(prefix="/internal/retention", tags=["retention"])


@router.post("/run")
async def run_retention(
    db: AsyncSession = Depends(get_db),
    x_admin_password: str | None = Header(default=None),
):
    if x_admin_password != settings.moderator_shared_password:
        raise HTTPException(status_code=401, detail="Unauthorized")

    summaries = await summarize_messages_older_than_retention(db)
    pruned = await prune_old_data(db)
    return {"summaries_created": summaries, **pruned}
