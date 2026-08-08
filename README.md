# Custom Guild: Phantoms Haunt

Custom Guild: Phantoms Haunt adds a complete recruitable guild and undead hero
class to Majesty Gold HD. It is an additive package for both Original Majesty
and the Northern Expansion, with custom gameplay, art, animation, interface
assets, audio, progression, AI behavior, and quest compatibility.

The playable mod is available as
[Custom Guild: Phantoms Haunt on Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3769947406).

Note that I do not claim the methods used here are the BEST way to do anything I have done, but they are functional ways! I encourage others to try themselves and share any improvements, corrections, additions, or better strategies.

It is recommended to leverage an AI coding agent to ingest the content in this repo and make it significantly easier to do the CAM unpacking/repacking required for this level of Majesty modding.

## Phantom and Haunt

The Haunt requires a level 2 Palace. Its build-menu availability uses Majesty's
native dependency table so it is hidden at Palace level 1 and appears normally
at level 2. It recruits Phantoms for 700 gold with a 16-second recruitment
time. Like the Temple to Krypta, every Haunt level uses a `2.0` repeat-build
multiplier, so constructing another Haunt increases its price normally. A new
Phantom begins with 1,600 level XP, 8 Vitality, 8 Strength, 25 Magic Resistance,
and 25 Dodge.

Phantoms use a dedicated field-oriented decision tree that prioritizes nearby
threats, rewards, defense, equipment, lairs, enemy buildings, roaming combat,
and exploration before making a reduced 30-percent go-home check. They use a
20-percent retreat threshold, enemy estimation `1.0`, self estimation `1.4`,
Priestess-matched loyalty `30`, and greed `12`. Their spell-confidence weights
are:

| Spell | Confidence |
| --- | ---: |
| Ice Lance | 10 |
| Frost Armor | 10 |
| Icy Touch | 25 |
| Call to Grave | 10 |
| Eternal Soul | 25 |
| Endless Winter | 30 |

The Haunt has three functional levels with unique active, construction,
damaged, destroyed, and collapsed art. Its upgrades unlock later Phantom magic
and add support interactions with Priestesses of Krypta.

Phantoms use the stock `Class 1` walk profile with a mild
`MovementRateModifier −15`. Their AI-facing Speed rating is `1` until Call to
Grave becomes available at level 5, then becomes `5` so threat evaluation
recognizes that they can escape almost any pursuer; this rating change does not
replace their walking animation or movement-rate tuning.

### Equipment

Phantoms begin with equipment built into their progression:

- Frozen Cowl: +2 physical armor.
- Black Icerod: +8 weapon damage, +5 Parry, and +10 base casting range.
- Frost Armor marker: +10 physical armor while the persistent Frost Armor
  protection is active.

The cowl and rod use tier-specific structural and magical names as they improve.
The Phantom's zero-damage base weapon combines with 8 Strength to preserve the
combat-evaluation floor used by Majesty's hero AI.

## Spells and Combat Effects

### Ice Lance — level 1

Ice Lance is a 32-direction custom projectile attack that deals 8 damage. Its
base range is 180 units, increased to 190 by the Black Icerod; enchantment
progression can extend the final range from 190 to 220.

The impact applies a three-second, non-stacking, refreshable Chill:

- `MovementRateModifier +50`
- `ActionRateModifier +500`

Majesty interprets positive rate modifiers as slower movement and actions.
Buildings and lairs still receive the projectile damage and impact effect, but
not Chill.

### Frost Armor — level 3

Frost Armor gives the Phantom a visible, persistent +10 physical-armor item and
a one-hit ward. The ward:

- reduces the first qualifying normal physical or magical hit to zero;
- is consumed on the attack attempt;
- recognizes the attacker's effective weapon or spellcasting range;
- Freezes a unit attacker for three seconds;
- recharges only after the Phantom completes a full rest at the Haunt, an Inn,
  or a Gazebo.

Once learned, the Phantom can cast it on itself when the ward is ready and an
enemy is within 240 units.

### Icy Touch — level 4, rank 3

Icy Touch has a five-second cooldown. It uses a 24-unit melee gate, Majesty's
stock adjacency result, or the target's actual attack range when that target
uses Majesty's direct `basic_attack` action. This supports long-reach and modded
melee units that use the stock action without admitting spell or projectile
ranges or requiring title-specific exceptions. Contact is rechecked when the
attack resolves. A successful cast performs one stock weapon attack, adds 30
spell damage, refreshes normal Chill for three seconds, and applies Gravechill
for eight seconds.

Gravechill is refreshable but non-stacking:

- Strength −5
- Defence −2
- Parry −2
- Magic Resistance −2

The spell requires a completed level-2 Haunt.

### Call to Grave — level 5, rank 4

Call to Grave is a custom portal return modeled on the Wizard's teleport
behavior. It has a 50,000-unit movement range, a five-second cooldown, and a
500-unit minimum-use distance. It recalls a Phantom whose current task is
`go_home` and whose destination is its home Haunt. It can also relay ordinary
building travel through that Haunt when doing so removes at least 500 units
from the remaining walk. The original commerce target, task, and travel state
remain intact, so the Phantom resumes toward the same building after arriving
beside the Haunt; target-building ownership is irrelevant. Commerce eligibility,
including the 500-unit savings test, is decided before casting. The effect
preserves the selected building, and the delayed portal does not repeat the
transient travel-script or savings checks after the Phantom has committed to the
cast. The teleport anchor is captured once from the Phantom's same-player birth
Haunt and never follows stock rehoming. A Phantom born into an Embassy or Outpost
therefore cannot use Call to Grave, and destroying its recorded Haunt disables
the spell even if the hero is later adopted elsewhere. While that Haunt remains
its home, the Phantom targets it while fleeing. Stock-shaped normal and safe
travel hooks give Call to Grave priority over other travel spells, including
Speed Tonics. If the spell is cooling down, travel reevaluates it while the
Phantom continues walking. Delayed portal movement is cancelled if the Phantom,
its recorded Haunt, or its preserved commerce target becomes invalid, dies, or
genuinely changes before the midpoint. Phantoms already alive in a save from
before this anchor was introduced fail closed and must be newly recruited to
receive a recorded Haunt.

### Eternal Soul — level 6, rank 5

Eternal Soul lasts 25 seconds and has a 30-second cooldown. It grants:

- +15 Parry;
- +15 Magic Resistance;
- +30% maximum health while preserving the Phantom's current health
  percentage;
- Empowered Chill with `MovementRateModifier +100` and
  `ActionRateModifier +1000`.

Empowered Chill is the second Chill tier. Normal Chill cannot weaken it or
extend its duration.

### Endless Winter — level 7, rank 7

Endless Winter has a 55-second cooldown and a 21-second lifetime. It selects
the closest eligible enemy, retaining the current combat target when distances
tie. The storm follows that original target's ordinary movement every 25
milliseconds, deals damage every 1,600 milliseconds, never retargets, and
affects a 175-unit radius. Tracking permanently detaches if the target dies,
enters a building, gains a native speed trail such as Winged Feet or Speed
Tonic, or moves farther than the entire 175-unit storm radius in one tracking
sample. The detached storm remains at its last valid location for the rest of
its normal lifetime. Rush unto Death deliberately has no speed trail, so its
mild movement bonus does not detach the storm.

| Distance from center | Damage | Control |
| ---: | ---: | --- |
| 0–24 | 8 | Empowered Chill |
| 25–80 | 6 | Normal Chill |
| 81–175 | 4 | Normal Chill |

The spell requires a completed level-3 Haunt.

## Guild and Faction Interactions

- A level-2 Haunt's `Gravekeeper` doubles Drain Life healing received by allied
  Priestesses for any unit.
- A level-3 Haunt's `Rush unto Death` gives allied Priestesses a persistent mild
  movement and action boost using `MovementRateModifier −22` and
  `ActionRateModifier −10`. It also raises their casting and maximum attack
  ranges from 160 to 220 so they can support a Phantom without advancing ahead
  of its firing line. Rush tracks its own state instead of claiming the native
  Winged Feet state, so actual Winged Feet and Speed Tonics remain available
  and can coexist with the perk.
- With a level 3 Haunt, Priestess support selects the nearest Phantom and uses a
  local follower threshold that allows one established follower. A supporting
  Priestess inherits a followed Phantom's building or lair target only after
  the Phantom actively begins attacking. The aligned 220-unit Rush ranges let
  stock `Attack_Object` engage without pulling her ahead of the Phantom. A
  merely queued raid remains in follow mode.
- Ordinary healers, healing potions, and player healing do not heal Phantoms.
  The Priestess's undead-healing exception prioritizes the Priestess herself,
  injured Phantoms, and then other undead.
- Placing a Haunt disables Paladin recruitment. Completing it dismisses living
  Paladins; destroying the final Haunt restores future Paladin recruitment but
  does not recall dismissed Paladins.
- Embassies and Outposts offer Phantoms and omit Paladins while a Haunt exists.

## Mod Compatibility

Custom Guild: Phantoms Haunt should work alongside most other mods that do not
include custom CAM archives. Its custom units, artwork, sounds, and most other
resources use dedicated `PH` identifiers, and the package does not replace a
standard guild.

### Freestyle limitation

The mod supports normal Original Majesty and Northern Expansion quests, but it
does not support Freestyle. Majesty crashes while starting a Freestyle game
when this mod loads a custom CAM provider. Because the Haunt depends on CAM resources for its art, interface, text, dependency data, and audio, the mod cannot provide a functional Freestyle edition.

### Other CAM Mods

Mods that do include custom CAM files are not automatically incompatible, but
they require more caution. Majesty loads CAM contents into shared global
registries; putting records in differently named CAM files does not isolate
them from records supplied by another mod. Potential conflicts include:

- `DATA/BDEP`: Majesty accepts one complete building-dependency table rather
  than merging multiple tables. Another mod that supplies BDEP requires a
  pair-specific compatibility provider containing the stock table and both
  mods' rules.
- `TILE` and `SPLT`: custom artwork and palettes are addressed by global numeric
  slots. Two mods that independently append art can select overlapping slots,
  causing missing, incorrect, recolored, or corrupted graphics.
- shared text resources such as `UNTN`, `ACTN`, `QITM`, `AITX`, and `HPTX`:
  these are whole tables, so load order can cause one mod's names, item text,
  advisor text, or help text to replace another's additions.
- `SMNU/AP07`: the Haunt uses this executable-supported recruitment-dialog
  slot. Another custom guild using the same slot would directly conflict with
  the Haunt's recruitment panel.

Non-CAM mods can still conflict if they deliberately reuse the same XML IDs or
replace the same stock GPL functions, but ordinary patches with unrelated
identifiers and behavior should coexist normally. There is no speculative
universal compatibility patch: if a specific mod conflict is reported, its CAM
records, identifiers, and effective load order can be examined and a focused
compatibility package made for that pairing.

Tested with the only other CAM mod available currently: MK CAM Content Patch from TheOverloard and they appeared to both work together without issue.

## Technical Architecture

The mod preserves stock data and appends namespaced records wherever Majesty's
runtime permits it.

| Area | Implementation |
| --- | --- |
| Package | One `.mmxml` manifest loading custom CAM archives, XML descriptions, and compiled GPL |
| Rules | Generated GPL sources compiled with the Majesty SDK compiler |
| World art | Custom TILE records appended to cloned IMAG structures |
| Interface | Custom raw-texture and icon CAM entries |
| Text | Dedicated STRT and SMNU additions |
| Audio | PCM WAVE records with stock-shaped DSND descriptors |
| Compatibility | Dataset base `Any`, native BDEP Palace gating, unique IDs, and guarded stock-compatible hooks |

Technical package names use `CustomGuildPhantomsHaunt`; player-facing text uses
`Custom Guild: Phantoms Haunt`.

For the detailed BDEP merge procedure, see
[Packaging architecture](docs/packaging.md#bdep-mod-compatibility).

### CAM and sprite work

The builder reads stock CAM structures, clones only the required records, and
appends namespaced custom entries. Building and hero frames are fitted to the
native TILE geometry rather than replacing stock assets.

Majesty addresses tiles by their position within a CAM's TILE section, so an
archive that appends custom tiles must still contain an entry for every slot
below the highest index it uses. Those unreferenced slots are written as
zero-length entries; the engine then falls back to the stock archive for them.
The package therefore contains only its own artwork, and none of Majesty's.

Custom building shadows use Majesty's reserved palette-control indices. Each
construction, active, damaged, collapsed, and destroyed frame receives a
geometry-derived shadow before TILE encoding. See
[Majesty building shadow encoding](docs/majesty-building-shadow-encoding.md).

### GPL and quest compatibility

Generated GPL implements Phantom progression, decisions, equipment, spells,
Haunt upgrades, Priestess interactions, Paladin exclusivity, and guarded quest
handling. Palace availability is data-driven through the stock `BDEP` table,
not a Palace watcher or construction callback. The package uses
`Dataset base="Any"` so one build can load in Original Majesty and the Northern
Expansion. See
[Quest compatibility](docs/quest-compatibility.md).

Dark Forest integrates the Haunt directly into the quest's stock guild lock and
Fervus-discovery unlock lists. That progression is confirmed in game without a
watcher or custom restoration path.

### Voice pipeline

The public repository contains only the 13 final game-used voice WAVs. They are
mono, 22,050 Hz, 16-bit PCM files produced from clean takes with the
reproducible revenant treatment in `scripts/process_phantom_voice.py`. Raw
Audacity projects and intermediate masters are deliberately not published.

The package uses:

- a stock-shaped multi-event `Phantom_Voice` descriptor;
- separate WAVs for recruitment, decisions, idling, hostile sightings, combat,
  fleeing, rewards, items, casting, leveling, death, and the Easter egg;
- stock-style random bark cadence rather than forced playback on every event.

See [Phantom voice production](docs/phantom-voice-line-plan.md) for the event
map, processing method, and game-format contract.

## Repository Layout

```text
docs/                            Public technical documentation
scripts/                         Build, review, generation, and audio tools
scripts/majesty_imag.py          IMAG and v1 TILE helpers for the review scripts
src/                             CAM builder and package validator
src/gpl/                         Static GPL source used by the builder
tests/                           Unit tests for the builder's pure functions
```

This repository stands alone. Nothing in it imports from another repository or
expects a sibling checkout on disk, and the test suite fails if that ever
changes.

Generated packages live under `dist/`, and visual inspection output lives
under `artifacts/`. Neither directory is source-controlled.

### Art and audio are not distributed

The `assets/` folder holds the original artwork, voice recordings, and Steam
Workshop images for this mod. It is deliberately not source-controlled, so a
clone of this repository does not include it.

Every image and audio path in the build and deployment scripts is an
overridable parameter, so the tooling works against your own files. Point the
parameters at your art, for example:

```powershell
.\scripts\Build-CustomGuildPhantomsHaunt.ps1 -PortraitImage .\my-art\portrait.png
```

Run `Get-Help .\scripts\Build-CustomGuildPhantomsHaunt.ps1 -Detailed` for the
full parameter list. The code, documentation, and tests in this repository are
complete and self-contained; only the artwork is withheld.

## Building

Requirements:

- Majesty Gold HD installed through Steam;
- the Majesty SDK and `Gplbcc.exe`;
- the workspace Python environment at `..\.tools\python.cmd`;
- Python dependencies used by the art tools, including Pillow.

Run a complete build:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Build-CustomGuildPhantomsHaunt.ps1
```

The validated package is written to `dist\CustomGuildPhantomsHaunt`.

After one complete build exists, gameplay-only and audio-only changes can use
the faster incremental paths:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Build-CustomGuildPhantomsHaunt.ps1 -GplOnly
powershell -ExecutionPolicy Bypass -File .\scripts\Build-CustomGuildPhantomsHaunt.ps1 -GameplayOnly
powershell -ExecutionPolicy Bypass -File .\scripts\Build-CustomGuildPhantomsHaunt.ps1 -TextOnly
powershell -ExecutionPolicy Bypass -File .\scripts\Build-CustomGuildPhantomsHaunt.ps1 -InterfaceOnly
powershell -ExecutionPolicy Bypass -File .\scripts\Build-CustomGuildPhantomsHaunt.ps1 -AudioOnly
powershell -ExecutionPolicy Bypass -File .\scripts\Build-CustomGuildPhantomsHaunt.ps1 -AudioOnly -GplOnly
```

`-GplOnly` recompiles behavior, `-GameplayOnly` regenerates unit XML and GPL,
`-TextOnly` refreshes text CAMs, and `-InterfaceOnly` rebuilds only the custom
recruitment-panel CAM. `-AudioOnly` packages the checked-in,
game-ready WAVs without requiring private recording projects or clean masters.
Combine `-AudioOnly -GplOnly` for an atomic runtime update that spans sound
registration and GPL without rebuilding art.

### Gameplay source

The static GPL body lives in `src/gpl/phantom.gpl` as ordinary GPL rather than
inside a Python string, so it can be edited with syntax highlighting and gives
readable diffs. The builder prepends the generated `expression` constants and
appends the quest rule overrides it extracts from the SDK.

### Tests

The builder's pure functions have unit tests that need neither the game nor the
SDK:

```powershell
..\.tools\python.cmd -m unittest discover -s tests
powershell -ExecutionPolicy Bypass -File .\tests\Test-HauntDeployment.ps1
```

They cover TILE encoding and decoding, CAM container round-trips, string-table
patching, tile reduction, palette selection, the generated XML, and safe,
content-exact local deployment. The deployment test uses disposable directories
and does not touch the installed mod. Package correctness is still checked by
the full validation that runs after every build.

Every build ends with structural and semantic validation of the manifest, XML
descriptions, CAM directories and payloads, WAVE formats, DSND routing, GPL
source contracts, compiled bytecode, custom IDs, tile mappings, palette
controls, and quest compatibility requirements.

During development, a validated package can be copied directly into the
content directory of a locally subscribed Workshop item and tested without
round-tripping through RGSeditor. RGSeditor is needed when the item itself is
published or updated, not for each local development build. No local content
path or publishing metadata is part of this repository.

The complete package structure is documented in
[Packaging architecture](docs/packaging.md).
