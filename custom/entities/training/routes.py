from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.responses import success_response
from custom.entities.training.methods import new_training_method, get_configuration_method


class CreateTrainingValidator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str
    element_from:str
    element_to:list
    focus:str
    #Facultatif : par défaut, nb_items du sujet dans TRAININGCONF
    number:int|None = None


def build_router() -> APIRouter:
    router = APIRouter(prefix="/training", tags=["trainings"])

    @router.post("")
    def new_training(payload: CreateTrainingValidator, request: Request, db: Session = Depends(get_db)):
        user_id = getattr(request.state, "user_id", None)
        result = new_training_method(
            db=db,
            user_id=user_id,
            subject=payload.subject,
            element_from=payload.element_from,
            element_to=payload.element_to,
            number=payload.number,
            focus=payload.focus
        )
        return success_response(result)

    @router.get("/configuration")
    def get_configuration(request: Request, db: Session = Depends(get_db)):
        user_id = getattr(request.state, "user_id", None)
        return get_configuration_method(db=db, user_id=user_id)


    return router
