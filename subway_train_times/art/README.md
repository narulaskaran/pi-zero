# Public-domain artwork

## Weekly collection

The board selects the same artwork for each weekday using **America/New_York** calendar dates, switching on the first normal refresh after local midnight. It does not choose again on each refresh, need a cron, or fetch art from the network.

| Day | Artist | Artwork | Met object |
|---|---|---|---|
| Monday | Albrecht Dürer | The Rhinoceros | [356497](https://www.metmuseum.org/art/collection/search/356497) |
| Tuesday | Katsushika Hokusai | The Great Wave | [36491](https://www.metmuseum.org/art/collection/search/36491) |
| Wednesday | Utagawa Hiroshige | Snowy Landscape | [55603](https://www.metmuseum.org/art/collection/search/55603) |
| Thursday | Utagawa Hiroshige | Twilight Moon at Ryōgoku Bridge | [45294](https://www.metmuseum.org/art/collection/search/45294) |
| Friday | Giovanni Battista Piranesi | The Piazza del Popolo | [362729](https://www.metmuseum.org/art/collection/search/362729) |
| Saturday | Utagawa Hiroshige | The Kiso Mountains in Snow | [36545](https://www.metmuseum.org/art/collection/search/36545) |
| Sunday | Katsushika Hokusai | Seaside Village in Winter | [37193](https://www.metmuseum.org/art/collection/search/37193) |

Every source object's public-domain flag and exact image URL were verified against The Met Collection API. `weekdays/catalog.json` records full titles, source/image URLs, original and bundled checksums, crops and rendering treatments. Bundled PNGs are contrast-adjusted grayscale derivatives; the renderer scales them to the actual art region before thresholding or ordered halftoning. Rhino alone uses a documented crop; other works preserve the full composition. Quiet captions may be visibly ellipsized to fit.

## Fallback artwork

Initial layout artwork: **The Rhinoceros**, Albrecht Dürer, 1515.

- The Metropolitan Museum of Art, object 356497
- Collection record: https://www.metmuseum.org/art/collection/search/356497
- Source image: https://images.metmuseum.org/CRDImages/dp/original/DT241450.jpg
- The Met Collection API identifies this object as `isPublicDomain: true`.
- Source SHA-256: `0ef189016f40f7edd267b263ca1984d1deeb5e586ff3d9d45cc91f82e7f62988`

The renderer crops normalized vertical coordinates 0.15–0.95, preserving the animal, adjusts contrast/brightness and renders a black-and-white derivative. This is a sourced historical print, not generated artwork.
