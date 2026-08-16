# Hero CAM Art Pipeline Notes

These notes consolidate the stock `maindata.cam` structure used by the Phantom
hero. They describe CAM/IMAG/TILE art wiring, not GPL actions.

## Short answer

For the Phantom, the safest definition of a complete hero was the full stock
Priestess IMAG contract. We cloned `AVG1Priestess` into `PHM1Phantom`, preserved
its record structure, replaced its art, and remapped only the referenced TILE
indices. The source IMAG contains these 12 sets:

| setID | Meaning | Phantom source TILEs | Practical status |
|---:|---|---:|---|
| 1 | Walk | 4586-4649 | Core |
| 8 | Stand | 4650-4657 | Core |
| 64 | Special | 4658-4689 | Core; preserve even if the hero uses a simple/fallback animation |
| 16 | Attack | 4690-4721 | Core |
| 96 | Die | 4722-4745, then shared 4778-4785 | Core |
| 128 | Cast | 4746-4777, plus shared effects 4788-4791 | Core; preserve for a stock-shaped hero even if rarely called |
| 1000 | Interface | 4786 | Portrait |
| 224 | Dead | 4787 | Dead/gravestone world art |
| 400 | Hotspot | references 4586 | Hero-level selection/position metadata |
| 1002 | Interface-02 | 4792 | Small hero icon |
| 1001 | Interface-01 | 4793 | Selected-unit/interface panel art |
| 300 | Minimap | 3729 | Minimap marker; shared stock tile is acceptable |

The TILE numbers above are the **stock Priestess source range**, not reserved
destination numbers for every custom hero. Phantom art was appended at new,
collision-free global TILE indices, and the cloned IMAG's low 16-bit TILE
references were remapped to those new indices.

## Mandatory versus optional

All 14 stock base-game playable hero IMAGs inspected carry the same 12-set core
contract above, even when a class is not an obvious caster. For a reliable new
hero, preserve all 12 rather than deleting apparently unused sets.

Additional animation families are class- or object-specific:

| setID | Meaning | Use for a normal hero |
|---:|---|---|
| 2-4 | Walk variants | Optional; only when the cloned stock hero/mechanic uses them |
| 17-19 | Attack variants | Optional |
| 65-67 | Special variants | Optional |
| 80-83 | Build | Not part of the ordinary hero contract; used by builders/buildings as appropriate |
| 97-103 | Die variants | Optional; ordinary heroes generally use 96 |
| 129-131 | Cast variants | Optional |
| 144-147 | Carry variants | Optional and class-specific; Ranger/Rogue-family records demonstrate it |
| 160-163 | Recoil | Not in the normal stock hero contract |
| 176-179 | Stand/walk transitions and turns | Not in the normal stock hero contract |
| 192-211 | Active/inactive variants | Object/mechanic-specific, not normal hero requirements |
| 240 | Crumble | Object/building-specific |
| 316 | Damage | Object/building-specific |
| 500/550 | Selection variants | Object-specific; do not add unless the stock analogue uses them |

`ImageSetIDXRef.xml` is a useful semantic catalog, but it does not mean every
listed family belongs in every IMAG. The cloned stock analogue is the authority.

## Direction-table correction

The claim that direction slots 0-1 are empty and 2-7 are used is not correct
for the stock Priestess or working Phantom hero IMAG. It comes from reading the
direction table at `set block + 0x38`; those two zeroes are preceding fields.

For the six primary hero animation sets, the eight signed relative direction
offsets begin at `set block + 0x40`, and all eight entries are populated. Keep a
single, consistent eight-direction ordering across Walk, Stand, Attack, Special,
Die, and Cast.

## Primary animation layout

An IMAG header stores the set count at `+0x14`, followed at `+0x18` by entries
of `(u32 setID, u32 relativeOffset)`. Within each primary set, direction blocks
retain geometry at direction-block `+0x14` (`s16 x`, `s16 y`, `u16 width`,
`u16 height`). Preserve the cloned structure and geometry unless the replacement
pipeline deliberately recomputes them.

The first visual frame-pair offset is not identical for every family:

| Set | First visual pair | Unique visual tiles per direction | Playback note |
|---|---:|---:|---|
| Walk 1 | `+0x28` | 8 | Eight unique frames |
| Stand 8 | `+0x30` | 1 | A control/non-art pair precedes the visual frame |
| Special 64 | `+0x28` | 4 | Four visual frames |
| Attack 16 | `+0x28` | 4 | Playback references `0,1,2,3,2,1,0` |
| Die 96 | `+0x28` | 3 | Begins directionally, then enters shared death/dissolve frames |
| Cast 128 | `+0x30` | 4 body frames | A control pair precedes the body; later pairs attach shared effects and recover |

Do not flatten these into a generic “N consecutive frame records” writer. Clone
the closest stock hero's complete IMAG and patch its TILE references.

## TILE hotspots, IMAG Hotspot, and attachments

These are related but distinct concepts:

- A TILE v3 record contains its per-image anchor/hotspot at TILE offsets `+10`
  and `+12`. Keeping the canvas, feet, and hotspot stable prevents sprites from
  jumping between animation phases.
- IMAG set 400 is the hero-level Hotspot set. In the Priestess scaffold it
  references the first Walk tile and carries selection/position metadata. Keep
  the stock structure unless there is a proven reason to alter it.
- Animation frame pairs can contain coordinate metadata/attachment offsets as
  well as the TILE reference. Priestess Cast uses these to place the attached
  spell effect; Phantom's staff glow uses a stable `(2, -5)` attachment offset.
- A frame's TILE word may store flags in its high 16 bits (`0x8000` and
  `0x4000` occur in Cast). Remap only the low 16-bit TILE index and preserve the
  high bits.

For Phantom Cast, all four body phases in a direction were fitted to the same
canvas/hotspot geometry. This prevented the feet and attached glow from bouncing.

## Palette and archive rules

Every TILE points to an SPLT palette index. A custom hero does not strictly have
to use only an existing stock SPLT: Phantom body art uses a valid existing hero
palette where appropriate, while its portrait/icon use the appended custom SPLT
slot 560. The real requirements are that the SPLT index exists, global indices
do not collide, and the relevant control colors retain their meaning.

Sprite palettes commonly reserve index 247 for transition/seam behavior and
248-250 for shadow bands. Palette cleanup must be asset-category-aware; profile
paintings and interface art are not interchangeable with world sprites and can
legitimately use high palette indices as ordinary colors.

TILE and SPLT IDs are global CAM registries. A sparse mod CAM must contain empty
placeholder entries below its highest custom slot; the engine can then fall back
to stock data for those empty entries. Do not overwrite stock TILE/SPLT slots to
install custom hero art.

## Phantom implementation recipe

1. Read the complete stock `AVG1Priestess` IMAG.
2. Generate all eight directions for the six primary animation families with a
   consistent direction map.
3. Fit replacement art to the cloned stock TILE geometry, deliberately preserving
   or recomputing the TILE hotspot so the feet stay fixed.
4. Add portrait, icon, interface panel, dead marker, and any custom effect art.
5. Append the replacement TILEs and any custom SPLT at collision-free global IDs.
6. Clone the IMAG as `PHM1Phantom` and remap every referenced TILE's low 16 bits,
   preserving flags, control pairs, direction tables, coordinates, playback
   repetition, and attachment metadata.
7. Keep the shared stock minimap tile or replace it intentionally.
8. Validate that all six primary sets have eight populated directions and that
   every referenced TILE/SPLT resolves.

