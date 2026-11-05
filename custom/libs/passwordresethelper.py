"""Tokens de réinitialisation de mot de passe (POST /users/forgot-password).

Le token n'est pas stocké : il contient l'id de l'utilisateur et sa date d'expiration,
signés par HMAC avec `WAKARU_PASSWORD_RESET_SECRET`. La signature couvre aussi le hash
du mot de passe et l'email actuels : changer l'un des deux invalide tous les tokens
déjà émis, ce qui rend chaque token à usage unique.
"""

import hashlib
import hmac
import re
import time

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.exceptions import ApiError

# `users.id` est un INTEGER : au-delà, PostgreSQL rejetterait la requête.
_MAX_USER_ID = 2_147_483_647
_TOKEN_PATTERN = re.compile(r"([0-9]{1,10})\.([0-9]{1,12})\.([0-9a-f]{64})")


class _PasswordResetSettings(BaseSettings):
    """Paramètres de la réinitialisation, lus dans le `.env` du projet (préfixe `WAKARU_`)."""

    # Clé de signature des tokens. Vide = aucun token émis ni accepté (fail-closed).
    password_reset_secret: str = ""
    # Préfixe de l'URL envoyée par mail, le token est ajouté à la suite.
    password_reset_url_prefix: str = "https://wakaru.fr/reinitialisationmotdepasse?token="
    password_reset_ttl_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_prefix="WAKARU_", extra="ignore")


password_reset_settings = _PasswordResetSettings()


class InvalidResetTokenError(ApiError):
    status_code = 400
    code = "invalid_reset_token"

    def __init__(self):
        super().__init__("Lien de réinitialisation invalide ou expiré.")


def _sign(user, expires_at: int) -> str:
    message = f"{user.id}.{expires_at}.{user.password or ''}.{user.email}"
    return hmac.new(
        password_reset_settings.password_reset_secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_reset_token(user) -> str:
    if not password_reset_settings.password_reset_secret:
        raise RuntimeError("WAKARU_PASSWORD_RESET_SECRET non configuré.")
    ttl_seconds = password_reset_settings.password_reset_ttl_minutes * 60
    expires_at = int(time.time()) + ttl_seconds
    return f"{user.id}.{expires_at}.{_sign(user, expires_at)}"


def read_reset_token_user_id(token: str) -> int:
    """Renvoie l'id annoncé par le token, sans le garantir : `check_reset_token` doit
    ensuite valider la signature avec l'utilisateur chargé."""
    match = _TOKEN_PATTERN.fullmatch(token)
    if match is None or int(match[1]) > _MAX_USER_ID:
        raise InvalidResetTokenError()
    return int(match[1])


def check_reset_token(token: str, user) -> None:
    """Lève `InvalidResetTokenError` si le token est expiré, mal signé ou déjà utilisé."""
    if not password_reset_settings.password_reset_secret:
        raise InvalidResetTokenError()
    match = _TOKEN_PATTERN.fullmatch(token)
    if match is None:
        raise InvalidResetTokenError()
    expires_at = int(match[2])
    if not hmac.compare_digest(match[3], _sign(user, expires_at)) or expires_at < time.time():
        raise InvalidResetTokenError()
