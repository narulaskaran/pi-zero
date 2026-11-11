# Monochrome artwork style guide

The accepted Dürer rhinoceros, Hokusai wave, Bewick bird and Liberty detail
establish the collection's visual direction. Bewick and Liberty are the clearest
controls for new white-ground landmark illustrations. Preserve accepted artwork.

## What makes the accepted pieces work

- **Recognizable form first.** The silhouette, proportions and major internal
  shapes identify the subject before the caption does. Detail supports that form.
- **A hierarchy of marks.** Strong outer contours and structural edges lead;
  lighter interior cuts, hatching and small accents follow. Uniform hairlines
  produce a diagram, while uniformly heavy strokes clog the drawing.
- **Shading describes volume.** Marks follow feathers, folds, armor or surfaces.
  Group them into deliberate light, middle and dark areas. Leave highlights open;
  avoid a flat mesh of equally spaced lines or arbitrary decorative scratches.
- **Richness stays inside the subject.** Clean white surroundings separate the
  artwork from the board. Do not add paper tint, stippled sky, gray background
  fields or a frame merely to make an illustration feel complete. Hokusai's
  accepted treatment is not a requirement to add background halftones elsewhere.
- **Dark accents have a purpose.** Use them for recesses, undersides and overlaps,
  balanced by white cuts. Avoid both large featureless black masses and an
  outline-only subject with no tonal body.
- **Natural irregularity follows structure.** Vary stroke length and spacing
  deliberately. Do not simulate engraving with random noise, repeated hatch
  stamps or unsupported architectural/geographic detail.
- **The whole composition survives reduction.** Small detail may disappear, but
  silhouette, landmark identity and the principal shadow masses must remain.

## Applying the style to provisional landmarks

### Eiffel Tower

Resolve silhouette, platform proportions, the lower arch and the open ironwork
before texture. Establish distinct leg faces and a coherent light direction;
use selected cross-bracing and underside shadows to convey iron construction.
Avoid repeated curved spans and sparse triangular scaffolding. Fine lattice
must support the large shapes instead of becoming an evenly weighted mesh.

### Space Needle

Make the observation deck, glazing band, roof and underside read as one solid
three-dimensional form. Resolve the real shaft and swept support arrangement
against references before adding detail. Give supports front/back separation
through contour weight and selective shadow. Avoid invented lattice, extra
platforms, uniform hairlines and a saucer perched on a wire cage.

### Mount Rainier

Establish a recognizable broad, asymmetric glaciated massif from a documented
viewpoint. Organize snowfields, ridges and shadowed rock into a few legible forms
before drawing smaller terrain cuts. Avoid a generic cone, symmetrical slopes,
wireframe contours or invented glacier geography. Label authored interpretations
honestly and retain the exact visual references.

The mountain must also communicate **landscape scale**. A narrow cutout of the
summit can read as an isolated rock even when its geography is accurate. Retain
enough descending flanks, snowfields and foothills to establish a whole mountain;
a few small trees or restrained foreground forms can provide scale. Avoid a
floating sliver, a long diagonal crop edge, or a foreground that competes with
the summit. Keep the sky white and judge the full composition at both slot sizes.

## Iteration and acceptance

1. Inspect the accepted controls, exact current raster and previous rejected
   attempts before drawing. State the visible problem and a different approach.
2. Keep editable sources and reproducible raster preparation. Record reference
   URLs, rights, derivative labeling, crop, padding, resize and binary treatment.
3. Fit grayscale artwork before final binary conversion unless a native proof
   demonstrates that another sequence is better. Repeated source thresholding
   and resizing can erase fine cuts or create coarse lines.
4. Render through the real Flask `/display.bmp` route with fixed example data.
   Decode the raw response and assert 800×480 pixels and mode `1` before any
   conversion. Inspect expanded, one-, two-, three-, four-reminder, overflow and
   long-text states. Read actual geometry from the renderer.
5. Compare at native size, with particular attention to the smallest crowded
   slot. Enlargement is useful for diagnosis, not acceptance. A candidate must
   improve form, tonal coherence and useful detail at both extremes.
6. Require unchanged non-art pixels and unchanged accepted-day rasters. Preserve
   captions, layout, weather, reminders, battery, timestamps and refresh policy.
7. Use a cold visual review. Valid files, nonblank output, higher ink coverage
   and recognizability alone do not establish aesthetic quality. Keep reviewer
   judgment separate from explicit user acceptance.
8. Limit repeated corrections. When extra marks fail to improve the same
   drawing, change the structure or source approach instead of adding more.

New illustrations should belong beside the bird and Liberty without pretending
to be historical engravings or measured architectural/geographic records.
