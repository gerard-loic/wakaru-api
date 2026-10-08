from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.responses import success_response
from custom.entities.llm.methods import create_lesson as create_lesson_method


class CreateLessonValidator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme: dict[str, Any]
    vocabulary: list[dict[str, Any]]
    kanji: dict[str, Any]
    kanjiwords: list[dict[str, Any]]
    grammar_rules: dict[str, Any]
    sentences: list[dict[str, Any]]
    exercise: dict[str, Any]


def build_router() -> APIRouter:
    router = APIRouter(prefix="/llm", tags=["llm"])

    @router.post("/createlesson")
    def create_lesson(payload: CreateLessonValidator, db: Session = Depends(get_db)):
        result = create_lesson_method(db, payload.model_dump())
        return success_response(result)

    return router
