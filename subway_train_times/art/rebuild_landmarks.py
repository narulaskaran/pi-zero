"""Offline reproduction of the three approved landmark PNGs.

Requires Pillow and CairoSVG. The NPS original is supplied locally, never fetched
by this script or the display service. See weekdays/LANDMARK-STUDIES.md.
"""
import argparse
import hashlib
import io
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFilter, ImageOps


SOURCE_SHA256 = 'ea1395f127eb6bf51662b9101c3d52cb941c4f1d25e12024112677b6244c09e2'
ART = Path(__file__).resolve().parent / 'weekdays'
# Observed photographic skyline at 1920×1280; not a measured terrain profile.
SKYLINE = [
    (0,510),(38,526),(74,493),(160,443),(259,402),(360,360),
    (480,334),(541,304),(590,282),(622,253),(670,234),(710,214),
    (755,200),(818,205),(877,222),(907,232),(973,224),(1026,224),
    (1080,232),(1120,240),(1167,261),(1200,290),(1221,312),
    (1267,331),(1308,347),(1359,374),(1400,398),(1444,420),
    (1483,440),(1522,456),(1570,498),(1614,536),(1658,568),
    (1693,587),(1741,624),(1787,658),(1837,684),(1880,707),(1920,722),
]


def vector_raster(filename, width, height):
    raw = cairosvg.svg2png(url=str(ART / filename),
                          output_width=width, output_height=height)
    with Image.open(io.BytesIO(raw)) as image:
        return image.convert('L')


def rainier_raster(source):
    with Image.open(source) as original:
        image = original.convert('RGB')
    image.thumbnail((1920, 1280), Image.Resampling.LANCZOS)
    gray = ImageOps.autocontrast(image.convert('L'), cutoff=.5)
    gray = gray.filter(ImageFilter.GaussianBlur(.6))
    mean = gray.filter(ImageFilter.GaussianBlur(20))
    # Open flat dark foreground into real photographed texture and edges while
    # retaining stronger tonal groups on the mountain. No terrain is invented.
    values = []
    for i, (value, local_mean) in enumerate(zip(gray.getdata(), mean.getdata())):
        y = i // gray.width
        strength = .80 + .20 * max(0, min(1, (y - 600) / 350))
        values.append(max(0, min(255, round(value + strength * (160 - local_mean)))))
    gray.putdata(values)
    sky = Image.new('L', gray.size, 0)
    ImageDraw.Draw(sky).polygon(SKYLINE + [(1920, 0), (0, 0)], fill=255)
    gray.paste(255, mask=sky)
    ImageDraw.Draw(gray).line(SKYLINE, fill=65, width=6)
    gray = gray.crop((0, 150, 1920, 1080))
    return ImageOps.expand(gray, border=30, fill=255)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rainier-source', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, default=ART)
    args = parser.parse_args()
    if hashlib.sha256(args.rainier_source.read_bytes()).hexdigest() != SOURCE_SHA256:
        parser.error('Rainier original checksum does not match the documented NPS source')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    vector_raster('friday-eiffel.svg', 1200, 1431).save(
        args.output_dir / 'friday-eiffel.png', optimize=True)
    needle = vector_raster('saturday-needle-refined.svg', 1440, 2304)
    needle = ImageOps.expand(needle.crop((162, 90, 1278, 1458)), border=25, fill=255)
    needle.save(args.output_dir / 'saturday-needle-refined.png')
    rainier_raster(args.rainier_source).save(args.output_dir / 'sunday-rainier-refined.png')
    print('Rebuilt three landmark PNGs; compare their checksums with catalog.json.')


if __name__ == '__main__':
    main()
