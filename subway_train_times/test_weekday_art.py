"""Offline weekday artwork tests and real Flask-route proof matrix."""
import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageChops, ImageDraw, ImageFont
import art_catalog
import home_edit
import subway_server as server
from test_home_edit import WEATHER

OUT = Path('/opt/data/artifacts/eink/crowded-layout-refinement')


class WeekdayArtTests(unittest.TestCase):
    def test_seven_verified_assets_and_small_large_sizes(self):
        entries = art_catalog.catalog()
        self.assertEqual(len(entries), 7)
        self.assertEqual(len({e['object_id'] for e in entries}), 7)
        for n, entry in enumerate(entries):
            self.assertEqual(entry['weekday'], n)
            self.assertTrue(entry['is_public_domain'])
            for w, h in [(354, 140), (354, 198), (369, 338)]:
                image = art_catalog.image_for(entry, w, h)
                self.assertEqual(image.mode, '1')
                self.assertLessEqual(image.width, w)
                self.assertLessEqual(image.height, h)

    def test_new_york_midnight_and_repeated_week(self):
        self.assertEqual(art_catalog.artwork_for(datetime(2026, 11, 10, 4, 59, tzinfo=timezone.utc))['weekday'], 0)
        self.assertEqual(art_catalog.artwork_for(datetime(2026, 11, 10, 5, 0, tzinfo=timezone.utc))['weekday'], 1)
        for n in range(7):
            day = datetime(2026, 11, 9) + timedelta(days=n)
            self.assertEqual(art_catalog.artwork_for(day)['weekday'], n)
            self.assertEqual(art_catalog.artwork_for(day), art_catalog.artwork_for(day.replace(hour=23, minute=59)))
            self.assertEqual(art_catalog.artwork_for(day), art_catalog.artwork_for(day + timedelta(days=7)))
        # Summer midnight is 04:00 UTC, not 05:00.
        self.assertEqual(art_catalog.local_day(datetime(2026, 7, 7, 3, 59, tzinfo=timezone.utc)).weekday(), 0)
        self.assertEqual(art_catalog.local_day(datetime(2026, 7, 7, 4, 0, tzinfo=timezone.utc)).weekday(), 1)

    def test_cached_images_are_not_mutable_shared_state(self):
        entry = art_catalog.artwork_for(datetime(2026, 11, 9))
        image = art_catalog.image_for(entry, 350, 210)
        before = image.tobytes()
        image.paste(0, (0, 0, image.width, image.height))
        self.assertEqual(art_catalog.image_for(entry, 350, 210).tobytes(), before)

    def test_art_failure_preserves_weather_and_empty_behavior(self):
        with patch.object(art_catalog, 'image_for', side_effect=OSError('unreadable image')):
            image = home_edit.render(datetime(2026, 11, 9), WEATHER, 37)
        self.assertEqual(image.size, (800, 480))
        self.assertIsNotNone(ImageChops.invert(image.crop((28, 120, 375, 330))).getbbox())
        self.assertIsNone(ImageChops.invert(image.crop((20, 450, 780, 480))).getbbox())

    def test_catalog_rejects_duplicate_weekday_and_hash_drift(self):
        original = art_catalog.ART_DIR
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Fail before image access when weekday assignment is malformed.
            (root / 'catalog.json').write_text(json.dumps({'artworks':[{'weekday':0}]*7}))
            art_catalog.catalog.cache_clear()
            with patch.object(art_catalog, 'ART_DIR', root), self.assertRaises(ValueError):
                art_catalog.catalog()
            # A valid weekday shape still fails on checksum mismatch.
            entries = [dict(e) for e in json.loads((original/'catalog.json').read_text())['artworks']]
            for entry in entries:
                (root / entry['file']).write_bytes(b'not the approved image')
            (root / 'catalog.json').write_text(json.dumps({'artworks':entries}))
            art_catalog.catalog.cache_clear()
            with patch.object(art_catalog, 'ART_DIR', root), self.assertRaises(ValueError):
                art_catalog.catalog()
        art_catalog.catalog.cache_clear()
        self.assertEqual(len(art_catalog.catalog()), 7)

    def test_all_weekdays_through_real_bmp_route_all_reminder_states(self):
        OUT.mkdir(parents=True, exist_ok=True)
        empty_images = []
        client = server.app.test_client()
        for n in range(7):
            day = datetime(2026, 11, 9, 12) + timedelta(days=n)
            class Clock(datetime):
                @classmethod
                def now(cls, tz=None):
                    return day
            states = {'empty':[], 'single':[{'title':'Water the plants','text':'Check the kitchen pots'}],
                      'two':[{'title':'Water the plants','text':'Check the kitchen pots'}, {'title':'Take out recycling','text':'Paper and glass'}],
                      'three':[{'title':f'Reminder {i+1}','text':f'Shared detail {i+1}'} for i in range(3)],
                      'four':[{'title':f'Reminder {i+1}','text':f'Shared detail {i+1}'} for i in range(4)],
                      'overflow':[{'title':f'Reminder {i+1}','text':f'Shared detail {i+1}'} for i in range(7)],
                      'long':[{'title':'A very long shared household reminder '*6,'text':'unbrokentoken'*40}]}
            for label, items in states.items():
                active = [dict(item, id=f'example-{i}', slot='banner' if i%2 else 'sidebar', priority=10-i, created_at='') for i,item in enumerate(items)]
                with patch.object(server, 'datetime', Clock), patch.object(server, 'load_config', return_value={}), patch.object(server, 'get_weather', return_value=WEATHER), patch.object(server, 'get_air_quality', return_value=37), patch.object(server.overlay_store, 'active', return_value=active):
                    response = client.get('/display.bmp')
                    self.assertEqual(response.status_code, 200)
                    image = Image.open(io.BytesIO(response.data))
                    self.assertEqual((image.size, image.mode), ((800,480),'1'))
                    self.assertLess(len(response.data), 50000)
                    image.save(OUT/f'{n}-{label}.png')
                    if label == 'empty':
                        empty_images.append(image.copy())
                        self.assertIsNone(ImageChops.invert(image.convert('L').crop((20,450,780,480))).getbbox())
                    if label == 'overflow':
                        self.assertIsNotNone(ImageChops.invert(image.convert('L').crop((650,450,780,479))).getbbox())
                    status = client.get('/status').json
                    self.assertEqual(status['artwork']['object_id'], art_catalog.catalog()[n]['object_id'])
                    self.assertEqual(status['renderer_version'], 'field-notes-2-weekday-art')
                    self.assertEqual(client.get('/refresh-rate').json['refresh_minutes'], 15)
        # Weekday change must actually alter the art pixels, not just metadata.
        for a,b in zip(empty_images,empty_images[1:]):
            self.assertIsNotNone(ImageChops.difference(a.convert('L'),b.convert('L')).crop((386,87,755,425)).getbbox())
        sheet = Image.new('RGB',(1600,2000),'white')
        draw = ImageDraw.Draw(sheet)
        f = ImageFont.truetype(str(home_edit.ROOT/'fonts/IBMPlexMono.ttf'),14)
        for n,image in enumerate(empty_images):
            x=(n%2)*800;y=(n//2)*500
            draw.text((x+20,y+3),art_catalog.catalog()[n]['day'],font=f,fill=0)
            sheet.paste(image.convert('RGB'),(x,y+20))
        sheet.save(OUT/'all-weekdays.png')


if __name__ == '__main__':
    unittest.main()
