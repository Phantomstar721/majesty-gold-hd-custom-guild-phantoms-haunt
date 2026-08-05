# Packaging Architecture

Custom Guild: Phantoms Haunt is an additive Majesty Gold HD mod package. The
same package supports Original Majesty and the Northern Expansion.

## Package layout

```text
CustomGuildPhantomsHaunt.mmxml
Data/
  Phantom.bcd
  phantom_actions.xml
  phantom_gpltext.cam
  phantom_interfacedata.cam
  phantom_maindata.cam
  phantom_miscdata.cam
  phantom_overlays.xml
  phantom_particles.xml
  phantom_projectiles.xml
  phantom_sounddesc.cam
  phantom_sounds.xml
  phantom_textdata.cam
  phantom_units.xml
  phantom_voices.cam
GPL/
  Phantom.gpl
  Phantom.gplproj
  Phantom_Building_Data.dat
  Phantom_Hero_Data.dat
  Phantom_Items_Data.dat
```

The manifest loads one `Dataset base="Any"` block so the same custom records
are available under both game datasets.

## Build stages

`scripts/Build-CustomGuildPhantomsHaunt.ps1` performs a complete build:

1. Resolve and validate source assets.
2. Generate interface icons and raw RGB inputs.
3. Generate level-specific building frames.
4. Generate hero animation frames.
5. Build custom CAM archives and XML descriptions.
6. Generate GPL source and data files.
7. Compile GPL with the Majesty SDK compiler.
8. Copy compiled bytecode into `Data/`.
9. Validate the complete package.

The Python builder reads stock CAM directory structures and creates additive
archives containing only required cloned structures and custom entries.

### Tile slots and package size

Majesty resolves a tile by its position within a CAM's TILE section. An archive
that appends custom tiles must therefore contain an entry for every slot below
the highest index it uses, and the Haunt's building art is cloned from Fervus
temple records sitting near the very top of the stock table, so the array has to
run the full length.

Those in-between slots are written as **zero-length entries**. The engine treats
a slot with no payload as no contribution and falls back to the stock archive,
so stock artwork renders normally and the package ships none of it. The current
validated package is roughly 16 MB; its exact size may move slightly as custom
art and audio evolve.

Package validation uses archive-specific allowlists and rejects any nonempty
unreferenced TILE payload, even a single unexpected byte.

### BDEP mod compatibility

Majesty requests one `DATA/BDEP` resource and parses the returned blob as the
complete building dependency table. CAM records with the same section and name
override one another according to the effective mod/archive order; their text
payloads are not concatenated or merged.

The official Haunt package therefore contains the complete installed stock BDEP
table followed by its one rule:

```text
PHG1 : ABJ2 ABJ3 NOT NOT ||
```

If another custom-building mod also supplies `DATA/BDEP`, a separate
compatibility provider must be made:

1. Start with the unmodified BDEP payload from the installed game's
   `Data/miscdata.cam`.
2. Append each mod's custom dependency rule exactly once, retaining CRLF line
   endings and the final newline.
3. Package that combined payload as the single effective `DATA/BDEP` record
   after the individual providers in the active mod/archive order.
4. Test every affected building's visibility at each relevant Palace level.

Do not concatenate two complete modded BDEP payloads: that duplicates the stock
table. Do not edit either mod's official archive in place. The compatibility
provider should be separately named and versioned for the exact pair of mods it
supports.

## Archive responsibilities

| Archive | Content |
| --- | --- |
| `phantom_maindata.cam` | Building, hero, spell, projectile, overlay, particle, icon, palette, and TILE data |
| `phantom_interfacedata.cam` | Custom recruitment-panel raw texture |
| `phantom_textdata.cam` | Menu and description strings |
| `phantom_gpltext.cam` | GPL-facing names and help text |
| `phantom_miscdata.cam` | Full stock BDEP table plus the Haunt's native level-2 Palace dependency |
| `phantom_voices.cam` | Event-specific PCM WAVE payloads |
| `phantom_sounddesc.cam` | Runtime DSND registrations |

The package deliberately carries no Phantom spell or equipment UI-icon art.
Majesty does not resolve those custom entries through a mod CAM, so retaining
generated icons or unchanged stock icon sheets would add misleading dead data.

XML descriptions provide units, actions, projectiles, overlays, particles, and
sound metadata. GPL provides behavior, decision integration, progression,
equipment, compatibility, and spell mechanics.

## Incremental builds

After a complete validated package exists:

```powershell
.\scripts\Build-CustomGuildPhantomsHaunt.ps1 -GplOnly
.\scripts\Build-CustomGuildPhantomsHaunt.ps1 -GameplayOnly
.\scripts\Build-CustomGuildPhantomsHaunt.ps1 -TextOnly
.\scripts\Build-CustomGuildPhantomsHaunt.ps1 -InterfaceOnly
.\scripts\Build-CustomGuildPhantomsHaunt.ps1 -AudioOnly
.\scripts\Build-CustomGuildPhantomsHaunt.ps1 -AudioOnly -GplOnly
```

`-GplOnly` regenerates and compiles gameplay source without rebuilding art.
`-GameplayOnly` regenerates unit-description XML and compiles GPL without
rebuilding art; use it when a change spans data values and decision logic.
`-TextOnly` rebuilds only the text CAMs. `-InterfaceOnly` rebuilds only the
custom recruitment-panel CAM.
`-AudioOnly` consumes the final `assets/audio/phantom-*-game.wav` files and
rebuilds the voice, sound, unit, and manifest components required by the audio
contract. Raw recording projects and clean intermediate masters are not
required or published.
`-AudioOnly -GplOnly` updates both runtime areas in one staged transaction when
a change spans sound registration and behavior, while still leaving art CAMs
untouched.

## Validation

`src/validate_phantom_build.py` verifies:

- the exact expected package file set;
- CAM headers, directories, section names, entry ranges, and payload bounds;
- custom WAVE format, DSND nested sizes and boundaries, and phase routing;
- XML identity and cross-reference contracts;
- unique custom IDs and stock-record preservation;
- indexed TILE structure, palette mappings, shadow controls, and custom image
  ownership;
- GPL source contracts and compiled bytecode consistency;
- building availability, hero progression, equipment, spell, and quest
  compatibility requirements.

## Local development

A validated package can be copied directly into the content directory of a
locally subscribed Workshop item while developing and testing. This avoids
using RGSeditor for every iteration. RGSeditor is required only for the final
publication or update operation.

Item identifiers, machine-specific paths, project metadata, and publishing
automation are intentionally outside this public repository.
