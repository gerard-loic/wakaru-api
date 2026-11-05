"""Variables communes à tous les gabarits d'emails de `custom/mails/`.

Le core ne transmet aux gabarits que le contexte de chaque envoi : `setup` (voir
`custom/__init__.py`) enregistre donc ces valeurs comme globales Jinja.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.mail.service import _env


class _MailSettings(BaseSettings):
    """Paramètres des emails, lus dans le `.env` du projet (préfixe `WAKARU_`)."""

    # URL publique du site (sans slash final), ex: https://wakaru.fr
    site_url: str = "https://wakaru.fr"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="WAKARU_", extra="ignore")


mail_settings = _MailSettings()


def register_mail_globals() -> None:
    _env.globals["site_url"] = mail_settings.site_url
