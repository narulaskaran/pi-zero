"""Battery readout acceptance through the production BMP route."""
import io
import unittest
from PIL import Image, ImageChops
from test_home_edit import FieldNotesTests


class BatteryHeaderTests(FieldNotesTests):
    def test_battery_header_all_reminder_states(self):
        for count in (0, 1, 2, 3, 4, 7):
            for i in range(count):
                self.post(f'row{i}')
            baseline = self.bitmap().convert('L')
            for percent in (0, 1, 73, 100):
                response = self.client.get(f'/display.bmp?battery={percent}')
                raw = Image.open(io.BytesIO(response.data))
                self.assertEqual((raw.size, raw.mode), ((800, 480), '1'))
                delta = ImageChops.difference(baseline, raw.convert('L'))
                bounds = delta.getbbox()
                self.assertIsNotNone(bounds)
                self.assertTrue(300 <= bounds[0] < bounds[2] <= 500, bounds)
                self.assertTrue(18 <= bounds[1] < bounds[3] < 54, bounds)
            for value in ('-1', '101', 'bad'):
                invalid = Image.open(io.BytesIO(self.client.get(f'/display.bmp?battery={value}').data)).convert('L')
                self.assertIsNone(ImageChops.difference(baseline, invalid).getbbox())
            baseline.save(f'/opt/data/artifacts/eink/battery-header/state-{count}-no-reading.png')
        Image.open(io.BytesIO(self.client.get('/display.bmp?battery=73').data)).save('/opt/data/artifacts/eink/battery-header/crowded.png')
        self.client.delete('/overlay')


if __name__ == '__main__':
    unittest.main()
