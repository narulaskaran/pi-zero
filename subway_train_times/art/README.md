# Board artwork

## Weekly collection

The board selects the same artwork for each weekday using **America/New_York** calendar dates, switching on the first normal refresh after local midnight. It does not choose again on each refresh, need a cron, or fetch art from the network.

| Day | Artist or treatment | Artwork | Source |
|---|---|---|---|
| Monday | Albrecht Dürer | The Rhinoceros | [356497](https://www.metmuseum.org/art/collection/search/356497) |
| Tuesday | Katsushika Hokusai | The Great Wave | [36491](https://www.metmuseum.org/art/collection/search/36491) |
| Wednesday | Bewick | A Bird | [National Gallery of Art, 124533](https://www.nga.gov/artworks/124533-bird) |
| Thursday | Adapted CC0 line art | Statue of Liberty detail | [FreeSVG](https://freesvg.org/statue-of-liberty) |
| Friday | Authored CC0 structural line study | Eiffel Tower | [Visual reference](https://www.musee-orsay.fr/fr/oeuvres/elevation-generale-de-la-tour-eiffel-68404) |
| Saturday | Authored CC0 architectural detail | Space Needle observation deck | [Visual reference](https://commons.wikimedia.org/wiki/File:Space_Needle_1997_Day.jpg) |
| Sunday | Adapted public-domain NPS photographic landscape | Mount Rainier from Spray Park | [NPS source and rights](https://npgallery.nps.gov/AssetDetail/caac960d-55ea-4666-9182-6893bc6854b8) |

[`weekdays/catalog.json`](weekdays/catalog.json) records the current seven selections,
their source/reference URLs, bundled SHA-256 checksums, and rendering treatments.
The renderer checks each bundled image against its recorded checksum and fits it
to the available region before thresholding, ordered halftoning, or dithering.
Captions may be ellipsized to fit.

Monday–Wednesday use historical prints. Thursday adapts a CC0 illustration.
The complete collection was approved in user review on 2026-11-11. Friday and
Saturday are authored architectural studies; Sunday is a photographic landscape
detail with tonal treatment. They are not historical engravings or measured
architectural/geographic records. See
[`weekdays/LANDMARK-STUDIES.md`](weekdays/LANDMARK-STUDIES.md) for the recorded
provenance and rights notes for these studies.

Only the selected weekday PNGs and editable SVGs for the two authored tower
studies are bundled. [Reproduction details](weekdays/LANDMARK-STUDIES.md) include
the deliberate Saturday crop and the NPS original needed to rebuild Sunday.
[The style guide](STYLE-GUIDE.md) records the collection's visual principles.
Superseded alternatives remain available in Git
history. The renderer uses IBM Plex Sans and IBM Plex Mono; their OFL license
texts are bundled in [`../fonts/`](../fonts/).

## Fallback artwork

Initial layout artwork: **The Rhinoceros**, Albrecht Dürer, 1515.

- The Metropolitan Museum of Art, object 356497
- Collection record: https://www.metmuseum.org/art/collection/search/356497
- Source image: https://images.metmuseum.org/CRDImages/dp/original/DT241450.jpg
- The Met Collection API identifies this object as `isPublicDomain: true`.
- Source SHA-256: `0ef189016f40f7edd267b263ca1984d1deeb5e586ff3d9d45cc91f82e7f62988`

The renderer crops normalized vertical coordinates 0.15–0.95, preserving the animal, adjusts contrast/brightness and renders a black-and-white derivative. This is a sourced historical print, not generated artwork.
