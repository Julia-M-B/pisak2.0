"""
Locating and, when needed, downloading prediction model files.

Large model weights (`*.pt`) are not shipped inside the package: they would bloat
the wheel and the git history. Instead they are hosted as release assets and fetched
on first use into a per-user cache directory. Small files needed for every run - the
tokenizer and the fallback unigram list - are bundled in the package.

A file is resolved in this order (first hit wins):

1. ``AAC_MODELS_DIR`` environment variable, if it points at a directory holding the
   file - lets a researcher pin a specific local copy.
2. The models directory bundled in the package - present in a source checkout and
   for the small bundled files.
3. The per-user cache - where previously downloaded files live.
4. Download from the manifest into the cache, verifying its SHA-256.

If none of these yields the file, a FileNotFoundError explains what to do.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import urllib.error
import urllib.request
from importlib.resources import files
from pathlib import Path
from typing import Optional

from aac_app.logging_config import get_module_logger

logger = get_module_logger(file_name="predictions", logger_name=__name__)

#: Environment variable pointing at a directory of model files to use as-is.
MODELS_DIR_ENV_VAR = "AAC_MODELS_DIR"


class ModelDownloadError(RuntimeError):
    """Raised when a model file cannot be downloaded or fails verification."""


MANIFEST: dict[str, dict[str, str]] = {
    "model.pt": {
        "url": "https://github.com/Julia-M-B/master_thesis_app/releases/download/v1.0.0/model.pt",
        "sha256": "3310750f2fd616004089eb4f79fd8c8acefd1342484dbfeb3e822ab669b3217f",
    },
    "fine_tuned_model.pt": {
        "url": "https://github.com/Julia-M-B/master_thesis_app/releases/download/v1.0.0/fine_tuned_model.pt",
        "sha256": "58f3fcb399b3928da0a84053cf24b057316302049494ae9ee06e16edf302da28",
    },
}


def _bundled_models_dir() -> Path:
    """Directory holding model files shipped inside the package."""
    return Path(str(files("aac_app").joinpath("models")))


def get_cache_dir() -> Path:
    """
    Return the per-user cache directory for downloaded models, creating it.

    Honours ``XDG_CACHE_HOME`` and falls back to ``~/.cache`` (XDG default).
    """
    base = os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")
    cache = Path(base) / "aac_app" / "models"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify(path: Path, expected_sha256: str) -> bool:
    actual = _sha256(path)
    if actual != expected_sha256:
        logger.error(
            "Checksum mismatch for %s: expected %s, got %s",
            path.name,
            expected_sha256,
            actual,
        )
        return False
    return True


def _download(filename: str, entry: dict[str, str]) -> Path:
    """
    Download a manifest file into the cache and verify it.

    The file is streamed to a temporary file and only moved into place once the
    checksum matches, so an interrupted download never leaves a half-written file
    that later looks complete.
    """
    url = entry.get("url")
    if not url:
        raise ModelDownloadError(
            f"No download URL configured for '{filename}'. Add it to MANIFEST in "
            f"{__name__} or place the file in the cache "
            f"directory ({get_cache_dir()}) manually."
        )

    expected = entry["sha256"]
    cache_dir = get_cache_dir()
    target = cache_dir / filename

    logger.info("Downloading model '%s' from %s", filename, url)
    tmp_fd, tmp_name = tempfile.mkstemp(dir=cache_dir, suffix=".part")
    tmp_path = Path(tmp_name)
    try:
        os.close(tmp_fd)
        try:
            _stream_to_file(url, tmp_path)
        except (urllib.error.URLError, OSError) as exc:
            raise ModelDownloadError(
                f"Failed to download '{filename}' from {url}: {exc}"
            ) from exc

        if not _verify(tmp_path, expected):
            raise ModelDownloadError(
                f"Downloaded '{filename}' failed checksum verification; "
                f"the file may be corrupted or the manifest is out of date."
            )

        os.replace(tmp_path, target)
        logger.info("Model '%s' downloaded to %s", filename, target)
        return target
    finally:
        tmp_path.unlink(missing_ok=True)


def _stream_to_file(url: str, target: Path) -> None:
    """Stream a URL to a file, logging progress for large downloads."""
    with urllib.request.urlopen(url) as response:  # noqa: S310 - trusted release URL
        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        next_report = 10
        with open(target, "wb") as out:
            for chunk in iter(lambda: response.read(1024 * 256), b""):
                out.write(chunk)
                downloaded += len(chunk)
                if total:
                    percent = downloaded * 100 // total
                    if percent >= next_report:
                        logger.info("  ... %s%% (%s bytes)", percent, downloaded)
                        next_report += 10


def resolve_model_file(filename: str, *, allow_download: bool = True) -> Path:
    """
    Return a local path to a model file, downloading it if necessary.

    :param filename: File to locate, e.g. "model.pt" or "spm_pl.model"
    :param allow_download: If False, never hit the network (used for tests)
    :raises FileNotFoundError: if the file cannot be located or fetched
    """
    # 1. Explicit directory override.
    override = os.environ.get(MODELS_DIR_ENV_VAR)
    if override:
        candidate = Path(override) / filename
        if candidate.is_file():
            return candidate

    # 2. Bundled with the package (source checkout, and small bundled files).
    bundled = _bundled_models_dir() / filename
    if bundled.is_file():
        return bundled

    # 3. Previously downloaded into the cache.
    cached = get_cache_dir() / filename
    if cached.is_file():
        entry = MANIFEST.get(filename)
        # If we know the expected checksum, make sure the cached copy is intact.
        if entry is None or _verify(cached, entry["sha256"]):
            return cached
        logger.warning("Cached '%s' is corrupted; re-downloading", filename)

    # 4. Download per manifest.
    entry = MANIFEST.get(filename)
    if entry is not None and allow_download:
        return _download(filename, entry)

    raise FileNotFoundError(
        f"Could not find model file '{filename}'. It is not bundled, not in the "
        f"cache ({get_cache_dir()}), and "
        + (
            "has no download URL configured."
            if entry is not None
            else "is not listed in the download manifest."
        )
        + f" You can also point {MODELS_DIR_ENV_VAR} at a directory containing it."
    )


def prefetch_models(names: Optional[list[str]] = None) -> None:
    """
    Ensure the given model files are available locally, downloading if needed.

    Intended for a setup/CLI step so a machine can be prepared before going offline.
    Defaults to every file listed in the manifest.
    """
    for name in names if names is not None else list(MANIFEST):
        path = resolve_model_file(name)
        logger.info("Model '%s' available at %s", name, path)
