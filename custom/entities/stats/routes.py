from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.responses import success_response
from custom.entities.stats.methods import stats_items_method



def build_router() -> APIRouter:
    router = APIRouter(prefix="/stats", tags=["stats"])

    @router.get("/items")
    def stats_items(request: Request, db: Session = Depends(get_db)):
        user_id = getattr(request.state, "user_id", None)
        result = stats_items_method(db, user_id)
        return success_response(result)

    return router
