"""Proof-preserving illustration treatment; no network or live state."""
import unittest
from PIL import Image
import art_catalog


class IllustrationTreatmentTests(unittest.TestCase):
    def test_dither_matches_selected_resize_then_conversion(self):
        entry = next(e for e in art_catalog.catalog() if e['weekday'] == 5)
        self.assertEqual(entry['method'], 'dither')
        for width, height in ((369, 338), (354, 140), (354, 198)):
            with self.subTest(width=width, height=height):
                with Image.open(art_catalog.ART_DIR / entry['file']) as original:
                    expected = original.convert('L')
                expected.thumbnail((width, height), Image.Resampling.LANCZOS)
                expected = expected.convert('1')
                actual = art_catalog.image_for(entry, width, height)
                self.assertEqual((actual.size, actual.mode), (expected.size, '1'))
                self.assertEqual(actual.tobytes(), expected.tobytes())
                actual.paste(0, (0, 0, actual.width, actual.height))
                self.assertEqual(art_catalog.image_for(entry, width, height).tobytes(), expected.tobytes())

    def test_approved_landmark_art_is_distinct_and_bundled(self):
        entries = art_catalog.catalog()[4:]
        self.assertEqual(len({entry['object_id'] for entry in entries}), 3)
        self.assertTrue(all(entry['selection_status'].startswith('user-approved') for entry in entries))
        for entry in entries:
            self.assertEqual(art_catalog.image_for(entry, 354, 140).mode, '1')


if __name__ == '__main__':
    unittest.main()
