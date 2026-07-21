# Majesty Phantom Guild POC

Proof of concept for adding a new buildable guild and a new recruitable hero
through a normal Majesty HD mod package.

The build output defines:

- `Phantom's Guild`, building ID `PHG1`, cost `1`.
- `Phantom`, hero ID `PHM1`, recruit cost `1`.
- New unit-name strings for the building and hero.
- New image IDs copied from Rogue/Rogue Guild descriptors, with placeholder cyan
  Phantom tiles injected into obvious 100x100 slots.
- New sound descriptions and generated placeholder WAVs.
- A GPL data entry for `Phantom` that uses Rogue-like AI behavior through a
  custom `Phantom_tree` wrapper.
- A GPL building data entry for `Phantoms_Guild1`, so peasant construction and
  guild completion scripts know how to initialize it.

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Build-PhantomGuildPoc.ps1
```

## Deploy

Close Majesty before deploying, then run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Deploy-PhantomGuildPoc.ps1
```

Enable `Phantom Guild POC` in the Mods screen, start a quest, and check the
normal castle build menu for `Phantom's Guild`.
