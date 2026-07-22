# Majesty Phantom Guild POC

Proof of concept for adding a new buildable guild and recruitable custom hero to
Majesty Gold HD through a local mod package.

This currently builds:

- `Phantoms Guild`, building ID `PHG1`, castle build-menu cost `1`.
- `Phantom`, hero ID `PHM1`, recruit cost `1`.
- Custom generated Phantom profile art, small hero icon, and small guild icon.
- Generated placeholder voice/soundbite WAVs.
- Wizard-style hero stats and Wizard decision-tree behavior through
  `Phantom_tree`.
- Custom spell descriptions and GPL callbacks:
  - `Ice Lance`: learned at birth, using an energy-blast-style missile/effect.
  - `Frost Armor`: auto-learned at level 3, modeled on Flame Shield.
  - `Blizzard`: auto-learned at level 7 for now, modeled as local AoE damage
    using meteor-storm-style effect art.

The in-map animated hero/building sprites and guild profile panel art are still
cloned from Wizard and Wizard Guild art for stability. The custom equipment
icons (`Phantoms Cowl`, `Dark Staff`) exist in the source art sheet, but they
are not wired into the equipment panel yet.

## Current Limitations

- `Blizzard` is level-gated, not truly learned through the Library yet. The
  stock Library GPL has hard-coded Wizard spell-learning paths, so that needs a
  dedicated pass.
- `Frost Armor` is currently a defensive buff. The intended "negate one attack
  and freeze/slow the attacker" behavior needs deeper combat-hook work.
- The hero/building world sprites and guild profile panel art are not custom
  yet.

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Build-PhantomGuildPoc.ps1
```

Build output goes to:

```text
.\dist\PhantomGuildPoc
```

## Deploy Locally

Close Majesty before deploying, then run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Deploy-PhantomGuildPoc.ps1
```

Enable `Phantom Guild POC` in the Mods screen, start a quest, and check the
normal castle build menu for `Phantoms Guild`.
