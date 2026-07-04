"""
Overlay store for the e-ink dashboard.

Overlays are short-lived content cards (reminders, jokes, images) pushed by
external agents (e.g. Hermes) via the HTTP API in subway_server.py. They are
composited into the rendered BMP alongside the core subway/weather data and
disappear automatically once expired.

Storage is a JSON file next to this module (gitignored) plus a directory of
decoded images. Every overlay MUST have an expiry — nothing lives forever.
"""

import base64
import binascii
import json
import os
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
OVERLAY_FILE = SCRIPT_DIR / "overlays.json"
IMAGE_DIR = SCRIPT_DIR / "overlay_images"

SLOTS = ("banner", "sidebar", "fullscreen")

DEFAULT_TTL_SECONDS = 3600          # 1 hour if caller doesn't specify
MAX_TTL_SECONDS = 7 * 24 * 3600     # hard cap: 7 days
MAX_TITLE_CHARS = 60
MAX_TEXT_CHARS = 500
MAX_IMAGE_BYTES = 512 * 1024        # decoded image size cap

_lock = threading.Lock()


def _now():
    return datetime.now()


def _load():
    try:
        with open(OVERLAY_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (OSError, ValueError):
        pass
    return []


def _save(overlays):
    tmp = OVERLAY_FILE.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(overlays, f, indent=2)
    os.replace(tmp, OVERLAY_FILE)


def _image_path(overlay_id):
    return IMAGE_DIR / f"{overlay_id}.png"


def _delete_image(overlay_id):
    try:
        _image_path(overlay_id).unlink()
    except OSError:
        pass


def _is_expired(o, now=None):
    now = now or _now()
    try:
        return datetime.fromisoformat(o["expires_at"]) <= now
    except (KeyError, ValueError):
        return True  # malformed = expired


def _is_started(o, now=None):
    now = now or _now()
    starts_at = o.get("starts_at")
    if not starts_at:
        return True
    try:
        return datetime.fromisoformat(starts_at) <= now
    except ValueError:
        return True


def _prune(overlays):
    """Drop expired overlays and their images. Returns (kept, changed)."""
    now = _now()
    kept = []
    changed = False
    for o in overlays:
        if _is_expired(o, now):
            _delete_image(o.get("id", ""))
            changed = True
        else:
            kept.append(o)
    return kept, changed


def add(payload):
    """Validate and store a new overlay. Returns the stored overlay dict.

    Raises ValueError with a human-readable message on invalid input.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    slot = payload.get("slot", "banner")
    if slot not in SLOTS:
        raise ValueError(f"slot must be one of {SLOTS}")

    title = (payload.get("title") or "").strip()[:MAX_TITLE_CHARS]
    text = (payload.get("text") or "").strip()[:MAX_TEXT_CHARS]
    image_b64 = payload.get("image_b64")
    if not (title or text or image_b64):
        raise ValueError("overlay needs at least one of: title, text, image_b64")

    try:
        priority = int(payload.get("priority", 0))
    except (TypeError, ValueError):
        raise ValueError("priority must be an integer")

    now = _now()

    # Expiry: accept ttl_seconds or an explicit expires_at ISO timestamp.
    if payload.get("expires_at"):
        try:
            expires_at = datetime.fromisoformat(payload["expires_at"])
        except ValueError:
            raise ValueError("expires_at must be an ISO timestamp")
    else:
        try:
            ttl = int(payload.get("ttl_seconds", DEFAULT_TTL_SECONDS))
        except (TypeError, ValueError):
            raise ValueError("ttl_seconds must be an integer")
        if ttl <= 0:
            raise ValueError("ttl_seconds must be positive")
        expires_at = now + timedelta(seconds=ttl)
    if expires_at <= now:
        raise ValueError("expires_at is already in the past")
    cap = now + timedelta(seconds=MAX_TTL_SECONDS)
    if expires_at > cap:
        expires_at = cap

    starts_at = None
    if payload.get("starts_at"):
        try:
            starts_at = datetime.fromisoformat(payload["starts_at"])
        except ValueError:
            raise ValueError("starts_at must be an ISO timestamp")

    overlay_id = payload.get("id") or uuid.uuid4().hex[:12]
    if not str(overlay_id).replace("-", "").replace("_", "").isalnum():
        raise ValueError("id must be alphanumeric (dashes/underscores ok)")
    overlay_id = str(overlay_id)[:40]

    has_image = False
    if image_b64:
        try:
            raw = base64.b64decode(image_b64, validate=True)
        except (binascii.Error, ValueError):
            raise ValueError("image_b64 is not valid base64")
        if len(raw) > MAX_IMAGE_BYTES:
            raise ValueError(f"image too large (max {MAX_IMAGE_BYTES} bytes decoded)")
        # Verify it's actually an image PIL can open.
        import io
        from PIL import Image
        try:
            probe = Image.open(io.BytesIO(raw))
            probe.verify()
        except Exception:
            raise ValueError("image_b64 does not decode to a readable image")
        IMAGE_DIR.mkdir(exist_ok=True)
        with open(_image_path(overlay_id), "wb") as f:
            f.write(raw)
        has_image = True

    overlay = {
        "id": overlay_id,
        "slot": slot,
        "title": title,
        "text": text,
        "has_image": has_image,
        "priority": priority,
        "created_at": now.isoformat(timespec="seconds"),
        "starts_at": starts_at.isoformat(timespec="seconds") if starts_at else None,
        "expires_at": expires_at.isoformat(timespec="seconds"),
    }

    with _lock:
        overlays, _ = _prune(_load())
        # Same id replaces the old overlay (idempotent updates).
        overlays = [o for o in overlays if o.get("id") != overlay_id]
        overlays.append(overlay)
        _save(overlays)
    return overlay


def list_all():
    """All unexpired overlays (may include not-yet-started ones)."""
    with _lock:
        overlays, changed = _prune(_load())
        if changed:
            _save(overlays)
    return overlays


def active(slot=None):
    """Overlays that should render right now, highest priority first.

    Ties broken by most recently created.
    """
    now = _now()
    overlays = [o for o in list_all() if _is_started(o, now)]
    if slot is not None:
        overlays = [o for o in overlays if o.get("slot") == slot]
    overlays.sort(key=lambda o: o.get("created_at", ""), reverse=True)
    overlays.sort(key=lambda o: o.get("priority", 0), reverse=True)
    return overlays


def get_image(overlay_id):
    """Path to the overlay's stored image, or None."""
    p = _image_path(overlay_id)
    return p if p.exists() else None


def remove(overlay_id):
    """Delete one overlay. Returns True if it existed."""
    with _lock:
        overlays = _load()
        kept = [o for o in overlays if o.get("id") != overlay_id]
        found = len(kept) != len(overlays)
        if found:
            _delete_image(overlay_id)
        kept, _ = _prune(kept)
        _save(kept)
    return found


def clear():
    """Delete all overlays. Returns how many were removed."""
    with _lock:
        overlays = _load()
        for o in overlays:
            _delete_image(o.get("id", ""))
        _save([])
    return len(overlays)
