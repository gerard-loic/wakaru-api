"""Vérification côté serveur d'un jeton captcha (Cloudflare Turnstile par défaut).

Le front affiche le widget avec la clé publique (site key) et envoie le jeton obtenu
avec le formulaire ; l'API le valide ici auprès du fournisseur avec la clé secrète.
hCaptcha et reCAPTCHA exposent la même API (`secret` + `response` en POST, réponse
JSON avec `success`) : il suffit de changer `captcha_verify_url`.
"""

import logging

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.exceptions import ApiError

logger = logging.getLogger("sylo_api")


class _CaptchaSettings(BaseSettings):
    """Paramètres du captcha, lus dans le `.env` du projet (préfixe `WAKARU_`)."""

    # Clé secrète du fournisseur. Vide = toute vérification échoue (fail-closed).
    captcha_secret: str = ""
    captcha_verify_url: str = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    captcha_timeout: float = 5.0

    model_config = SettingsConfigDict(env_file=".env", env_prefix="WAKARU_", extra="ignore")


captcha_settings = _CaptchaSettings()


class CaptchaError(ApiError):
    status_code = 400
    code = "invalid_captcha"


def verify_captcha(token: str) -> None:
    """Lève `CaptchaError` si le jeton est absent, invalide, expiré ou déjà utilisé
    (un jeton Turnstile n'est valable qu'une fois et 300 secondes)."""
    if not captcha_settings.captcha_secret:
        logger.error("WAKARU_CAPTCHA_SECRET non configuré : vérification captcha impossible.")
        raise CaptchaError("Captcha invalide.")
    if not token:
        raise CaptchaError("Captcha invalide.")

    try:
        response = httpx.post(
            captcha_settings.captcha_verify_url,
            data={"secret": captcha_settings.captcha_secret, "response": token},
            timeout=captcha_settings.captcha_timeout,
        )
        response.raise_for_status()
        result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Vérification captcha impossible : %s", exc)
        raise CaptchaError("Captcha invalide.") from exc

    if not result.get("success"):
        raise CaptchaError("Captcha invalide.", details=result.get("error-codes"))
