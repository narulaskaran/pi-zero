"""Offline weekday artwork, using New York's calendar day (Monday=0)."""
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json

from PIL import Image

ROOT = Path(__file__).resolve().parent
ART_DIR = ROOT / 'art' / 'weekdays'
TIMEZONE = ZoneInfo('America/New_York')


@lru_cache(maxsize=1)
def catalog():
    data = json.loads((ART_DIR / 'catalog.json').read_text())
    entries = data['artworks']
    if len(entries) != 7 or sorted(e['weekday'] for e in entries) != list(range(7)):
        raise ValueError('Artwork catalog must contain each weekday exactly once')
    for entry in entries:
        name = entry['file']
        if Path(name).name != name or not entry.get('is_public_domain'):
            raise ValueError('Invalid bundled artwork entry')
        if hashlib.sha256((ART_DIR / name).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Artwork asset checksum mismatch')
    return tuple(sorted(entries, key=lambda e: e['weekday']))


def local_day(now=None):
    now = now or datetime.now(TIMEZONE)
    # Existing injection callers use naive local datetimes; interpret as New York.
    if isinstance(now, datetime) and now.tzinfo is not None:
        now = now.astimezone(TIMEZONE)
    return now


def artwork_for(now=None):
    return dict(catalog()[local_day(now).weekday()])


@lru_cache(maxsize=64)
def _image(filename, width, height, method, threshold):
    with Image.open(ART_DIR / filename) as source:
        image = source.convert('L')
    image.thumbnail((max(1, width), max(1, height)), Image.Resampling.LANCZOS)
    if method == 'threshold':
        image = image.point(lambda v: 255 if v > threshold else 0, '1')
    elif method == 'dither':
        # Match approved grayscale illustration proofs after fitting to the slot.
        image = image.convert('1')
    elif method == 'ordered':
        matrix = ((0, 2), (3, 1))
        pixels = image.load()
        for y in range(image.height):
            for x in range(image.width):
                pixels[x, y] = 255 if pixels[x, y] > (matrix[y % 2][x % 2] + .5) * 64 else 0
        image = image.convert('1')
    else:
        raise ValueError('Unknown artwork treatment')
    return image


def image_for(entry, width, height):
    # Return a copy so callers cannot mutate the shared cached artwork.
    return _image(entry['file'], int(width), int(height), entry['method'], entry.get('threshold', 151)).copy()


def status(now=None):
    entry = artwork_for(now)
    return {'day': entry['day'], 'object_id': entry['object_id'],
            'artist': entry['artist'], 'title': entry['title'],
            'timezone': str(TIMEZONE),
            'catalog_sha256': hashlib.sha256((ART_DIR / 'catalog.json').read_bytes()).hexdigest()}
