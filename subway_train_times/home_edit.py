"""Field Notes: deterministic 800x480 adaptive 1-bit weather/reminder board."""
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
import math
import logging
import art_catalog

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance

ROOT = Path(__file__).resolve().parent
SCALE = 1
REGIONS = {'sidebar': (415, 78, 774, 343), 'banner': (26, 365, 774, 472),
           'fullscreen': (26, 78, 774, 472)}


@lru_cache(maxsize=64)
def font(size, face='sans', scale=SCALE, weight=400):
    name = 'IBMPlexMono.ttf' if face == 'mono' else 'IBMPlexSans.ttf'
    f = ImageFont.truetype(str(ROOT / 'fonts' / name), int(size * scale))
    if face == 'sans':
        try:
            f.set_variation_by_axes([weight, 100])
        except (AttributeError, OSError, ValueError):
            pass
    return f


def _fit_text(draw, value, f, max_width, marker='...'):
    value = ' '.join(str(value).split())
    if draw.textbbox((0, 0), value, font=f)[2] <= max_width:
        return value
    while value and draw.textbbox((0, 0), value + marker, font=f)[2] > max_width:
        value = value[:-1]
    return value.rstrip() + marker


def _text(d, x, y, value, size=20, face='sans', anchor=None, max_width=None, weight=400):
    f = font(size, face, weight=weight)
    value = str(value)
    if max_width is not None:
        value = _fit_text(d, value, f, max_width)
    d.text((int(x), int(y)), value, font=f, fill=0, anchor=anchor)


def _line(d, points, width=1):
    d.line([(int(x), int(y)) for x, y in points], fill=0, width=max(1, int(width)))


def _number(value):
    try:
        n = float(value)
        return round(n) if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def _degree(value):
    n = _number(value)
    return '--' if n is None else str(n) + '°'


def forecast_index(weather, now):
    dates = (weather or {}).get('daily', {}).get('time', [])
    tomorrow = (now.date() + timedelta(days=1)).isoformat()
    return dates.index(tomorrow) if tomorrow in dates else None


def _daily(weather, key, index):
    if index is None:
        return None
    values = (weather or {}).get('daily', {}).get(key, [])
    return values[index] if index < len(values) else None


def weather_copy(current):
    code = current.get('weather_code')
    feels = _number(current.get('apparent_temperature'))
    if feels is None:
        feels = _number(current.get('temperature_2m'))
    if code is None:
        return 'WEATHER ON PAUSE', 'Still a good day.', 'Live conditions unavailable.'
    if code >= 95:
        return 'STORMY SKIES', 'Take care outside.', 'Check local alerts before heading out.'
    if code >= 71 and code <= 86 and code not in (80, 81, 82):
        return 'SNOW OUTSIDE', 'Bundle up.', 'A warm layer and sensible shoes.'
    if code >= 51:
        return 'RAIN OUTSIDE', 'Bring an umbrella.', 'A raincoat if you’re heading out.'
    if code in (45, 48):
        first = 'A LITTLE FOG'
    elif code == 3:
        first = 'CLOUDY SKIES'
    elif code in (1, 2):
        first = 'A LITTLE SUN'
    else:
        first = 'CLEAR SKIES'
    if feels is None:
        return first, 'Take it easy.', 'Check the forecast before heading out.'
    if feels < 35:
        return first, 'Cold air.', 'Bundle up if you’re heading out.'
    if feels < 55:
        return first, 'Cool air.', 'A jacket if you’re heading out.'
    if feels >= 85:
        return first, 'Warm air.', 'Water and shade if you’re heading out.'
    return first, 'Gentle air.', 'A little time outside might be nice.'


def air_copy(aqi):
    n = _number(aqi)
    if n is None:
        return 'AIR UNAVAILABLE', 'No current air-quality reading'
    if n <= 50:
        return 'GOOD AIR', f'AQI {n} · A little breathing room'
    if n <= 100:
        return 'MODERATE AIR', f'AQI {n} · Sensitive? Take it easy'
    if n <= 150:
        return 'MIND THE AIR', f'AQI {n} · Limit sensitive exposure'
    if n <= 200:
        return 'UNHEALTHY AIR', f'AQI {n} · Reduce outdoor exertion'
    return 'STAY AIR-AWARE', f'AQI {n} · Avoid outdoor exertion'


def _art_image(width, height):
    path = ROOT / 'art' / 'durer-rhinoceros.jpg'
    with Image.open(path) as src:
        art = src.convert('L')
    art = art.crop((0, int(art.height * .15), art.width, int(art.height * .95)))
    art = ImageOps.autocontrast(art, cutoff=1)
    art = ImageEnhance.Brightness(art).enhance(1.08)
    art.thumbnail((int(width), int(height)), Image.Resampling.LANCZOS)
    art = art.point(lambda v: 255 if v > 151 else 0).convert('1').convert('L')
    return art


def _place_art(im, box, now=None):
    x, y, w, h = box
    if w <= 0 or h <= 0:
        return ''
    try:
        entry = art_catalog.artwork_for(now)
        art = art_catalog.image_for(entry, w, h)
        caption = entry['caption']
    except (OSError, ValueError, KeyError) as exc:
        logging.getLogger(__name__).warning('Weekday art unavailable; using bundled rhino: %s', exc)
        art = _art_image(w, h)
        caption = 'Dürer · The Rhinoceros, 1515'
    px = int(x + (w - art.width) / 2)
    py = int(y + (h - art.height) / 2)
    im.paste(art, (px, py))
    return caption


def _reminder_line(d, im, reminder, y, width, title_size=20, body_size=15):
    x = 200
    thumb = reminder.get('_image_path')
    if thumb:
        try:
            with Image.open(thumb) as src:
                image = src.convert('L')
            image.thumbnail((32, 32), Image.Resampling.LANCZOS)
            im.paste(image, (32, y + 1))
        except (OSError, ValueError):
            pass
    d.text((182, y + 7), '—', font=font(15, 'mono'), fill=0)
    available = width - x - 20
    has_title = bool(reminder.get('title'))
    title = reminder.get('title') or reminder.get('text') or ''
    text = reminder.get('text') or '' if has_title else ''
    for offset, value, size, weight in ((0, title, title_size, 560), (22, text, body_size, 400)):
        if not value:
            continue
        f = font(size, 'mono' if offset == 0 else 'sans', weight=weight)
        fitted = _fit_text(d, value, f, available)
        d.text((x, y + offset), fitted, font=f, fill=0)


def draw_reminder_list(im, reminders):
    """Compatibility helper: replace only the adaptive reminder section."""
    reminders = list(reminders or [])
    if not reminders:
        return im
    split = 252 if len(reminders) >= 3 else 310
    result = render(datetime.now(), None, reminders=reminders)
    im.paste(result.crop((0, split, 800, 480)), (0, split))
    return im


def render(now, weather, aqi=None, battery_percent=None, has_sidebar=False, reminders=None):
    now = art_catalog.local_day(now)
    reminders = list(reminders or [])
    populated = bool(reminders)
    count = len(reminders)
    split = (252 if count >= 3 else 310) if populated else 468
    im = Image.new('L', (800, 480), 255)
    d = ImageDraw.Draw(im)
    dy = 0 if populated else 65
    current = (weather or {}).get('current', {})
    temp = _degree(current.get('temperature_2m'))
    code = current.get('weather_code')
    condition = {0: 'Clear', 1: 'Mostly clear', 2: 'Partly cloudy', 3: 'Cloudy', 45: 'Foggy', 48: 'Foggy'}.get(code)
    if condition is None:
        condition = ('Storms' if code in (95, 96, 99) else
                     'Snow' if code in (71, 73, 75, 77, 85, 86) else
                     'Rain' if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82) else
                     'Unavailable')
    feels = _degree(current.get('apparent_temperature'))
    forecast_day = forecast_index(weather, now)
    hi = _degree(_daily(weather, 'temperature_2m_max', forecast_day))
    lo = _degree(_daily(weather, 'temperature_2m_min', forecast_day))
    rain = _number(_daily(weather, 'precipitation_probability_max', forecast_day))
    tomorrow_rain = f'{rain}%' if rain is not None else '--'
    air_value = _number(aqi)
    air_label = str(air_value) if air_value is not None else '--'
    _text(d, 28, 18, now.strftime('%a %d %b').upper(), 17, 'mono')
    _text(d, 772, 18, 'NEW YORK', 16, 'mono', anchor='ra')
    _line(d, [(28, 54), (772, 54)])
    temp_size = 78
    while temp_size > 40 and d.textlength(temp, font=font(temp_size, 'sans', weight=560)) > 155:
        temp_size -= 1
    _text(d, 27, 64 + dy, temp, temp_size, 'sans', weight=560)
    condition_size = 29
    while condition_size > 17 and d.textlength(condition, font=font(condition_size, 'mono')) > 190:
        condition_size -= 1
    _text(d, 186, 87 + dy, condition, condition_size, 'mono', max_width=190)
    _text(d, 187, 132 + dy, f'Feels like {feels}', 17, 'sans', max_width=188)
    _text(d, 29, 184 + dy, 'Tomorrow', 16, 'mono')
    _text(d, 159, 180 + dy, f'{hi} / {lo}', 24, 'sans', max_width=210, weight=560)
    _text(d, 29, (216 if count >= 3 else 224) + dy, f'Rain {tomorrow_rain}   ·   AQI {air_label}', 17, 'mono', max_width=335)
    art_box = (386, 87, 369, 338) if not populated else (418, 69, 354, split - 112)
    caption = _place_art(im, art_box, now)
    if art_box[3] > 0:
        _text(d, art_box[0] + 3, 434 if not populated else split - 34, caption, 12, 'mono', max_width=art_box[2] - 6)

    if populated:
        _line(d, [(28, split), (772, split)])
        _text(d, 28, split + 18, 'HOME', 16, 'mono')
        shown = min(4, count)
        row_ys = ([split + 43, split + 93] if count <= 2 else [284, 326, 368, 410])
        for i, reminder in enumerate(reminders[:shown]):
            y = row_ys[i]
            if i:
                _line(d, [(30, y - 5), (770, y - 5)], .7)
            _reminder_line(d, im, reminder, y, 772, 22 if count <= 2 else 20, 15 if count <= 2 else 14)
        if count > shown:
            _text(d, 690, 461, f'+{count - shown} MORE', 12, 'mono', anchor='ra')

    if battery_percent is not None:
        _text(d, 772, 468, f'BATTERY {battery_percent}%', 9, 'mono', anchor='ra')
    return im


def _wrapped(d, text, f, width):
    words = str(text).split()
    lines, line = [], ''
    for word in words:
        candidate = (line + ' ' + word).strip()
        if d.textbbox((0, 0), candidate, font=f)[2] <= width:
            line = candidate
            continue
        if line:
            lines.append(line)
            line = ''
        for ch in word:
            if line and d.textbbox((0, 0), line + ch, font=f)[2] > width:
                lines.append(line)
                line = ''
            line += ch
    if line:
        lines.append(line)
    return lines


def _fit_lines(d, text, size, face, width, max_lines, weight=400):
    f = font(size, face, scale=1, weight=weight)
    lines = _wrapped(d, text, f, width)
    omitted = len(lines) > max_lines
    if omitted:
        lines = lines[:max_lines]
        lines[-1] = _fit_text(d, lines[-1] + '...', f, width)
    return f, lines


def draw_overlay(im, overlay, image_path=None):
    """Draw a title and body (and optional image) in the requested overlay slot."""
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = REGIONS[overlay['slot']]
    d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=255)
    x, y, width = x0 + 8, y0 + 8, x1 - x0 - 16
    if image_path:
        with Image.open(image_path) as source:
            art = source.convert('L')
        art.thumbnail((width, (y1 - y0) // 3), Image.Resampling.LANCZOS)
        im.paste(art, (x, y))
        y += art.height + 6
    title = overlay.get('title') or ''
    body = overlay.get('text') or ''
    size = 25 if overlay['slot'] != 'fullscreen' else 38
    if title:
        f, lines = _fit_lines(d, title, size, 'sans', width, 1, 600)
        for line in lines:
            d.text((x, y), line, font=f, fill=0)
        y += size + 7
    body_size = 18 if overlay['slot'] != 'fullscreen' else 25
    max_lines = max(1, (y1 - 8 - y) // (body_size + 5))
    f, lines = _fit_lines(d, body, body_size, 'sans', width, max_lines)
    for line in lines:
        d.text((x, y), line, font=f, fill=0)
        y += body_size + 5
