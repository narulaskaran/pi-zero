"""Last-rendered timestamp regression checks through the real BMP compositor."""
import importlib.util
import io
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageChops
import home_edit
import subway_server as server
import test_home_edit as fixtures

class UpdatedTimeTests(fixtures.FieldNotesTests):
    def test_updated_all_states_preserves_every_other_pixel(self):
        import subprocess
        import types
        baseline = types.ModuleType('baseline')
        baseline.__file__ = home_edit.__file__
        source = subprocess.check_output(['git', 'show', 'ece4c7a:subway_train_times/home_edit.py'], cwd=home_edit.ROOT)
        exec(compile(source, baseline.__file__, 'exec'), baseline.__dict__)
        out = Path('/opt/data/artifacts/eink/last-updated')
        out.mkdir(parents=True, exist_ok=True)
        for count in (0, 1, 2, 3, 4, 7):
            server.overlay_store.clear()
            for i in range(count):
                self.post(f'item{i}', title=f'Reminder {i}', text=f'Useful detail {i}')
            for battery in ('', '?battery=73'):
                with patch.object(server, 'home_edit', baseline):
                    before = Image.open(io.BytesIO(self.client.get('/display.bmp' + battery).data)).convert('L')
                response = self.client.get('/display.bmp' + battery)
                raw = Image.open(io.BytesIO(response.data))
                self.assertEqual((raw.size, raw.mode), ((800, 480), '1'))
                delta = ImageChops.difference(before, raw.convert('L'))
                bounds = delta.getbbox()
                self.assertIsNotNone(bounds)
                assert bounds is not None
                self.assertTrue(280 <= bounds[0] < bounds[2] <= 520, bounds)
                self.assertTrue(36 <= bounds[1] < bounds[3] < 54, bounds)
                raw.save(out / f'state-{count}{"-battery" if battery else ""}.png')
        self.post('full', slot='fullscreen', title='Special occasion', text='A fullscreen message')
        with patch.object(home_edit, '_text', wraps=home_edit._text) as text:
            self.bitmap()
        self.assertIn('UPDATED 6:00 PM ET', [c.args[3] for c in text.call_args_list])

    def test_updated_timezone_and_minutes(self):
        for moment, expected in ((datetime(2026, 11, 10, 0, 4, tzinfo=timezone.utc), 'UPDATED 7:04 PM ET'),
                                 (datetime(2026, 7, 10, 0, 4, tzinfo=timezone.utc), 'UPDATED 8:04 PM ET')):
            with patch.object(home_edit, '_text', wraps=home_edit._text) as text:
                home_edit.render(moment, fixtures.WEATHER)
            self.assertIn(expected, [c.args[3] for c in text.call_args_list])
