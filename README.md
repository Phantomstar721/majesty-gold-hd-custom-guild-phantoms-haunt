# Majesty Phantom Guild POC

Proof of concept for adding a new buildable guild and recruitable custom hero to
Majesty Gold HD through a local mod package.

This currently builds:

- `Phantoms Guild`, building ID `MBPhantomGuild`, castle build-menu cost `1`.
- `Phantom`, hero ID `PHM1`, recruit cost `1`.
- Custom generated Phantom profile art, small hero icon, and small guild icon.
- Custom generated Phantom Guild world/building sprite frames, including
  inactive, active, damaged, destroyed, and build-progress variants.
- Custom Phantom starter special items:
  - `Frozen Cowl`, item ID `80`, grants `+1` armor.
  - `Black Icerod`, item ID `81`, grants `+8` weapon damage.
  - Phantom starter items are removed by `Phantom_death` before normal
    gravestone handling, so they do not drop as loot.
- Generated placeholder voice/soundbite WAVs.
- Wizard-style hero stats and Wizard decision-tree behavior through
  `Phantom_tree`.
- A Phantom-only `Ice Lance` spell entry, custom directional projectile art,
  and copied Frost Field hit overlay art.

The in-map animated hero sprite is currently based on the Priestess of Krypta
sprite set with a Phantom recolor.

## Current Status

Confirmed working in-game:

- Private Workshop packaging keeps `Phantoms Guild` available across quest
  reloads and main-menu returns.
- `Phantoms Guild` is buildable from the castle menu and recruits `Phantom`
  heroes.
- Phantom profile art, matching hero-list/guild member icons, custom guild
  build-menu icon, Priestess-based in-map sprite recolor, starter special
  items, and death cleanup all work.
- `Ice Lance` is a Phantom-only custom spell with its own directional
  projectile art and Frost Field hit overlay, without modifying stock Wizard
  spell visuals.
- `Phantoms Guild` now has a generated Phantom-only building sprite set wired
  through appended tile records, without modifying the stock Wizard Guild art.

Next planned work:

- Continue tuning Phantom balance, spell progression, and any additional
  Phantom-only items or spells.

## Custom Special Items

The stable path for giving Phantoms custom special items is the same basic
pattern used by Majesty's quest and Bazaar inventory items:

1. Define a unique numeric item constant in `phantom_gpl()`:

   ```gpl
   expression #Phantom_Item_FrozenCowl 80
   expression #Phantom_Item_BlackIcerod 81
   ```

2. Define a matching inventory item description in `phantom_units_xml()`.
   The important parts are:

   - `ID` should be the item unit/description name, such as `FrozenCowl`.
   - `ImageIDBase` should point to the art entry, such as `PHIC`.
   - Include `IsInventoryItem`.
   - Include an attribute whose ID matches the numeric expression name without
     the `#`, such as `Phantom_Item_FrozenCowl`.

3. Give the item directly to the hero with the numeric constant:

   ```gpl
   $CreateNewInventoryItem(#Phantom_Item_FrozenCowl, thisagent, #Allow_Cloned_Quest_Item);
   ```

4. Apply any stat effect directly after creation, or route it through a helper
   function:

   ```gpl
   $adjustattribute(thisagent, #ATTRIB_Armor_Basic_Damage, 1);
   ```

5. Add the display name to `QITM` in `phantom_gpltext.cam`. `QITM` is an
   indexed STRT table, so the table must physically extend to the item ID. For
   example, item ID `80` needs a real slot 80, not only a string record whose ID
   is 80.

The current generator handles step 5 in `write_gpltext_cam()` by extending
`QITM` through `patch_indexed_strt_strings()`. This was required to avoid
`Unknown Item` in the hero Items panel.

Do not use the earlier birth-thread transfer approach for Phantom starter gear.
Creating string-named custom inventory items through a delayed hero thread was
unstable and caused crashes after Phantom spawn.

Phantom starter gear should also be removed before normal hero death item-drop
logic runs. The current build does that with `Phantom_death`, which deletes only
`#Phantom_Item_FrozenCowl` and `#Phantom_Item_BlackIcerod`, then calls the stock
`gravestone` flow so other legitimate inventory items still behave normally.
Add any future Phantom-only starter or class gear to
`Phantom_remove_starter_items` at the same time it is granted.

## Implementation Notes

### Private Workshop Package

For testing new buildings and heroes, the reliable path is a real private Steam
Workshop item. Loose local mods can appear to work for the first quest after
launch, then lose custom build-menu registrations after returning to the main
menu. The private Workshop package does not have that problem.

The current private item is:

```text
3769947406
```

The normal fast test cycle is:

1. Build into `dist\PhantomGuildPoc`.
2. Deploy directly into Steam's subscribed Workshop folder with
   `scripts\Deploy-PhantomGuildPocRegisteredWorkshop.ps1`.
3. Launch Majesty and enable `Phantom Guild POC` in the mod list.

Keep the SDK/RGSeditor path available for updating the private Workshop item
metadata, but day-to-day local testing should use the registered Workshop deploy
script once the item exists.

### Custom Building Sprite Art

The working custom guild sprite path is:

- Start from the stock `ABX1Rogue Guild1` image record because it has normal
  peasant-built guild state wiring and avoids the Wizard Guild's magical
  construction visuals.
- Generate exact-size RGB replacements for the specific Rogue Guild source
  tiles used by the Phantom Guild clone. The current generator reads from
  `assets\source\phantom-guild-sprite-sheet.png` and writes files named like
  `building_tile_01755.rgb`.
- Append those rendered tiles to `phantom_maindata.cam` under `PHG1Bld####`
  tile entries.
- Remap only the cloned `PHG1Phantom Guild` image entry to the appended tile
  indices.
- Do not overwrite or replace the stock `ABX1Rogue Guild1` image entry, and do
  not replace the stock Rogue Guild tile IDs in-place.

This keeps the original Wizard Guild functioning normally while giving the
Phantom Guild its own inactive, active, damaged, destroyed, and build-progress
world art.

The Phantom Guild should remain a normal peasant-built guild. Its building XML
intentionally matches normal guild placement behavior and does not use
terrain-height modification.

### Custom Icon Art

The current icon build path is generated rather than manually sliced from a
source sheet:

- `scripts\generate_phantom_icons.py` writes the current Phantom hero, guild,
  spell, and equipment icon PNG/RGB files into `dist\temp`.
- `assets\source\phantom-icons-sheet.png` is a current reference/contact sheet
  for humans, not build input.
- The Phantom Guild build-menu icon, hero-list icon, guild member/count icon,
  and Phantom profile portrait are palette-remapped to palette `560` so they
  share the same cyan/blue visual family in-game.
- The cloned Phantom image has an internal hero icon tile copied from the
  Priestess source image. That appended tile must be patched too, or the guild
  count and roster/list icons can appear with different palette tones.

### Custom Spell Art

The working custom directional projectile path is:

- Define the projectile unit as `PHp1` in `phantom_projectiles_xml()`.
- Use `<ImageIDBase value="PHp1"/>` for `ice_lance_missile`.
- Clone the stock Fire Blast moving image structure from
  `WPc2fire_blast_M`, but write it back under the custom image name
  `PHp1fire_blast_M`.
- Do not emit or overwrite the stock `WPc2fire_blast_M` image in the mod CAM.
- Append custom projectile tiles to `phantom_maindata.cam` and remap the cloned
  `IMAG` entry to those appended tile indices.
- Keep stock Fireball directional tile slots `8368-8495` unchanged.

This keeps Wizard spell visuals independent while still reusing the stock
directional projectile image layout that Majesty already knows how to render.

The generated Ice Lance projectile tiles use stock palette `161`. That palette
has cyan, blue, and white entries that render correctly for icy art. Palette
index `255` and magenta-like colors must be avoided when converting RGB pixels,
or visible pixels can become transparent/keyed out in-game.

The copied hit effect uses the Frost Field hit overlay from `DataMX`:

```text
XR30frost_fld_hit
```

It is repackaged as:

```text
PHo3Ice Lance Hit
```

The impact art must be palette-remapped into a palette included by
`phantom_maindata.cam`; the current build remaps it into palette `32`.

### TILE v3 Encoding

Majesty TILE version 3 RLE rows use this segment layout:

```text
u16 x_end
u8  count
u8  flags
u8[count] palette_indices
```

`x_end` is the exclusive end column, not the start column. Decode or encode each
segment at:

```text
[x_end - count, x_end)
```

Treating `x_end` as a start position causes sheared or oversized frames and can
make custom art look corrupted even when the CAM structure is otherwise valid.

### Custom Hero Sprite

The current Phantom in-map sprite is based on the Priestess of Krypta sprite
set, not the Black Phantom monster. The Black Phantom source rendered as a
smoky translucent blob after recoloring. The Priestess sprite gave a more
readable cloaked caster silhouette.

The working path is:

- Clone `AVG1Priestess`.
- Recolor red cloak pixels toward cyan/blue.
- Recolor bright staff pixels toward black.
- Append recolored custom tiles.
- Remap the cloned Phantom `IMAG` entry to the appended tiles.
- Do not alter the stock Priestess image or tiles.

## Current Limitations

- `Frost Armor` and `Blizzard` still need a dedicated stability pass.
- The Phantom Guild is still a proof of concept rather than a balanced finished
  content mod.

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Build-PhantomGuildPoc.ps1
```

Build output goes to:

```text
.\dist\PhantomGuildPoc
```

## Update The Private Workshop Item

The reliable test path is the private Steam Workshop item created through
RGSeditor:

```text
3769947406
```

Loose local deployment under `Documents\My Games\MajestyHD\Mods` can load for a
first quest, but Majesty does not keep these custom building definitions
registered after returning to the main menu. Use the private Workshop item for
normal testing.

After building, close Majesty and sync the package to the SDK upload folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Deploy-PhantomGuildPocSdk.ps1
```

Then open the mod document in RGSeditor:

```text
C:\Program Files (x86)\Steam\steamapps\common\Majesty HD\SDK\Mods\PhantomGuildPoc\PhantomGuildPoc.mmxml
```

Use RGSeditor's Steam Workshop upload window to update the private item. The
`.mswproj` file saved under `assets\source` is Workshop upload metadata, not the
mod document to open directly. If the Workshop upload window opens blank, use
the upload window's `File` menu to open:

```text
C:\Program Files (x86)\Steam\steamapps\common\Majesty HD\SDK\Mods\PhantomGuildPoc\PhantomGuildPoc.mswproj
```

The content path should be:

```text
C:\Program Files (x86)\Steam\steamapps\common\Majesty HD\SDK\Mods\PhantomGuildPoc
```

Once Steam has downloaded or subscribed the private item locally, future builds
can also be copied directly to the registered Workshop content folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Deploy-PhantomGuildPocRegisteredWorkshop.ps1
```

That script intentionally fails if Steam has not created the Workshop content
folder yet.

## Loose Local Deploy

Close Majesty before deploying, then run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Deploy-PhantomGuildPoc.ps1
```

This is useful for checking that files copy cleanly, but repeated in-game quest
testing should use the private Workshop item above.
