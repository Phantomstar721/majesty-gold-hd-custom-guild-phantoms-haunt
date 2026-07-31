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
  phantom_mx_interfacedata.cam
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

## Archive responsibilities

| Archive | Content |
| --- | --- |
| `phantom_maindata.cam` | Building, hero, spell, projectile, overlay, particle, icon, palette, and TILE data |
| `phantom_interfacedata.cam` | Standard interface images and raw textures |
| `phantom_mx_interfacedata.cam` | Northern Expansion interface additions |
| `phantom_textdata.cam` | Menu and description strings |
| `phantom_gpltext.cam` | GPL-facing names and help text |
| `phantom_voices.cam` | Event-specific PCM WAVE payloads |
| `phantom_sounddesc.cam` | Runtime DSND registrations |

XML descriptions provide units, actions, projectiles, overlays, particles, and
sound metadata. GPL provides behavior, decision integration, progression,
equipment, compatibility, and spell mechanics.

## Incremental builds

After a complete validated package exists:

```powershell
.\scripts\Build-CustomGuildPhantomsHaunt.ps1 -GplOnly
.\scripts\Build-CustomGuildPhantomsHaunt.ps1 -AudioOnly
```

`-GplOnly` regenerates and compiles gameplay source without rebuilding art.
`-AudioOnly` consumes the final `assets/audio/phantom-*-game.wav` files and
rebuilds the voice, sound, unit, and manifest components required by the audio
contract. Raw recording projects and clean intermediate masters are not
required or published.

## Validation

`src/validate_phantom_build.py` verifies:

- the exact expected package file set;
- CAM headers, directories, section names, entry ranges, and payload bounds;
- custom WAVE format and DSND phase routing;
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
