from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def setup(app: FastAPI) -> None:
    from custom.libs.mailhelper import register_mail_globals
    from custom.libs.mediahelper import media_settings

    # Montage hors routes FastAPI : non soumis à `enforce_auth`, donc public.
    Path(media_settings.media_dir).mkdir(parents=True, exist_ok=True)
    app.mount(
        media_settings.media_url_path,
        StaticFiles(directory=media_settings.media_dir),
        name="media",
    )
    register_mail_globals()
