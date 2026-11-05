"""Stockage local de médias (images...) servis publiquement sur `media_url_path`.

Les fichiers sont écrits dans `media_dir` et exposés sans authentification par le
montage `StaticFiles` déclaré dans `custom/__init__.py` (`setup`). L'URL publique
renvoyée est `media_base_url` + `media_url_path` + chemin relatif du fichier.
"""

import logging
import re
import time
import uuid
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict


class _MediaSettings(BaseSettings):
    """Paramètres de stockage, lus dans le `.env` du projet (préfixe `WAKARU_`)."""

    # Dossier de stockage (relatif au dossier de lancement, /app en Docker).
    media_dir: str = "media"
    # Chemin sur lequel les fichiers sont servis.
    media_url_path: str = "/media"
    # URL publique de l'API (sans slash final), ex: http://wakaru-api.diatem.local
    media_base_url: str = ""
    # Taille maximale d'un fichier téléchargé, en octets.
    media_max_size: int = 10 * 1024 * 1024

    model_config = SettingsConfigDict(env_file=".env", env_prefix="WAKARU_", extra="ignore")


media_settings = _MediaSettings()

_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}

# Largeurs de miniatures acceptées par upload.wikimedia.org : toute autre largeur est
# rejetée en 400 (voir https://www.mediawiki.org/wiki/Common_thumbnail_sizes).
_WIKIMEDIA_STEPS = [20, 40, 60, 120, 250, 330, 500, 960, 1280, 1920, 3840]
# .../thumb/<a>/<ab>/<Fichier>/<prefixe><largeur>px-<Fichier>[.png]
_WIKIMEDIA_THUMB = re.compile(r"^(https?://(?:upload|thumb)\.wikimedia\.org/.+?)/thumb(/.+)/([^/]*?)(\d+)px-([^/]+)$")

# La politique de Wikimedia impose un User-Agent identifiant le client et un contact
_USER_AGENT = "wakaru-api/1.0 (https://e-kodo.fr; loic.gerard@e-kodo.fr)"

# Nouvelles tentatives sur les erreurs passagères (429, 5xx, timeouts)
_MAX_ATTEMPTS = 3
_RETRY_BASE_DELAY = 1.0
# Un Retry-After plus long abandonne la tentative : l'import bloque la requête en cours.
_RETRY_MAX_DELAY = 30.0


class MediaHelper:
    def __init__(self):
        self._dir = Path(media_settings.media_dir)
        self._logger = logging.getLogger("sylo_api.mediahelper")

    def downloadImage(self, url: str, subdir: str = "") -> str:
        """Télécharge l'image `url`, la stocke dans `media_dir/subdir` et renvoie son
        URL publique. Lève une exception si le téléchargement échoue ou si le contenu
        n'est pas une image supportée."""
        candidates = self._getCandidateUrls(url.strip())
        for i, candidate in enumerate(candidates):
            try:
                data, ext = self._fetchWithRetry(candidate)
                break
            except (httpx.HTTPError, ValueError) as e:
                if i == len(candidates) - 1:
                    raise
                #error : le logger sylo_api ignore les niveaux inférieurs
                self._logger.error("Échec %s (%r), essai suivant", candidate, e)

        folder = self._dir / subdir
        folder.mkdir(parents=True, exist_ok=True)
        filename = uuid.uuid4().hex + ext
        (folder / filename).write_bytes(data)

        relative = f"{subdir}/{filename}" if subdir else filename
        self._logger.info("Image %s stockée dans %s", candidate, folder / filename)
        return self.getPublicUrl(relative)

    def getPublicUrl(self, relative_path: str) -> str:
        return f"{media_settings.media_base_url}{media_settings.media_url_path}/{relative_path}"

    def _fetchWithRetry(self, url: str) -> tuple[bytes, str]:
        """`_fetch` avec nouvelles tentatives sur les erreurs passagères."""
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                return self._fetch(url)
            except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
                delay = self._getRetryDelay(e, attempt)
                if delay is None or attempt == _MAX_ATTEMPTS:
                    raise
                #error : le logger sylo_api ignore les niveaux inférieurs
                self._logger.error("Échec %s (%r), nouvelle tentative dans %.1fs", url, e, delay)
                time.sleep(delay)

    def _getRetryDelay(self, error: httpx.HTTPError, attempt: int) -> float | None:
        """Délai avant la tentative suivante, None si l'erreur ne justifie pas de réessayer."""
        if isinstance(error, httpx.HTTPStatusError):
            status = error.response.status_code
            if status != 429 and status < 500:
                return None
            retry_after = self._parseRetryAfter(error.response.headers.get("retry-after"))
            if retry_after is not None:
                return retry_after if retry_after <= _RETRY_MAX_DELAY else None
        return _RETRY_BASE_DELAY * 2 ** (attempt - 1)

    def _parseRetryAfter(self, value: str | None) -> float | None:
        """Retry-After en secondes : nombre de secondes ou date HTTP."""
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            pass
        try:
            date = parsedate_to_datetime(value)
        except ValueError:
            return None
        return max(0.0, (date - datetime.now(timezone.utc)).total_seconds())

    def _fetch(self, url: str) -> tuple[bytes, str]:
        # User-Agent explicite : Wikimedia refuse les clients anonymes
        headers = {"User-Agent": _USER_AGENT}
        with httpx.stream("GET", url, headers=headers, follow_redirects=True, timeout=30) as r:
            r.raise_for_status()
            content_type = r.headers.get("content-type", "").split(";")[0].strip().lower()
            ext = _EXTENSIONS.get(content_type)
            if ext is None:
                raise ValueError(f"Type de contenu non supporté pour {url} : {content_type}")

            data = bytearray()
            for chunk in r.iter_bytes():
                data.extend(chunk)
                if len(data) > media_settings.media_max_size:
                    raise ValueError(f"Image trop volumineuse : {url}")
        return bytes(data), ext

    def _getCandidateUrls(self, url: str) -> list[str]:
        """URLs à essayer dans l'ordre. Pour une miniature Wikimedia : largeur arrondie
        à la taille standard supérieure, puis fichier original (miniature plus large
        que l'original, refusée par Wikimedia). L'original n'est servi que par
        upload.wikimedia.org : thumb.wikimedia.org redirige vers l'accueil de Commons."""
        m = _WIKIMEDIA_THUMB.match(url)
        if m is None:
            return [url]
        base, path, prefix, width, name = m.groups()
        step = next((s for s in _WIKIMEDIA_STEPS if s >= int(width)), _WIKIMEDIA_STEPS[-1])
        original_base = base.replace("://thumb.wikimedia.org", "://upload.wikimedia.org", 1)
        return [f"{base}/thumb{path}/{prefix}{step}px-{name}", f"{original_base}{path}"]
