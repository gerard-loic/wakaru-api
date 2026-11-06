"""Tokens de désinscription des emails d'information (POST /users/unsubscribe).

Le token n'est pas stocké : il contient l'id de l'utilisateur, signé par HMAC avec
`WAKARU_UNSUBSCRIBE_SECRET`. Il n'expire pas et ne dépend ni de l'email ni du mot de
passe : le lien d'un ancien email doit rester valable.
"""

import hashlib
import hmac
import re

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.exceptions import ApiError

# `users.id` est un INTEGER : au-delà, PostgreSQL rejetterait la requête.
_MAX_USER_ID = 2_147_483_647
_TOKEN_PATTERN = re.compile(r"([0-9]{1,10})\.([0-9a-f]{64})")


class _UnsubscribeSettings(BaseSettings):
    """Paramètres de la désinscription, lus dans le `.env` du projet (préfixe `WAKARU_`)."""

    # Clé de signature des tokens. Vide = aucun token émis ni accepté (fail-closed).
    unsubscribe_secret: str = ""
    # Préfixe de l'URL envoyée par mail, le token est ajouté à la suite.
    unsubscribe_url_prefix: str = "https://wakaru.fr/desabonnement?token="

    model_config = SettingsConfigDict(env_file=".env", env_prefix="WAKARU_", extra="ignore")


unsubscribe_settings = _UnsubscribeSettings()


class InvalidUnsubscribeTokenError(ApiError):
    status_code = 400
    code = "invalid_unsubscribe_token"

    def __init__(self):
        super().__init__("Lien de désinscription invalide.")


def _sign(user_id: int) -> str:
    return hmac.new(
        unsubscribe_settings.unsubscribe_secret.encode("utf-8"),
        f"unsubscribe.{user_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_unsubscribe_url(user_id: int) -> str:
    """Lève `ApiError` si le secret manque : mieux vaut ne pas envoyer le mail que
    l'envoyer sans lien de désinscription."""
    if not unsubscribe_settings.unsubscribe_secret:
        raise ApiError("WAKARU_UNSUBSCRIBE_SECRET non configuré.")
    return f"{unsubscribe_settings.unsubscribe_url_prefix}{user_id}.{_sign(user_id)}"


def read_unsubscribe_token(token: str) -> int:
    """Renvoie l'id de l'utilisateur, ou lève `InvalidUnsubscribeTokenError` si le token
    est mal formé ou mal signé."""
    if not unsubscribe_settings.unsubscribe_secret:
        raise InvalidUnsubscribeTokenError()
    match = _TOKEN_PATTERN.fullmatch(token)
    if match is None or int(match[1]) > _MAX_USER_ID:
        raise InvalidUnsubscribeTokenError()
    user_id = int(match[1])
    if not hmac.compare_digest(match[2], _sign(user_id)):
        raise InvalidUnsubscribeTokenError()
    return user_id
