# Approved landmark artwork

The complete seven-day collection was approved in user review on 2026-11-11.
Monday–Thursday retain their existing source images and treatments. The three
landmark selections below reproduce the approved expanded and crowded proofs.
They are not historical engravings or measured architectural/geographic records.

## Friday: Eiffel Tower

Newly authored CC0 structural line study, with converging supports, level
platforms, selected cross-members and a broad lower opening. The editable
`friday-eiffel.svg` is rasterized directly to a 1200×1431 grayscale PNG;
production fits it with Lanczos and thresholds at 190.

Visual/factual references, not copied image sources:

- [Musée d'Orsay elevation](https://www.musee-orsay.fr/fr/oeuvres/elevation-generale-de-la-tour-eiffel-68404).
  The museum's photographic reproduction is separately copyrighted; it is not
  embedded, traced or redistributed in the authored artwork.
- [1889 summit engraving](https://commons.wikimedia.org/wiki/File:Le_sommet_de_la_Tour_Eiffel._Coupe_dessin%C3%A9ee_par_M._Rouillard.jpg),
  identified as public domain on its source page, informed tonal choices only.
- Official [history](https://www.toureiffel.paris/en/the-monument/history) and
  [key figures](https://www.toureiffel.paris/en/the-monument/key-figures).

New illustration dedication: [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).

## Saturday: Space Needle observation-deck detail

Newly authored CC0 architectural interpretation. The full editable
`saturday-needle-refined.svg` is retained. Its 1440×2304 grayscale raster is
cropped to `(162, 90, 1278, 1458)`, then given a 25-pixel white border. This
purposeful deck detail preserves the roof, glazing, underside and upper support
forms at the small display size. Production fits grayscale before Pillow's
default 1-bit dithering. It is not a full-tower or measured engineering drawing.

Visual/factual references, not traced or embedded:

- [1997 Space Needle photograph](https://commons.wikimedia.org/wiki/File:Space_Needle_1997_Day.jpg),
  separately licensed CC BY-SA 3.0 on its source page.
- [Seattle historical design references](https://www.seattle.gov/documents/departments/neighborhoods/historicpreservation/landmarks/landmarkspreservationboard/meetingdocuments/lpb071522_spaceneedle_brief.pdf).
- [Space Needle press kit](https://www.spaceneedle.com/press-kit).

The authored illustration, rather than any reference photograph, is dedicated
[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).

## Sunday: Mount Rainier from Spray Park

Adapted photographic landscape detail retaining the broad summit, connected
snowfields, descending flanks and foreground firs for scale. This replaces the
earlier generic mountain drawing and isolated summit cutout.

- [NPS item and rights metadata](https://npgallery.nps.gov/AssetDetail/caac960d-55ea-4666-9182-6893bc6854b8).
  Credit: **NPS Photo**. Item constraints: **Public domain:Full Granting Rights**.
- [Original 6000×4000 JPEG](https://npgallery.nps.gov/GetAsset/caac960d-55ea-4666-9182-6893bc6854b8/original.jpg).
- Original SHA-256: `ea1395f127eb6bf51662b9101c3d52cb941c4f1d25e12024112677b6244c09e2`.

Preparation preserves the photo's aspect ratio at 1920×1280. It uses grayscale
autocontrast (0.5% cutoff), a 0.6-pixel source blur, and local tonal normalization
against a 20-pixel blurred mean. The normalization opens flat dark foreground
areas into photographed edges and texture. Sky above the observed silhouette
is removed; that silhouette receives a 6-pixel source outline. A
`(0, 150, 1920, 1080)` crop and 30-pixel white border retain the fuller landscape.
Production fits grayscale, then thresholds at 136. No hidden terrain is
reconstructed. This is a photographic treatment, not an engraving.

## Reproduction and runtime

[`../rebuild_landmarks.py`](../rebuild_landmarks.py) reproduces the three PNGs
using Pillow and CairoSVG. Supply the exact NPS original locally:

```sh
python rebuild_landmarks.py --rainier-source rainier-original.jpg --output-dir /tmp/rebuilt-art
```

The script checks the original checksum before processing it. Source images
and preparation are offline build inputs; normal display requests never fetch
reference images. The catalog records exact approved PNG checksums and rendering
treatments. Existing bundled fonts retain their separate OFL licenses.
