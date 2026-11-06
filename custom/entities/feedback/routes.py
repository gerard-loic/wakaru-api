from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.responses import success_response
from custom.entities.feedback.methods import send_feedback_method


class FeedbackValidator(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    type: Literal["comment", "bug", "remark"]
    message: str = Field(min_length=1, max_length=5000)


def build_router() -> APIRouter:
    router = APIRouter(prefix="/feedback", tags=["feedback"])

    @router.post("")
    def send_feedback(payload: FeedbackValidator, request: Request, db: Session = Depends(get_db)):
        """Envoi d'un commentaire, bug ou remarque par l'utilisateur connecté. Le mail
        part avant la réponse, et non en tâche de fond : en cas d'échec, le front reçoit
        l'erreur et l'utilisateur ne perd pas son message sans le savoir."""
        send_feedback_method(db, request.state.user_id, payload.type, payload.message)
        return success_response(None)

    return router
