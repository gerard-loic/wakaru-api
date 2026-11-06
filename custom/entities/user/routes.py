from fastapi import BackgroundTasks, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError
from sqlalchemy.orm import Session

from app.auth import mark_public
from app.database import get_db
from app.entities.user.routes import _parse_with, build_router as build_core_router
from app.exceptions import UnauthorizedError
from app.responses import success_response
from custom.libs.captchahelper import verify_captcha


class RegisterValidator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    # Consentement aux mails : décoché par défaut, le front doit l'envoyer explicitement.
    is_mailing_allowed: bool = False
    # Jeton renvoyé par le widget captcha du front (Turnstile : champ cf-turnstile-response).
    captcha_token: str = Field(min_length=1)


class ForgotPasswordValidator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    captcha_token: str = Field(min_length=1)


class ResetPasswordValidator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        # bcrypt refuse les mots de passe de plus de 72 octets. Pas de ValueError ici :
        # elle finirait dans `ctx`, que le handler de validation ne sait pas sérialiser.
        if len(value.encode("utf-8")) > 72:
            raise PydanticCustomError(
                "password_too_long", "Le mot de passe ne doit pas dépasser 72 octets."
            )
        return value


class UnsubscribeValidator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1, max_length=255)


class UpdateMeValidator(BaseModel):
    """Champs modifiables par l'utilisateur sur son propre compte. Liste blanche : ni
    `roles`, ni `level_id`, ni `initial_token`. Les champs sont optionnels mais `null`
    est refusé (seule l'absence du champ signifie « ne pas modifier »)."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(None, min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    first_name: str = Field(None, min_length=1, max_length=100)
    last_name: str = Field(None, min_length=1, max_length=100)
    password: str = Field(None, min_length=8, max_length=128)
    is_mailing_allowed: bool = Field(None)
    # Obligatoire pour changer `email` ou `password` (voir UserMethods.update_me).
    current_password: str = Field(None, min_length=1)


def build_router(model, methods, *, create_validator, update_validator):
    router = build_core_router(
        model, methods, create_validator=create_validator, update_validator=update_validator
    )

    @router.post("/register")
    def register(payload: RegisterValidator, db: Session = Depends(get_db)):
        """Création de compte depuis le front : public, protégé par captcha. Le compte
        reçoit le rôle USER (et donc ses connaissances par défaut) et le niveau par
        défaut ; l'email de bienvenue est envoyé par le create du core."""
        verify_captcha(payload.captcha_token)
        data = payload.model_dump(exclude={"captcha_token"})
        obj = methods.register(db, data)
        return success_response(obj)

    mark_public(f"{model.prefix()}/register", "POST")

    @router.post("/forgot-password")
    def forgot_password(payload: ForgotPasswordValidator, background_tasks: BackgroundTasks):
        """Demande de réinitialisation : public, protégé par captcha. La réponse est la
        même que le compte existe ou non ; le mail part en tâche de fond."""
        verify_captcha(payload.captcha_token)
        background_tasks.add_task(methods.send_password_reset, payload.email)
        return success_response(None)

    mark_public(f"{model.prefix()}/forgot-password", "POST")

    @router.post("/reset-password")
    def reset_password(payload: ResetPasswordValidator, db: Session = Depends(get_db)):
        """Saisie du nouveau mot de passe avec le token reçu par mail : public, le token
        fait office d'authentification."""
        methods.reset_password(db, payload.token, payload.password)
        return success_response(None)

    mark_public(f"{model.prefix()}/reset-password", "POST")

    @router.post("/unsubscribe")
    def unsubscribe(payload: UnsubscribeValidator, db: Session = Depends(get_db)):
        """Désinscription depuis le lien des emails d'information : public, le token
        fait office d'authentification. En POST car les scanners de messagerie ouvrent
        les liens des mails : c'est la page du front qui appelle cette route."""
        methods.unsubscribe(db, payload.token)
        return success_response(None)

    mark_public(f"{model.prefix()}/unsubscribe", "POST")

    @router.get("/me")
    def get_me(
        request: Request,
        with_: str | None = Query(
            None, alias="with", description="Relations à charger, séparées par des virgules"
        ),
        db: Session = Depends(get_db),
    ):
        user_id = getattr(request.state, "user_id", None)
        if user_id is None:
            raise UnauthorizedError("Utilisateur non authentifié.")
        obj = methods.get_or_404(db, user_id, with_=_parse_with(with_))
        return success_response(obj)

    @router.put("/me")
    def update_me(
        payload: UpdateMeValidator,
        request: Request,
        with_: str | None = Query(
            None, alias="with", description="Relations à charger, séparées par des virgules"
        ),
        db: Session = Depends(get_db),
    ):
        user_id = getattr(request.state, "user_id", None)
        if user_id is None:
            raise UnauthorizedError("Utilisateur non authentifié.")
        data = payload.model_dump(exclude_unset=True)
        obj = methods.update_me(db, user_id, data, with_=_parse_with(with_))
        return success_response(obj)

    @router.delete("/me")
    def delete_me(request: Request, db: Session = Depends(get_db)):
        """Suppression logique et anonymisation du compte connecté. Ses tokens sont
        refusés dès lors que l'utilisateur est supprimé (voir `resolve_user_id`)."""
        user_id = getattr(request.state, "user_id", None)
        if user_id is None:
            raise UnauthorizedError("Utilisateur non authentifié.")
        methods.delete(db, user_id)
        return success_response(None)

    # Les routes /{item_id} sont déclarées par le core avant nous et captureraient
    # "/me" (le PUT du core est même public) : on remonte les routes /me en tête pour
    # qu'elles soient évaluées en premier.
    me_path = f"{model.prefix()}/me"
    router.routes.sort(key=lambda route: route.path != me_path)

    return router
