from fastapi import Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.crud.routes import build_crud_router
from app.database import get_db
from app.exceptions import UnauthorizedError
from app.responses import success_response


class AnswerValidator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool


class DoneValidator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day: str
    index: int = Field(ge=0)


def build_router(model, methods, *, create_validator, update_validator):
    router = build_crud_router(
        model, methods, create_validator=create_validator, update_validator=update_validator
    )

    @router.post("/{item_id}/answer")
    def answer(item_id: str, payload: AnswerValidator, request: Request, db: Session = Depends(get_db)):
        user_id = getattr(request.state, "user_id", None)
        if user_id is None:
            raise UnauthorizedError("Utilisateur non authentifié.")
        obj = methods.answer(db, model.cast_pk(item_id), user_id, payload.success)
        return success_response(obj)

    @router.post("/{item_id}/read")
    def read(item_id: str, request: Request, db: Session = Depends(get_db)):
        user_id = getattr(request.state, "user_id", None)
        if user_id is None:
            raise UnauthorizedError("Utilisateur non authentifié.")
        obj = methods.read(db, model.cast_pk(item_id), user_id)
        return success_response(obj)

    @router.post("/{item_id}/done")
    def done(item_id: str, payload: DoneValidator, request: Request, db: Session = Depends(get_db)):
        user_id = getattr(request.state, "user_id", None)
        if user_id is None:
            raise UnauthorizedError("Utilisateur non authentifié.")
        obj = methods.done(db, model.cast_pk(item_id), user_id, payload.day, payload.index)
        return success_response(obj)

    return router
