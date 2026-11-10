"""Tokens de sortie du mode vacances (POST /users/resume).

Un utilisateur en vacances (`is_onvacation`) ne reçoit pas les nouveaux thèmes, mais
reçoit quand même leur annonce, avec un lien pour se remettre en actif et activer ce
thème. Le token n'est pas stocké : il contient l'id de l'utilisateur et celui du thème,
signés par HMAC. Il n'expire pas : le lien d'un ancien email doit rester valable.

La clé est `WAKARU_UNSUBSCRIBE_SECRET`, déjà requise pour envoyer l'annonce. Le message
signé commence par `resume.` : un token de désinscription ne peut pas servir ici, ni
l'inverse.
"""

import hashlib
import hmac
import re

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.exceptions import ApiError
from custom.libs.unsubscribehelper import unsubscribe_settings

# `users.id` et `themes.id` sont des INTEGER : au-delà, PostgreSQL rejetterait la requête.
_MAX_ID = 2_147_483_647
_TOKEN_PATTERN = re.compile(r"([0-9]{1,10})\.([0-9]{1,10})\.([0-9a-f]{64})")


class _VacationSettings(BaseSettings):
    """Paramètres du mode vacances, lus dans le `.env` du projet (préfixe `WAKARU_`)."""

    # Préfixe de l'URL envoyée par mail, le token est ajouté à la suite.
    resume_url_prefix: str = "https://wakaru.fr/reprise?token="

    model_config = SettingsConfigDict(env_file=".env", env_prefix="WAKARU_", extra="ignore")


vacation_settings = _VacationSettings()


class InvalidResumeTokenError(ApiError):
    status_code = 400
    code = "invalid_resume_token"

    def __init__(self):
        super().__init__("Lien de reprise invalide.")


def _sign(user_id: int, theme_id: int) -> str:
    return hmac.new(
        unsubscribe_settings.unsubscribe_secret.encode("utf-8"),
        f"resume.{user_id}.{theme_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_resume_url(user_id: int, theme_id: int) -> str:
    """Lève `ApiError` si le secret manque."""
    if not unsubscribe_settings.unsubscribe_secret:
        raise ApiError("WAKARU_UNSUBSCRIBE_SECRET non configuré.")
    return f"{vacation_settings.resume_url_prefix}{user_id}.{theme_id}.{_sign(user_id, theme_id)}"


def read_resume_token(token: str) -> tuple[int, int]:
    """Renvoie `(user_id, theme_id)`, ou lève `InvalidResumeTokenError` si le token est
    mal formé ou mal signé."""
    if not unsubscribe_settings.unsubscribe_secret:
        raise InvalidResumeTokenError()
    match = _TOKEN_PATTERN.fullmatch(token)
    if match is None or int(match[1]) > _MAX_ID or int(match[2]) > _MAX_ID:
        raise InvalidResumeTokenError()
    user_id, theme_id = int(match[1]), int(match[2])
    if not hmac.compare_digest(match[3], _sign(user_id, theme_id)):
        raise InvalidResumeTokenError()
    return user_id, theme_id
