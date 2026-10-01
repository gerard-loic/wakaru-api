"""Filtrage générique "connaissance utilisateur", réutilisable par n'importe
quelle entité (hiragana, katakana, kanji, word, ...).

Par défaut, `list`/`get`/`QUERY` ne renvoient que les lignes sur lesquelles
l'utilisateur courant a une ligne dans `user_knowledges` (`entity_name` =
`model.name`, `entity_id` = l'id de la ligne, `user_id` = l'utilisateur
courant) — sauf s'il a la permission libre `KNOWLEDGE_UNLIMITED` (voir
`config/generate-config.json`, `additionnal.permissions`), auquel cas rien
n'est filtré. `create`/`update`/`delete` ne sont pas concernées.

Ce module ne fait pas partie du framework Sylo : c'est une lib du projet
(`custom/libs/`), importable par n'importe quel `custom/entities/<nom>/routes.py`.

Usage (voir `custom/entities/hiragana/routes.py`) :

    from custom.libs.knowledge_gating import build_knowledge_gated_router

    def build_router(model, methods, *, create_validator, update_validator):
        return build_knowledge_gated_router(
            model, methods, create_validator=create_validator, update_validator=update_validator
        )
"""

from typing import Type

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.auth import user_has_permission
from app.config import get_settings
from app.crud.filters import compile_filter
from app.crud.methods import BaseCRUDMethods
from app.crud.model import EntityModel, get_model
from app.crud.ordering import compile_order_by
from app.crud.routes import build_crud_router
from app.database import get_db
from app.exceptions import NotFoundError
from app.responses import success_response

_settings = get_settings()

KNOWLEDGE_UNLIMITED_UID = "KNOWLEDGE_UNLIMITED"

_ORDERBY_DESCRIPTION = (
    "Tri, ex: email.ASC ou email.DESC (plusieurs champs séparés par des virgules)."
)
_FILTER_DESCRIPTION = (
    "Expression de filtre sur les colonnes de l'entité, ex: \"status == 'active'\"."
)


def _parse_with(with_: str | None) -> list[str]:
    if not with_:
        return []
    return [item.strip() for item in with_.split(",") if item.strip()]


def _resolve_offset(page: int | None, offset: int, limit: int) -> int:
    if page is not None:
        return (page - 1) * limit
    return offset


class _QueryPayload(BaseModel):
    filter: str | None = Field(default=None, description=_FILTER_DESCRIPTION)
    limit: int = Field(default=_settings.default_page_size, ge=1, le=_settings.max_page_size)
    offset: int = Field(default=0, ge=0)
    page: int | None = Field(default=None, ge=1)
    orderby: str | None = Field(default=None, description=_ORDERBY_DESCRIPTION)
    with_: list[str] | None = Field(default=None, alias="with")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


def _known_entity_ids_clause(model: type[EntityModel], user_id: int) -> ColumnElement:
    user_knowledge = get_model("user_knowledge")
    known_ids = select(user_knowledge.table.c.entity_id).where(
        user_knowledge.table.c.entity_name == model.name,
        user_knowledge.table.c.user_id == user_id,
        user_knowledge.table.c.deleted_at.is_(None),
    )
    return model.pk_column.in_(known_ids)


def _knowledge_filter(db: Session, request: Request, model: type[EntityModel]) -> ColumnElement | None:
    """`None` si l'utilisateur voit tout (permission KNOWLEDGE_UNLIMITED), sinon la
    clause à combiner en AND pour ne garder que les lignes qu'il connaît déjà."""
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        # Ne devrait pas arriver (auth globale obligatoire), mais ne rien
        # divulguer par défaut plutôt que planter.
        return model.pk_column.is_(None)
    if user_has_permission(db, user_id, KNOWLEDGE_UNLIMITED_UID):
        return None
    return _known_entity_ids_clause(model, user_id)


def _combine(user_clause: ColumnElement | None, knowledge_clause: ColumnElement | None) -> ColumnElement | None:
    if user_clause is not None and knowledge_clause is not None:
        return and_(user_clause, knowledge_clause)
    return knowledge_clause if user_clause is None else user_clause


def build_knowledge_gated_router(
    model: type[EntityModel],
    methods: BaseCRUDMethods,
    *,
    create_validator: Type[BaseModel],
    update_validator: Type[BaseModel],
) -> APIRouter:
    """Équivalent de `build_crud_router`, mais les routes `list`/`get`/`QUERY` sont
    restreintes aux lignes connues de l'utilisateur courant (voir le docstring du
    module). `create`/`update`/`delete` sont déléguées telles quelles."""
    router = build_crud_router(
        model,
        methods,
        create_validator=create_validator,
        update_validator=update_validator,
        enabled=("create", "update", "delete"),
    )

    @router.get("")
    def list_items(
        request: Request,
        limit: int = Query(_settings.default_page_size, ge=1, le=_settings.max_page_size),
        offset: int = Query(0, ge=0),
        page: int | None = Query(None, ge=1, description="Page affichée (1-indexée, prime sur offset)"),
        orderby: str | None = Query(None, description=_ORDERBY_DESCRIPTION),
        with_: str | None = Query(
            None, alias="with", description="Relations à charger, séparées par des virgules"
        ),
        db: Session = Depends(get_db),
    ):
        resolved_offset = _resolve_offset(page, offset, limit)
        order_clauses = compile_order_by(orderby, model) if orderby else None
        items, total = methods.list(
            db,
            limit=limit,
            offset=resolved_offset,
            with_=_parse_with(with_),
            filter_clause=_knowledge_filter(db, request, model),
            order_by=order_clauses,
        )
        return success_response(
            items,
            meta={
                "total": total,
                "limit": limit,
                "offset": resolved_offset,
                "page": resolved_offset // limit + 1,
            },
        )

    def _run_query(payload: _QueryPayload, request: Request, db: Session):
        user_clause = compile_filter(payload.filter, model) if payload.filter else None
        filter_clause = _combine(user_clause, _knowledge_filter(db, request, model))
        order_clauses = compile_order_by(payload.orderby, model) if payload.orderby else None
        resolved_offset = _resolve_offset(payload.page, payload.offset, payload.limit)
        items, total = methods.list(
            db,
            limit=payload.limit,
            offset=resolved_offset,
            with_=payload.with_ or [],
            filter_clause=filter_clause,
            order_by=order_clauses,
        )
        return success_response(
            items,
            meta={
                "total": total,
                "limit": payload.limit,
                "offset": resolved_offset,
                "page": resolved_offset // payload.limit + 1,
            },
        )

    @router.api_route("", methods=["QUERY"])
    def query_items(payload: _QueryPayload, request: Request, db: Session = Depends(get_db)):
        return _run_query(payload, request, db)

    @router.post("/query")
    def query_items_fallback(payload: _QueryPayload, request: Request, db: Session = Depends(get_db)):
        # Repli pour les clients/proxys qui ne relaient pas encore la méthode HTTP QUERY.
        return _run_query(payload, request, db)

    @router.get("/{item_id}")
    def get_item(
        item_id: str,
        request: Request,
        with_: str | None = Query(
            None, alias="with", description="Relations à charger, séparées par des virgules"
        ),
        db: Session = Depends(get_db),
    ):
        casted_id = model.cast_pk(item_id)
        knowledge_clause = _knowledge_filter(db, request, model)
        if knowledge_clause is not None:
            visible = (
                db.query(model.pk_column)
                .filter(model.pk_column == casted_id, knowledge_clause)
                .first()
            )
            if visible is None:
                raise NotFoundError(model.name, item_id)
        obj = methods.get_or_404(db, casted_id, with_=_parse_with(with_))
        return success_response(obj)

    return router
