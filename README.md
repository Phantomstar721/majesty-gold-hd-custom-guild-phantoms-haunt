# Custom Guild: Phantoms Haunt

Custom Guild: Phantoms Haunt adds a complete recruitable guild and undead hero
class to Majesty Gold HD. It is an additive package for both Original Majesty
and the Northern Expansion, with custom gameplay, art, animation, interface
assets, audio, progression, AI behavior, and quest compatibility.

The playable mod is available as
[Custom Guild: Phantoms Haunt on Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3769947406).

## Phantom and Haunt

The Haunt becomes available at Palace level 2. It recruits Phantoms for 700
gold with a 16-second recruitment time. A new Phantom begins with 1,600 level
XP, 8 Vitality, 8 Strength, 25 Magic Resistance, and 25 Dodge.

Phantoms use Wizard-like spell decisions with a 30% retreat threshold, an
enemy-estimation multiplier of 1.0, and a self-estimation multiplier of 1.2.
Their spell-confidence weights are:

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
- Freezes a unit attacker for three seconds;
- recharges only after the Phantom completes a full rest at the Haunt, an Inn,
  or a Gazebo.

Once learned, the Phantom can cast it on itself when the ward is ready and an
enemy is within 240 units.

### Icy Touch — level 4, rank 3

Icy Touch has a five-second cooldown and a fixed 24-unit melee gate. A
successful cast performs one stock weapon attack, adds 30 spell damage,
refreshes normal Chill for three seconds, and applies Gravechill for eight
seconds.

Gravechill is refreshable but non-stacking:

- Strength −5
- Defence −2
- Parry −2
- Magic Resistance −2

The spell requires a completed level-2 Haunt.

### Call to Grave — level 5, rank 4

Call to Grave is a custom portal return modeled on the Wizard's teleport
behavior. It has a 50,000-unit movement range, a five-second cooldown, and a
500-unit minimum-use distance. It is eligible only when the Phantom's current
task is `go_home` and its destination is its home Haunt, or when `fleeing_in_terror` and forces the flee target to always be the home Haunt.

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
tie. The storm follows that original target visually every 25 milliseconds,
deals damage every 1,600 milliseconds, never retargets, and affects a
175-unit radius:

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
  `ActionRateModifier −10`.
- With a level 3 Haunt, Priestess support selects the nearest Phantom and uses a local follower
  threshold that allows one established follower.
- Ordinary healers, healing potions, and player healing do not heal Phantoms.
  The Priestess's undead-healing exception prioritizes the Priestess herself,
  injured Phantoms, and then other undead.
- Placing a Haunt disables Paladin recruitment. Completing it dismisses living
  Paladins; destroying the final Haunt restores future Paladin recruitment but
  does not recall dismissed Paladins.
- Embassies and Outposts offer Phantoms and omit Paladins while a Haunt exists.

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
| Compatibility | Dataset base `Any`, unique IDs, and guarded stock-compatible hooks |

Technical package names use `CustomGuildPhantomsHaunt`; player-facing text uses
`Custom Guild: Phantoms Haunt`.

### CAM and sprite work

The builder reads stock CAM structures, clones only the required records, and
appends namespaced custom entries. Building and hero frames are fitted to the
native TILE geometry rather than replacing stock assets.

Custom building shadows use Majesty's reserved palette-control indices. Each
construction, active, damaged, collapsed, and destroyed frame receives a
geometry-derived shadow before TILE encoding. See
[Majesty building shadow encoding](docs/majesty-building-shadow-encoding.md).

### GPL and quest compatibility

Generated GPL implements Phantom progression, decisions, equipment, spells,
Haunt upgrades, Priestess interactions, Paladin exclusivity, and guarded
availability handling. The package uses `Dataset base="Any"` so one build can
load in Original Majesty and the Northern Expansion. See
[Quest compatibility](docs/quest-compatibility.md).

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
assets/audio/                    Final game-used voice WAVs
assets/source/buildings/         Haunt source art by building level
assets/source/hero/              Phantom portrait and animation source art
assets/source/interface/         Interface source art
assets/source/references/        Current raster-art references
assets/source/spells/            Spell and effect source art
docs/                            Public technical documentation
scripts/                         Build, review, generation, and audio tools
src/                             CAM builder and package validator
```

Generated packages live under `dist/`, and visual inspection output lives
under `artifacts/`. Neither directory is source-controlled.

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
powershell -ExecutionPolicy Bypass -File .\scripts\Build-CustomGuildPhantomsHaunt.ps1 -AudioOnly
```

`-AudioOnly` packages the checked-in, game-ready WAVs; it does not require the
private recording projects or clean masters.

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
