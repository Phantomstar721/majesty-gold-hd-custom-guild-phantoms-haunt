# Majesty Building Shadow Encoding

This note records the working shadow format established while implementing the
Phantoms Haunt. It applies to custom Majesty building sprites stored as indexed
TILE v3 images.

## What the Engine Actually Renders

Majesty does not calculate a building's ground shadow from its alpha or
silhouette at runtime. The shadow is authored into the TILE as reserved palette
indices. Raw indexed previews show these pixels as red and magenta, but the game
interprets them as shadow/blend controls.

The stock Wizard Guild is the reference implementation. Its raw control-index
frames are preserved at:

```text
artifacts/references/wizard_guild_build_tile01780_raw_controls.png
artifacts/references/wizard_guild_inactive_tile01781_raw_controls.png
artifacts/references/wizard_guild_damaged_a_tile01782_raw_controls.png
artifacts/references/wizard_guild_damaged_b_tile01783_raw_controls.png
artifacts/references/wizard_guild_destroyed_tile01784_raw_controls.png
```

The current Phantoms Haunt generator projects each frame's opaque silhouette
toward the upper-left in sprite coordinates, consistent with Majesty's
apparent light source over the viewer's right shoulder. The affine projection
also compresses tall geometry toward its ground contact, so this should not be
described or tuned as a lower-left cast. Construction, inactive, active,
damaged, and destroyed frames must each use their own visible geometry.

The projected mask is ground shadow only. Do not apply it over the opaque
building body. Surface lighting and self-shadowing belong in the ordinary
building artwork and must follow the geometry shown in that individual frame.

## Reserved Palette Indices

The Wizard Guild reference uses these exact control entries:

| Index | Reference RGB | Purpose |
| ---: | --- | --- |
| `247` | `(156, 33, 24)` | Red transition/seam control |
| `248` | `(178, 0, 178)` | Shadow band |
| `249` | `(204, 0, 204)` | Shadow band |
| `250` | `(229, 0, 229)` | Shadow band |

The RGB values are how the indexed pixels appear in a raw preview; the palette
indices are what matter to the renderer. The Phantoms Haunt uses registered
palette `560`, whose entries `247-250` are patched to these reference values.

Do not append a new SPLT palette for a mod building merely to add these colors.
Majesty does not register that palette at runtime and can crash with:

```text
Attempt to do 816 blit without a palette
```

Ordinary visible artwork must quantize to indices `1-246`. Index `0` is
transparent. Do not allow normal art to quantize into the control range, and do
not use reserved indices `251-255` in these custom building frames.

## Critical RLE Segment Rule

The red seam is not simply a visible one-pixel outline. It terminates the
shadow-control RLE segment before the ordinary building pixels begin.

A correct row boundary is conceptually:

```text
segment A: [shadow 248-250 ... transition 247]
segment B: [ordinary building pixels 1-246 ...]
```

Segments A and B must touch. There is no transparent pixel or horizontal gap
between them. They are separate records in the TILE v3 row even though their
pixel coordinates are adjacent.

Direct transitions from a shadow index to a body index must also split into
separate segments. More generally, no TILE v3 RLE segment in a shadowed building
frame may contain both:

```text
control indices: 247-250
body indices:      1-246
```

This was verified against the stock Wizard Guild TILE:

- Every observed `248-250 -> 247 -> body` transition kept the shadow and red
  seam together, then began the body in a new segment.
- Every observed direct `shadow -> body` or `body -> shadow` transition crossed
  a segment boundary.

Our original encoder combined the control pixels and following body pixels
because they were all nonzero and contiguous. Majesty then applied the
shadow/blit semantics to the rest of that segment. The visible result was
ordinary building artwork disappearing in repeated horizontal bands,
especially in the deliberately darkened parts of the source art.

Changing RGB values, thickening the seam, or altering the body silhouette
cannot correct that failure. The RLE segment structure must be fixed.

## Art Boundary Rules

- Paint indices `248-250` only on the projected ground-shadow area.
- Put index `247` at the contact seam where the ground-shadow controls meet the
  building body.
- Keep the seam continuous across horizontal, vertical, and diagonal contacts.
- Do not insert index `0` between the seam and the body. That produces a
  one-pixel strip of visible terrain between the building and its shadow.
- Do not limit gap detection to a literal one-pixel sandwich. Construction
  scaffolds, damaged walls, rubble, and balcony notches can leave a
  multi-pixel transparent channel connected to the exterior. Measure through
  transparent space from both the projected magenta shadow and the authored
  body. A narrow channel between them is part of the shadow, even when it is
  not an enclosed transparent component.
- Fill the complete channel with the nearest shadow band first. Then derive
  index `247` only on the final shadow pixels touching actual body art. The
  Phantoms Haunt generator performs this for gaps up to 14 pixels deep on the
  shadow-facing side and inside concave row spans.
- Preserve the nearest existing `248-250` feather band when filling a channel;
  hard-coding one band produces conspicuous blocks of a different magenta in
  raw frames and a different blend strength in game.
- Fill a transparent component only when its complete boundary is shadow
  control. This removes black islands inside the projected shadow without
  painting legitimate openings bounded by scaffold or building artwork.
- Keep this fill out of the lit/right exterior. A projected mask may pass
  behind transparent openings in the two-dimensional sprite, but it must not
  wrap the ground shadow around the front of the building.
- Construction frames use an additional upper-left-facing domain. Their
  permissible concavity depth remains the full 14-pixel pit distance, but
  tapers to zero at the ground-contact row. Narrowing the horizontal domain
  below 14 pixels reopens scaffold pits; the vertical taper and state-specific
  bottom clearance prevent controls from collecting along the bottom and right
  perimeter while still allowing the seam to close against scaffold geometry.
  A flat foundation/rubble stage may also need a small bottom clearance so
  isolated foreground boards do not drag the shadow down to the sprite base.
- The literal local contact remains the final safety check: if a transparent
  index-`0` pixel touches both a magenta shadow index `248-250` and ordinary
  body art in its eight neighboring pixels, that transparent pixel must become
  red seam index `247`.
- Do not place red seam pixels around magenta areas that border only transparent
  background; those become orphan red artifacts.
- Remove transparent or near-black antialias fringe at the artwork boundary.
  Preserve genuinely dark artwork as an opaque, nonzero body index.
- Never reuse the completed building's body or shadow mask for an unfinished
  construction frame.
- Leave at least one transparent column on both sides of every construction
  TILE. A frame that touches either fixed side boundary is clipped and must
  fail generation/validation rather than reaching the game.

## High-Resolution Generated State Workflow

The first successful Phantoms Haunt destruction pass established a repeatable
way to create missing building states without asking the image model to produce
engine-ready pixels:

1. Use the existing clean high-resolution building sheet as the authoritative
   reference for architecture, footprint, isometric camera, palette, material,
   entrance direction, and lighting.
2. Generate one missing structural concept at a time. Specify its exact place
   between the preceding and following states, and supply both as references
   when possible.
3. Keep effects out of the source art: no fire, smoke, dust, ground, cast
   shadow, units, labels, UI, or health bars. Majesty adds destruction effects
   through separate animation layers, while the sprite generator authors the
   ground-shadow controls.
4. Generate on a flat chroma-key magenta background. Remove the background and
   antialias spill before grading, resizing, or shadow projection.
5. Preserve each accepted high-resolution state as its own versioned source
   asset. Never silently substitute an earlier or later state when a source is
   missing.
6. Grade and downscale each state independently into its stock TILE dimensions,
   then derive the shadow from that downscaled state’s actual silhouette.
7. Review both the high-resolution progression and a nearest-neighbor contact
   sheet of the exact engine-sized frames before building.

For the Phantoms Haunt, the validated Fervus-compatible progression is:

| Engine state | Tile | High-resolution concept |
| --- | ---: | --- |
| Damaged A | `1529` | Existing damaged source |
| Damaged B | `1530` | `phantom-guild-damaged-b-sample-v1.png` |
| Collapsed intermediate | `1531` | `phantom-guild-collapsed-intermediate-sample-v1.png` |
| Final rubble | `1508` | Existing destroyed source |

The accepted engine fitting values are deliberately state-specific:

| State | Scale multiplier | X offset | Shadow `(shear, vertical scale)` |
| --- | ---: | ---: | --- |
| Damaged B | `0.88` | `+10` | `(0.43, 0.81)` |
| Collapsed intermediate | `0.92` | `+8` | `(0.27, 0.88)` |

These numbers are not universal defaults. They record why this art fits its
fixed Fervus canvases without clipping. A future sprite must be measured again.
The invariant is that top, left, right, and reserved bottom gutters remain
transparent after the shadow is painted. The generator and post-build
validator now reject the two transitional Phantoms Haunt frames if they touch a
fixed top or side boundary.

### Upgrade-Level Art Sets

Each Haunt level must be generated into a separate working directory. The
Fervus upgrade IMAGs reuse some source TILE numbers (including the final
destroyed tile), and every level emits identically named active frames; merging
the directories would silently overwrite one level with another.

The Level 2 and Level 3 production paths each provide:

- separate early and late upgrade-construction sources;
- active architecture plus a derived inactive variant;
- eight full-building active pulse frames;
- damaged A, derived damaged B, collapsed intermediate, and final destroyed
  sources;
- state-specific sizing, palette grading, cast shadows, and seam controls.

The resulting tiles are appended as distinct `PHG2Bld`/`PHG2Act` and
`PHG3Bld`/`PHG3Act` families. Only their matching cloned Fervus upgrade IMAG is
remapped. The post-build validator treats every nonblank member of those
families as a shadowed building TILE and independently checks ownership, RLE
class splits, shadow/body seams, construction gutters, and reserved indices.

## Stock Destruction Overlay Attachments

Fire, smoke, and dust are separate IMAG animation layers; they are not part of
the building TILE or its magenta ground shadow. Cloning a stock building IMAG
also clones those attachment positions, which may not fit custom geometry.

For Fervus-derived destruction states, composite set IDs encode the overlay
layer in the high byte and the base death state in the low word. The Phantom
Guild’s inherited upper-right fire was layer 3 on states `99-103`:

```text
0x03000063 through 0x03000067
```

The correct signed `(x, y)` attachment coordinate begins exactly at:

```text
set_offset + u32(set_offset + 64)
```

Do not add `4` or `8` bytes. Writing later metadata can leave the visible
effect unchanged while a mistaken validator appears to pass. After patching,
read the built custom IMAG record back independently and verify the real
coordinates. The Phantoms Haunt remaps those five layer-3 anchors to `(35, 25)`.

Patch every engine state that displays the mismatched overlay, not merely the
last rubble state. Base states `98-103` map in pairs to damage tiles `1529`,
`1530`, and `1531`; the separate `Crumble` set `240` then holds `1531` before
switching to final tile `1508` while its dust layer advances.

Only patch the cloned custom IMAG entry. The stock source building archive and
its original Fervus attachment coordinates must remain unchanged.

## Encoder Requirements

TILE v3 row segments have this form:

```text
u16 x_end
u8  count
u8  flags
u8[count] palette_indices
```

The custom building encoder must terminate its current segment whenever the
next nonzero pixel changes class between:

```text
shadow/control: 247-250
ordinary body:    1-246
```

This class split is implemented by `split_shadow_controls=True` in
`src/build_phantom_guild.py`. It is deliberately enabled for native-size
custom building PNG conversion.

The post-build validator independently decodes every custom shadowed building
TILE and fails the build if a segment contains both classes or if transparent
index `0` remains trapped between shadow controls and building art. A successful
build prints only:

```text
Verification passed.
```

Do not remove this validation when changing the TILE encoder.

## Failure Signatures

| In-game result | Likely cause |
| --- | --- |
| No ground shadow | Missing or incorrectly mapped indices `248-250` |
| Magenta/red visible in game | Wrong palette, wrong control indices, or control pixels used outside the supported building path |
| One-pixel terrain/bright gap | Index `0` or omitted shadow pixels between the shadow and body |
| Horizontal bands of missing building pixels | Shadow controls and body pixels share one RLE segment |
| Dark portions disappear preferentially | Same mixed-segment failure; it is not proof that dark RGB itself is transparent |
| Red outline away from the building | Orphan index `247` around shadow/background rather than shadow/body contact |
| `Attempt to do 816 blit without a palette` | TILE references a palette Majesty did not register |

## Reproduction Checklist

1. Inspect the clean art and author its surface lighting for the frame's actual
   geometry.
2. Build an opaque body mask, cleaning only transparency/antialias fringe.
3. Project that frame's silhouette toward the upper-left in sprite coordinates
   to create the ground shadow.
4. Quantize the shadow into indices `248-250`.
5. Fill narrow transparent shadow/body channels, then add index `247` only at
   the resulting shadow-to-body contact.
6. Quantize all visible art to indices `1-246`; use `0` only for true
   transparency.
7. Encode control and body pixels as separate, touching RLE segments.
8. Run the normal build and require `Verification passed.` before deployment.
9. Test in Majesty, including every construction and damage state; binary
   validation cannot verify the artistic direction or geometry of a shadow.
