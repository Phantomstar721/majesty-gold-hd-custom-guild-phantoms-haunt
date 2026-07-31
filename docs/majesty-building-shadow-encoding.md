# Majesty Building Shadow Encoding

Custom Guild: Phantoms Haunt uses indexed TILE v3 images for its building
frames. Majesty does not derive building shadows from alpha at runtime; the
shadow is encoded directly into each TILE with reserved palette-control
indices.

## Palette contract

Ordinary visible art uses palette indices `1-246`, while index `0` remains
transparent. Building shadows use the engine-supported control range
`247-250`.

The registered Phantoms Haunt palette preserves the stock control colors:

| Index | Reference RGB | Role |
| ---: | --- | --- |
| `247` | `(156, 33, 24)` | Transition and seam control |
| `248` | `(178, 0, 178)` | Shadow band |
| `249` | `(204, 0, 204)` | Shadow band |
| `250` | `(229, 0, 229)` | Shadow band |

The RGB values describe the raw indexed preview. In game, Majesty interprets
the indices as terrain-darkening controls.

## Generation

Each building state is processed independently:

1. Load the approved high-resolution source for that exact state.
2. Crop and fit it to the native stock TILE geometry.
3. Quantize visible pixels into the safe palette range.
4. Project the opaque silhouette toward the upper-left.
5. Compress the projection vertically toward the building's ground contact.
6. Add a narrow transition seam where the building meets the projected mask.
7. Encode visible art and shadow controls into separate TILE v3 RLE segments.

Construction, inactive, active, damaged, collapsed, and destroyed frames use
their own silhouettes. This keeps the shadow consistent with the visible
geometry throughout construction and destruction.

## RLE requirement

Majesty's TILE v3 decoder treats visible palette pixels and shadow-control
pixels as different semantic classes. A single encoded RLE segment must never
mix the two classes.

The builder splits rows at every visible/shadow transition. The validator
decodes every generated building TILE and confirms:

- no segment mixes visible and shadow-control indices;
- all indices remain in the approved ranges;
- transition seams exist where required;
- construction transparency remains connected to the exterior;
- each expected custom TILE and palette mapping is present.

## Stock reference

The Wizard Guild's build, inactive, damaged A, damaged B, and destroyed frames
at stock TILE indices `1780-1784` provide the reference control behavior. The
Phantoms Haunt uses its own appended TILE names and does not overwrite those
stock records.

## Source layout

Approved building sources are organized by level:

```text
assets/source/buildings/haunt/level-1/
assets/source/buildings/haunt/level-2/
assets/source/buildings/haunt/level-3/
```

The default build invokes `scripts/generate_phantom_building_sprites.py` for
each level and packages the resulting frames through
`src/build_phantom_guild.py`.
