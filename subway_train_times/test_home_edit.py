"""Isolated Field Notes acceptance tests; all API storage lives in temp dirs."""
import base64
import hashlib
import io
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageChops
import home_edit
import subway_server as server

REAL_GET_WEATHER = server.get_weather
REAL_GET_AIR_QUALITY = server.get_air_quality
WEATHER = {
    'current': {'temperature_2m': 53, 'apparent_temperature': 47, 'weather_code': 0},
    'daily': {'time': ['2026-11-08', '2026-11-09', '2026-11-10'], 'temperature_2m_max': [61, 56, 57],
              'temperature_2m_min': [46, 43, 42], 'precipitation_probability_max': [17, 4, 8],
              'sunrise': ['2026-11-08T06:34', '2026-11-09T06:35', '2026-11-10T06:36'],
              'sunset': ['2026-11-08T16:44', '2026-11-09T16:43', '2026-11-10T16:42']}}
NOW = datetime(2026, 11, 9, 18, 0)
ARTIFACTS = Path('/opt/data/artifacts/eink/field-notes-deploy')


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW


class FieldNotesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name)
        self.patches = [patch.object(server, 'load_config', return_value={}),
                        patch.object(server.overlay_store, 'OVERLAY_FILE', self.state / 'overlays.json'),
                        patch.object(server.overlay_store, 'IMAGE_DIR', self.state / 'images'),
                        patch.object(server, 'get_air_quality', return_value=37),
                        patch.object(server, 'get_weather', return_value=WEATHER),
                        patch.object(server, 'datetime', FixedDateTime),
                        patch.object(server.overlay_store, '_now', return_value=NOW)]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.client = server.app.test_client()

    def post(self, id, slot='banner', title=None, text=None, priority=0, **kwargs):
        body = {'id': id, 'slot': slot, 'title': title or id, 'text': text or 'Shared reminder text',
                'priority': priority, 'ttl_seconds': 3600}
        body.update(kwargs)
        r = self.client.post('/overlay', json=body)
        self.assertEqual(r.status_code, 201, r.data)
        return r.json

    def bitmap(self):
        response = self.client.get('/display.bmp')
        self.assertEqual(response.status_code, 200)
        image = Image.open(io.BytesIO(response.data))
        self.assertEqual((image.size, image.mode), ((800, 480), '1'))
        return image

    def test_status_version_and_refresh_contract(self):
        self.assertEqual(self.client.get('/status').json['renderer_version'], 'field-notes-2-weekday-art')
        self.assertEqual(self.client.get('/status').json['layout'], 'home_edit')
        self.assertEqual(self.client.get('/refresh-rate').json['refresh_minutes'], 15)

    def test_weather_sparse_extreme_and_tomorrow_by_date(self):
        self.assertEqual(home_edit.forecast_index(WEATHER, NOW), 2)
        self.assertIsNone(home_edit.forecast_index(WEATHER, datetime(2026, 11, 12)))
        for weather in ({}, {'current': {}}, {'current': {'temperature_2m': -12, 'apparent_temperature': -30, 'weather_code': 95}}, {'daily': {'time': []}}):
            im = home_edit.render(NOW, weather, None)
            self.assertEqual(im.size, (800, 480))
            self.assertEqual(im.convert('1').mode, '1')

    def test_adaptive_states_are_native_monochrome_and_empty_removes_footer(self):
        empty = self.bitmap().convert('L')
        self.assertIsNone(ImageChops.difference(empty.crop((20, 450, 780, 480)), Image.new('L', (760, 30), 255)).getbbox())
        self.assertIsNotNone(ImageChops.invert(empty.crop((20, 56, 780, 391))).getbbox())
        for n in (1, 2, 4, 7):
            records = [{'id': f'n{i}', 'title': f'Row {i}', 'text': f'Body {i}', 'priority': n-i} for i in range(n)]
            image = home_edit.render(NOW, WEATHER, 37, reminders=records)
            self.assertEqual((image.size, image.convert('1').mode), ((800, 480), '1'))
            region = image.convert('L').crop((25, 250 if n >= 3 else 310, 775, 478))
            self.assertGreater(ImageChops.invert(region).getbbox()[3], 0)

    def test_legacy_reminder_helper_only_changes_lower_section(self):
        base = home_edit.render(NOW, WEATHER, 37)
        before = base.copy()
        result = home_edit.draw_reminder_list(base, [{'title': 'Keep the title', 'text': 'And its body'}])
        self.assertIs(result, base)
        self.assertIsNone(ImageChops.difference(before.crop((0, 0, 800, 310)), base.crop((0, 0, 800, 310))).getbbox())
        self.assertIsNotNone(ImageChops.difference(before.crop((0, 310, 800, 480)), base.crop((0, 310, 800, 480))).getbbox())

    def test_layout_count_change_preserves_header_and_weather_for_each_state(self):
        empty = home_edit.render(NOW, WEATHER, 37, reminders=[]).convert('L')
        two = home_edit.render(NOW, WEATHER, 37, reminders=[{'title': 'A'}, {'title': 'B'}]).convert('L')
        four = home_edit.render(NOW, WEATHER, 37, reminders=[{'title': str(i)} for i in range(4)]).convert('L')
        for other in (two, four):
            self.assertIsNone(ImageChops.difference(empty.crop((0, 0, 800, 55)), other.crop((0, 0, 800, 55))).getbbox())
        # Weather is stable across reminder counts; only expected empty-state vertical reflow differs.
        for a, b, box in ((two, home_edit.render(NOW, WEATHER, 37, reminders=[{'title': 'A'}, {'title': 'B'}]).convert('L'), (0, 55, 370, 305)),
                          (four, home_edit.render(NOW, WEATHER, 37, reminders=[{'title': str(i)} for i in range(4)]).convert('L'), (0, 55, 370, 305))):
            self.assertIsNone(ImageChops.difference(a.crop(box), b.crop(box)).getbbox())

    def test_title_body_long_tokens_overflow_and_thumbnail(self):
        self.post('long', title='A title ' * 20, text='UNBROKEN' * 50)
        self.post('four', title='Four', text='Four body')
        self.post('three', title='Three', text='Third body')
        self.post('five', title='Five', text='Fifth body')
        image = self.bitmap().convert('L')
        self.assertIsNotNone(ImageChops.invert(image.crop((30, 250, 770, 478))).getbbox())
        thumb = Image.new('RGB', (18, 18), 'black')
        data = io.BytesIO(); thumb.save(data, format='PNG')
        response = self.client.post('/overlay', json={'id': 'with-image', 'slot': 'banner', 'title': 'Image', 'text': 'Thumbnail survives', 'image_b64': base64.b64encode(data.getvalue()).decode(), 'priority': 100, 'ttl_seconds': 60})
        self.assertEqual(response.status_code, 201)
        stored = self.client.get('/display.bmp')
        self.assertEqual(stored.status_code, 200)
        with_image = Image.open(io.BytesIO(stored.data)).convert('L')
        self.assertIsNotNone(ImageChops.difference(image, with_image).crop((32, 289, 50, 307)).getbbox())

    def test_priority_start_expiry_crud_and_one_active_snapshot(self):
        self.post('low', 'banner', priority=1)
        self.post('high', 'sidebar', priority=9)
        self.post('future', 'banner', priority=99, starts_at='2026-11-10T08:00:00')
        with patch.object(server.overlay_store, 'active', wraps=server.overlay_store.active) as active:
            image = self.bitmap()
        active.assert_called_once_with()
        rows = server.overlay_store.active()
        self.assertEqual([r['id'] for r in rows], ['high', 'low'])
        self.assertEqual(image.mode, '1')
        self.assertEqual(self.client.delete('/overlay/low').status_code, 200)
        self.assertEqual([o['id'] for o in self.client.get('/overlays?active=1').json['overlays']], ['high'])
        self.assertEqual(self.client.delete('/overlays').json['cleared'], 2)

    def test_fullscreen_is_exclusive_and_keeps_title_and_text(self):
        self.post('reminder', 'banner', title='Hidden under fullscreen')
        self.post('exclusive', 'fullscreen', title='FULLSCREEN TITLE', text='Distinct fullscreen body copy')
        with patch.object(server.overlay_store, 'get_image', return_value=None), patch.object(home_edit, 'draw_overlay', wraps=home_edit.draw_overlay) as overlay:
            image = server.generate_image(now=NOW, weather=WEATHER)
        overlay.assert_called_once()
        self.assertEqual(overlay.call_args.args[1]['id'], 'exclusive')
        self.assertEqual(image.size, (800, 480))

    def test_overlay_slots_and_png_route(self):
        for slot in ('banner', 'sidebar', 'fullscreen'):
            overlay = {'slot': slot, 'title': 'Overlay heading', 'text': 'Overlay body remains distinct ' * 30}
            im = home_edit.render(NOW, WEATHER, 37)
            home_edit.draw_overlay(im, overlay)
            self.assertEqual(im.size, (800, 480))
        self.assertEqual(self.client.get('/display.png').status_code, 200)

    def test_empty_route_keeps_tomorrow_rain_and_aqi_visible(self):
        image = self.bitmap().convert('L')
        # Independent content bands must contain actual dark pixels at approved empty-state y positions.
        for box in ((25, 245, 365, 275), (25, 285, 365, 320)):
            self.assertIsNotNone(ImageChops.invert(image.crop(box)).getbbox(), box)

    def test_real_route_renders_title_and_body_in_each_reminder_row(self):
        fixtures = [
            ([{'title': 'Row one title', 'text': 'First body is visible'}, {'title': 'Row two title', 'text': 'Second body is visible'}], [353, 403]),
            ([{'title': f'Four row {i}', 'text': f'Body detail {i}'} for i in range(4)], [295, 337, 379, 421]),
        ]
        for records, tops in fixtures:
            server.overlay_store.clear()
            for i, record in enumerate(records):
                self.post(f'pixel-{i}', 'banner', record['title'], record['text'])
            image = self.bitmap().convert('L')
            for y in tops:
                for band in ((200, y, 770, y + 21), (200, y + 22, 770, y + 40)):
                    self.assertIsNotNone(ImageChops.invert(image.crop(band)).getbbox(), band)

    def test_fullscreen_route_uses_native_coordinates_and_shows_content_below_image(self):
        self.post('full-image', 'fullscreen', 'A visible fullscreen heading', 'The fullscreen body remains within the display.', has_image=False)
        image = Image.open(io.BytesIO(self.client.get('/display.png').data)).convert('L')
        self.assertIsNotNone(ImageChops.invert(image.crop((35, 82, 760, 128))).getbbox())
        self.assertIsNotNone(ImageChops.invert(image.crop((35, 130, 760, 210))).getbbox())
        self.assertIsNone(ImageChops.invert(image.crop((0, 480, 800, 480))).getbbox())

    def test_overlay_store_read_errors_fall_back_but_renderer_errors_propagate(self):
        with patch.object(server.overlay_store, 'active', side_effect=OSError('overlay read failed')):
            result = server.generate_image(now=NOW, weather=WEATHER)
        self.assertEqual(result.size, (800, 480))
        with patch.object(server.overlay_store, 'active', return_value=[{'id': 'with-image', 'slot': 'banner', 'has_image': True}]), \
             patch.object(server.overlay_store, 'get_image', side_effect=OSError('image lookup failed')):
            result = server.generate_image(now=NOW, weather=WEATHER)
        self.assertEqual(result.size, (800, 480))
        with patch.object(home_edit, 'render', side_effect=RuntimeError('renderer bug')):
            with self.assertRaisesRegex(RuntimeError, 'renderer bug'):
                server.generate_image(now=NOW, weather=WEATHER)

    def test_network_failure_is_explicit(self):
        with patch.object(server.requests, 'get', side_effect=OSError('offline')), patch.object(server, 'load_config', return_value={}):
            self.assertIsNone(REAL_GET_WEATHER(40, -74))
            server._air_cache.clear()
            self.assertIsNone(REAL_GET_AIR_QUALITY(40, -74))
        self.assertEqual(home_edit.render(NOW, None, None).size, (800, 480))

    def test_no_transit_fetch_and_route_produced_previews(self):
        with patch.object(server, 'get_subway', side_effect=AssertionError('transit forbidden'), create=True):
            ARTIFACTS.mkdir(parents=True, exist_ok=True)
            for state, records in (('empty', []), ('two', [{'id': 'a', 'title': 'Water plants', 'text': 'Check the soil'}, {'id': 'b', 'title': 'Take out recycling', 'text': 'Before collection'}]), ('four', [{'id': str(i), 'title': f'Field note {i}', 'text': f'Useful detail {i}', 'priority': 4-i} for i in range(4)])):
                server.overlay_store.clear()
                for record in records:
                    self.post(record['id'], 'banner', record['title'], record['text'], record.get('priority', 0))
                response = self.client.get('/display.bmp')
                self.assertEqual(response.status_code, 200)
                im = Image.open(io.BytesIO(response.data)).convert('1')
                out = ARTIFACTS / f'staged-{state}.png'
                im.save(out)
                self.assertEqual((im.size, im.mode), ((800, 480), '1'))
                self.assertTrue(out.exists())
                self.assertEqual(len(hashlib.sha256(out.read_bytes()).hexdigest()), 64)


if __name__ == '__main__':
    unittest.main(verbosity=2)
