# Majesty Phantoms Haunt POC

Proof of concept for adding a new buildable guild and recruitable custom hero to
Majesty Gold HD through a local mod package.

This currently builds:

- `Phantoms Haunt`, building ID `MBPhantomGuild`, castle build-menu cost `1`.
- `Phantom`, hero ID `PHM1`, recruit cost `1`.
- Custom generated Phantom profile art, small hero icon, and small guild icon.
- A custom blue Phantoms Haunt dialog look built by borrowing the stock Elf
  recruit dialog.
- Custom generated Phantoms Haunt world/building sprite frames, including
  inactive, active, damaged, destroyed, and build-progress variants.
- Custom Phantom starter special items:
  - `Frozen Cowl`, item ID `80`, grants `+2` physical armor using the same
    `AdjustAttribute(Armor_Basic_Damage)` path as Majesty's Ring of Protection.
  - `Black Icerod`, item ID `81`, displays and grants `+5 parry` through the
    same `MagicalAdjustAttribute(Parry)` path as Majesty's Ring of Protection.
  - Phantom starter items are removed by `Phantom_death` before normal
    gravestone handling, and are marked non-droppable so leaving the realm
    through the palace deletes them instead of spawning them as ground loot.
- Phantom baseline balance: `8` Vitality, `8` Strength, `25` Magic Resistance,
  `25` Dodge, and `180` conceptual base casting range. Artifice remains `8`;
  Majesty uses it for equipment-shopping choices, stealing checks, and
  Gambling Hall fallback rolls, not spell damage, casting speed, range, or
  cooldown.
- Generated placeholder voice/soundbite WAVs.
- Wizard-style hero stats and Wizard decision-tree behavior through
  `Phantom_tree`.
- A Phantom-only `Ice Lance` spell entry, generated-source directional
  projectile and icon art, a copied Frost Field hit overlay, and a timed Chill
  debuff.
- A level-3 `Frost Armor` spell with a persistent crystal ward, one-hit damage
  negation, a three-second retaliatory Freeze, and rest-to-recharge behavior.

The in-map animated hero sprite is currently based on the Priestess of Krypta
sprite set with a Phantom recolor.

## Current Status

Confirmed working in-game:

- Private Workshop packaging keeps `Phantoms Haunt` available across quest
  reloads and main-menu returns.
- `Phantoms Haunt` is buildable from the castle menu and recruits `Phantom`
  heroes.
- Phantom profile art, matching hero-list/guild member icons, custom guild
  build-menu icon, custom dialog panel art, generated in-map sprite art,
  starter special items, and death cleanup all work.
- `Ice Lance` is a Phantom-only custom spell with its own directional
  projectile art and Frost Field hit overlay, without modifying stock Wizard
  spell visuals.
- `Phantoms Haunt` now has a generated Phantom-only building sprite set wired
  through appended tile records, without modifying the stock Wizard Guild art.
- Occupied Haunts use an eight-frame full-building active animation so
  the cyan windows and arcane highlights pulse while heroes are inside.
- `A Deal with the Demon` is patched for testing so it starts with both a
  Phantoms Haunt and an Elven Bungalow.

Next planned work:

- Restore or reattach proper Phantom hero sprite shadows.
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
   $AdjustAttribute (thisagent, #ATTRIB_Armor_Basic_Damage, 2);
   ```

   Inventory entries are only IDs while held; the item XML does not
   automatically add its stats to the owner. The current starter-item grant
   therefore applies the two bonuses explicitly:

   ```gpl
   $AdjustAttribute (thisagent, #ATTRIB_Armor_Basic_Damage, 2);
   $MagicalAdjustAttribute (thisagent, #ATTRIB_Parry, 5);
   ```

   Frozen Cowl uses the ordinary armor adjustment from the stock Ring of
   Protection path. Black Icerod uses that ring's magical Parry-adjustment
   path. Their `QITM` strings display `+2 armor` and `+5 parry`; Majesty does
   not generate those descriptions from the GPL changes, so validation must
   keep the displayed text and mechanical values synchronized.

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

Class gear that must never become loot also needs
`<Attribute ID="CanDropItem" Value="0"/>` in its unit description. Majesty's
stock `flee_map` path calls `Hero_Drop_Quest_Items` after a departing hero
enters the palace. `CanDropItem=1` makes that function delete the inventory
entry and spawn its world-item agent beside the palace; `0` makes it delete the
entry without spawning anything. This covers palace realm exit and other stock
inventory-drain paths without replacing the global `flee_map` routine. Keep the
explicit `Phantom_death` cleanup as a defensive, class-scoped death path.

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
3. Launch Majesty and enable `Phantoms Haunt POC` in the mod list.

Keep the SDK/RGSeditor path available for updating the private Workshop item
metadata, but day-to-day local testing should use the registered Workshop deploy
script once the item exists.

### Guild Dialog Path

Majesty's recruit-panel behavior is keyed in `MajestyHD.exe` by stock AP dialog
IDs. Mod files can replace menu data, strings, art, units, actions, and GPL, but
they do not appear to register a brand-new recruiting AP handler.

The current Workshop-only compromise is to borrow the stock Elf recruit dialog:

```text
AP07
```

The Phantoms Haunt uses `AP07` because that ID already has the right recruit
behavior. The mod replaces the AP07 strings and redirects its raw texture
reference from `INTIraw textures` to `PHTIraw textures`, which gives the Phantom
Guild the blue custom panel background. The AP07 menu also references the Elf
guild member/count icon through image token `AVd1`, so the generator rewrites:

```text
AVd1 -> PHM1
INTI -> PHTI
```

This makes the Phantoms Haunt use the Phantom icon and custom background. Because
AP07 is shared, the stock Elven Bungalow also inherits those AP07 visual
overrides while this mod is active.

Other stock recruit guild AP IDs can be used the same way, but the same rule
applies: the chosen stock guild's panel is the thing being borrowed. Attempts to
create unrelated custom AP IDs such as unused-looking alphanumeric IDs either
fell back to non-recruit UI behavior, collided with unrelated stock panels, or
crashed when selected. That strongly suggests the recruit UI class dispatch is
not data-driven by the mod CAM files alone.

A truly isolated Phantom-only recruit panel likely needs an external exe patch
or hook so Majesty dispatches a new AP ID to a recruit-capable panel class.

### Guild Panel Background Art

The guild panel background was not controlled by the obvious-looking
`INBgbuilding dialog` image record. Replacing or cloning that record either did
nothing useful, painted only frame fragments, or caused `Attempt to do 816 blit
without a palette` crashes when the panel opened.

The working background path is:

- Clone the stock recruit dialog `SMNU` entry from `AP07`.
- Rewrite its raw texture image token from `INTI` to `PHTI`.
- Clone the stock `INTIraw textures` image record as `PHTIraw textures`.
- In the cloned `PHTI` image, remap raw-texture backing tile `466` to a newly
  appended tile.
- Encode the appended tile from the generated Phantom panel source art.
- Emit only `PHTIraw textures` and the appended backing tile in
  `phantom_interfacedata.cam`; leave the stock `INTI` and `INBg` records alone.

The generated source panel is:

```text
assets\source\phantom-interface-panel-source.png
```

The build script converts it to raw RGB at `200x245`, matching the tile backing
size the current encoder expects. `assets\source\phantom-interface-panel-202x245.png`
is kept as a human reference for the slightly wider panel framing we observed
during testing, but the build path uses the resampled raw RGB output.

The useful implementation anchors are:

```text
BUILDING_DIALOG_BACKING_TILE = 466
RAW_TEXTURES_IMAGE = INTIraw textures
PHANTOM_RAW_TEXTURES_IMAGE = PHTIraw textures
```

### Custom Building Sprite Art

The working custom guild sprite path is:

- Start from the stock `ABQ1Temple, Fervus1` image record. It has normal
  peasant-built construction behavior and a scaffold footprint that fits the
  large Phantoms Haunt art better than the Rogue Guild source did.
- Do not start from the Wizard Guild image record for this building. Its
  construction state has special magical self-build visuals that look wrong
  when reused for the Phantoms Haunt, even though the Wizard active-state pulse
  behavior was useful as a reference.
- Generate exact-size PNG/RGB replacements for the specific Fervus source tiles
  used by the Phantoms Haunt clone. The current generator reads from
  `assets\source\phantom-guild-sprite-sheet-smooth.png` and writes files named
  like `building_tile_01505.png`.
- Generate the three construction states from
  `assets\source\phantom-guild-construction-proof-v1.png`. This is a
  high-resolution generated interpretation of normal construction stages,
  downscaled into the stock Fervus build-state tile sizes.
- Generate distinct destruction transitions from
  `assets\source\phantom-guild-damaged-b-sample-v1.png` and
  `assets\source\phantom-guild-collapsed-intermediate-sample-v1.png`.
  The resulting Fervus-compatible progression is damaged A (`1529`), damaged B
  (`1530`), collapsed intermediate (`1531`), and final rubble (`1508`).
- Process every destruction source independently through palette grading and
  geometry-derived upper-left shadow generation. Do not reuse the full-building
  shadow mask on a lower collapse state.
- Append those rendered tiles to `phantom_maindata.cam` under `PHG1Bld####`
  tile entries.
- Remap only the cloned `PHG1Phantom Guild` image entry to the appended tile
  indices.
- Do not overwrite or replace the stock `ABQ1Temple, Fervus1` image entry, and
  do not replace the stock Fervus tile IDs in-place.

This keeps the original Wizard Guild functioning normally while giving the
Phantoms Haunt its own inactive, active, damaged, destroyed, and build-progress
world art.

The Phantoms Haunt should remain a normal peasant-built guild. Its building XML
intentionally matches normal guild placement behavior and does not use
terrain-height modification.

#### Occupied / Active Building Animation

Fervus has a separate small active overlay state (`Active-256`) for its cave
fire layer. Blanking those tiles removes the stock overlay, but replacing them
with hand-painted low-resolution art looks bad and is not the path to use.

The better working path is to mimic the Wizard Guild's main `Active` state
behavior while keeping the Fervus construction scaffold:

- `scripts\generate_phantom_building_sprites.py` emits
  `building_active_frame_00.png` through `building_active_frame_07.png`.
- These are full-building frames generated from the same smooth Phantoms Haunt
  source art, with only the cyan highlight intensity pulsed.
- The generator also projects each clean building silhouette down and left,
  painting a three-band cast shadow with Majesty's reserved palette indices
  `248`, `249`, and `250`, with transition key `247` only where shadow meets
  the outer building edge. The clean source sheets remain unchanged; the
  magenta shadow-key pixels exist only in generated `dist\temp` frames and the
  encoded custom TILE records.
- Surface lighting and self-shadowing remain authored into the ordinary
  building artwork. Do not project the ground-shadow mask across opaque
  building pixels; it is not a valid self-shadow mask for isometric geometry.
  Generate each construction state from its own visible silhouette so an
  unfinished foundation does not cast the completed tower's shadow.
- The custom world frames use registered palette `560`. Do not append a new
  SPLT index for shadow colors: Majesty does not extend its runtime palette
  registry from a mod CAM and will fail with an
  `Attempt to do 816 blit without a palette` error.
- `src\build_phantom_guild.py` appends those frames as `PHG1Act00` through
  `PHG1Act07`.
- The cloned `PHG1Phantom Guild` image record has only its stock `Active`
  state (`set ID 192`) rewritten to point at those appended active-frame tiles.
- The stock Fervus and Wizard Guild image records are left untouched.

This gave the desired occupied-building pulse without reintroducing Wizard
Guild construction effects or breaking normal peasant construction.

Majesty does not derive these shadows from sprite alpha at runtime. Stock
building TILE records contain authored pixels in reserved palette indices
`247-250`, shown as red/magenta by raw asset viewers and interpreted as
shadow/blend keys by the game. Clean extractor previews intentionally hide
those indices, so replacement art must regenerate or explicitly preserve them.

The palette keys alone are not sufficient. Majesty applies their special blit
behavior at the TILE v3 RLE-segment level. A shadow-control run and ordinary
building artwork must be encoded as separate, immediately touching segments;
combining them makes the engine consume building pixels in horizontal bands.
See [Majesty Building Shadow Encoding](docs/majesty-building-shadow-encoding.md)
before creating or changing custom building sprites.

### Custom Icon Art

The current icon build path is generated rather than manually sliced from a
source sheet:

- `scripts\generate_phantom_icons.py` writes the current Phantom hero, guild,
  spell, and equipment icon PNG/RGB files into `dist\temp`.
- `assets\source\phantom-icons-sheet.png` is a current reference/contact sheet
  for humans, not build input.
- The Phantoms Haunt build-menu icon, hero-list icon, guild member/count icon,
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

The projectile and both Ice Lance icons now derive from the generated,
transparent high-resolution source:

```text
assets\source\ice-lance-projectile-source-v2.png
```

The CAM builder crops the source silhouette, rotates it into all 32 inherited
Fire Blast directions, downscales it into each native projectile TILE, and
nudges the visible art slightly forward along the travel vector so the first
frame reads ahead of the caster anchor. `scripts\create_ice_lance_review.py`
decodes all 32 packaged directions into the persistent
`artifacts\reviews\ice-lance-directional-packaged-review.png` contact sheet.
The approved `v2` source compresses the original value range into neutral
arctic blues and pale cyan-white highlights; `v1` remains beside it as the
higher-contrast rollback source.

The generated Ice Lance projectile tiles use stock palette `161`. That palette
has cyan, blue, and white entries that render correctly for icy art. Palette
index `255` and magenta-like colors must be avoided when converting RGB pixels,
or visible pixels can become transparent/keyed out in-game.

Ice Lance deals `8` damage, compared with stock Energy Blast's `10`. The
Phantom's base casting range is `180`, below the Wizard's `240`. Majesty stores
casting range on the hero rather than the individual spell, so this technically
applies to the Phantom's complete spell kit; Frost Armor is self-targeted and
Blizzard is caster-centered, making Ice Lance the only current spell materially
affected. Custom special items are stored as inventory IDs and do not
automatically transfer XML attributes to their owner. Frozen Cowl therefore
uses the stock Ring-of-Protection pattern to apply `+2` basic-damage armor when
granted. The Cowl passed combat, treasure, and gold tests independently.
Initial Black Icerod Parry tests appeared to implicate both `AdjustAttribute`
and `MagicalAdjustAttribute`, including a version deferred until after birth.
The actual common failure was removing the old `+8` weapon damage while the
Phantom's base weapon damage was `0`. Stock `target_eval` divides enemy HP by
`hero_damage`. That helper totals basic, structural, and magical weapon damage,
then adds integer `Strength / strength_div`. For the original Strength-2
caster, every term was `0`, causing the crash on entering combat. Majesty's
`strength_div` is `8`, so the Phantom now uses Strength `8` with base weapon
damage `0`. Integer division supplies the required AI-evaluation floor of `1`
without a hidden weapon stat. The separate XML `Attack` value remains `30`;
zero `WeaponBasicDamage` means the rod is not secretly adding physical damage,
not that every engine attack-related field is zero. Ice Lance damage remains
its independent fixed value of `8`, and the Icerod itself grants only `+5`
Parry. Package validation requires the safe Strength threshold and rejects the
old rod weapon-damage bonus.

On a non-building target, `Ice_Lance_Hit` creates the original invisible
`ice_lance_chill_icon` timer for three seconds and adds `50` to
`ATTRIB_MovementRateModifier` and `500` to `ATTRIB_ActionRateModifier`.
These engine modifiers use different scales rather than percentages: the
movement value provides a gentler slow, while the larger action value follows
stock Majesty slow effects closely enough to make action delay observable.
`Ice_Lance_Chill_End` reverses both values.
On a repeated hit, the existing effector is deleted so its callback first
reverses the old modifiers, then Chill is reapplied with a fresh three-second
timer. This refreshes the duration without stacking the penalty. The mechanic
otherwise retains the first working Chill implementation recovered from the
original Codex session transcript.

The mechanical timer remains an invisible `PHo4` overlay and is the sole owner
of the cleanup callback. A separate visual-only `PHo5` overlay displays the
custom cyan snowflake through the packaged `PHo4chill_icon` image. The image
uses the larger stock animated-status canvas and contains 29 distinct frames:
the snowflake spins around its vertical axis through horizontal perspective
compression, with a subtle scale pulse and vertical bob. A cyan glint sweeps
across its face to make the turn readable even though the snowflake itself is
symmetrical. Its layered dark-blue, bright-cyan, and pale-cyan strokes are
tuned for the stronger size and vibrancy of Majesty's Wither-style status
effects. Every hit refreshes both overlays independently, so the symbol tracks
the three-second Chill duration without participating in modifier application
or cleanup.

### Chill and status-effect implementation notes

Majesty's rate modifiers are fixed engine offsets, not percentage inputs.
`ATTRIB_MovementRateModifier` and `ATTRIB_ActionRateModifier` also use different
numeric scales; assigning the same number to both does not produce the same
slow and can make it appear that both modifiers affected movement. The working
Ice Lance values are therefore intentionally different (`+50` movement and
`+500` action). Positive values slow the corresponding rate, and the cleanup
callback applies the exact negatives. Because units have different base
movement classes and action timings, one fixed modifier can produce different
effective percentage changes between units. No dependable GPL path was found
for converting the live speed/action class into an exact percentage reduction,
and stock effects such as Medusa-style slows likewise use fixed modifiers.
Treat this as a mild Chill, not a guaranteed numeric-percent debuff.

The safe non-stacking refresh sequence is:

1. If the mechanical timer effector exists, delete it. Deletion runs its end
   callback and reverses the previous modifiers.
2. Apply the movement and action modifiers once.
3. Recreate the mechanical effector for the full duration.
4. Independently delete and recreate the visual effector for the same duration.

Do not apply another set of modifiers before deleting the old mechanical
effector. Do not give the visual overlay a cleanup callback: modifier ownership
must stay centralized in one timer so multiple Phantoms refresh rather than
stack. The three-second duration lives on the `ice_lance` action as
`EffectorDuration`; both effectors read it through `$GetSpellAttribute`, so the
timer and icon cannot silently drift apart.

For floating buff/debuff symbols, cloning an existing animated status-image
layout is more reliable than inventing overlay geometry. Chill clones the
29-frame `XR25plague_icon` image record, appends custom remapped TILE records,
and keeps the template's canvas, hotspot, and timing. The mechanical `PHo4`
overlay uses `NotVisibleInISOView`; visible `PHo5` points at the generated
`PHo4chill_icon` image. The snowflake needs stronger scale, line weight, and
cyan contrast than an isolated review suggests because in-game terrain and
sprites reduce legibility. Its approved animation simulates rotation around
the vertical axis by compressing the horizontal dimension, plus a small bob,
pulse, and sweeping glint. Rotating the entire snowflake in the image plane
reads as a wheel and was rejected.

Impact visuals and debuffs should remain separate. Ice Lance creates its native
hit overlay before the building/lair guard, so every surviving target shows the
six-frame impact, while only units continue into Chill. Attaching the overlay
to a large building uses the building's engine anchor and can place late frames
near its center, but it is the stable native behavior. A coordinate-spawned
Character is unsafe because it becomes a real gameplay unit and can leave
placeholder dots or disrupt AI. A coordinate-spawned particle system compiled
but did not render the intended animated overlay in game, so that path was also
removed.

Buildings and lairs take Ice Lance damage and receive the same native animated
Frost Field hit overlay as units, but do not receive Chill. Majesty attaches
that overlay to the target's engine anchor, matching the standard projectile
impact path even though the final frames may sit nearer a large building's
center. Coordinate-spawned characters and particle-system impact anchors are
not used; those experiments either disrupted gameplay logic or failed to
render the intended animation.

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

### Frost Armor

Phantoms automatically learn Frost Armor at level 3. `Phantom_tree` checks for
enemies within the Phantom's fixed `240` sight radius before entering the
normal Wizard combat tree and casts the ward on itself whenever it is learned,
unspent, and inactive. The fixed radius avoids passing a nested
`GetAttribute` call into Majesty's runtime-sensitive `compile_enemies` native.
The trigger intentionally uses combat awareness rather than Ice Lance's
shorter casting range because Frost Armor is self-targeted. Auto-cast applies
the armor directly and plays the stock `Basic_Cast` presentation action,
avoiding the spell scheduler's silent availability rejection. The
Phantom watcher also recognizes `Attack_object` in either `ActiveScript` or
`BackScript`, covering combat travel that began outside the decision tree's
immediate proximity check. Ready, active, and spent are stored as `0`, `1`, and
`2` in the Phantom's otherwise unused
`Reborn_Counter` hero field. Stock code only changes that field for Healers, so
it gives the custom hero durable per-agent state without tying spell selection
to an overlay timer. The field is reset during Phantom birth and death; a
future Phantom rebirth mechanic must migrate Frost Armor to a different field.

The rotating octahedral crystal is visual-only. It receives the longest
duration used by a stock action (`180000` milliseconds), and the Phantom-owned
watcher recreates it if that animation expires while state is still active.
Majesty does not treat effector duration `0` as infinite: it lets an overlay
expire with its natural animation. Visual renewal therefore never decides
whether the armor can be cast and never owns the armor-stat cleanup.

Frost Armor adds `10000` basic-damage armor while active, making the first
ordinary weapon attack deal zero damage. The Phantom's existing `Hostiles`
list acts as the local attack-attempt signal: the ward clears that list when
cast, then its recurring watcher consumes the ward when the first valid
attacker appears. Majesty's `react(attacker, target)` adds the attacker just
before the hit roll, but other AI paths can leave broader combat relationships
in the same list. The watcher therefore also requires that the reported
hostile currently targets the Phantom and is within its own maximum attack
range (plus a small 24-unit movement/geometry tolerance). Nonqualifying entries
are cleared so a later real attack can report itself again. This prevents the
Phantom's first attack against a distant melee target from consuming the ward.
The local filter avoids modifying global attack/damage functions and requires
no changes to enemy definitions. It intentionally reacts to the first
qualified attack attempt, even when the engine's hit roll would otherwise
miss.

Unit attackers are Frozen for three seconds through Majesty's native
`HasEffectPetrify`, `Freeze_Unit`, `GetProperUnitArt`, and `UnFreeze_Unit`
path. The effect stops movement and actions rather than approximating another
rate modifier. An attacker that is already petrified by some other effect is
left alone. Buildings and lairs still consume the ward and have their damage
absorbed, but are not Frozen. Each size-specific casing is also explicitly
given the same three-second lifetime as the controlling frozen timer; duration
`0` is not used for persistent spell visuals.

The spent state is the durable state value `2`. Entering a home building
replaces the stock rest activity with a thin wrapper around
`Rest_At_Guild`; once the Phantom reaches full health, the wrapper deletes the
spent marker. Inns and Gazebos share Majesty's `rest_at_inn` full-heal path, so
the Phantom-owned watcher recognizes the complete rest window from
`rest_at_inn` through `Done_resting_inn`; guild rest is similarly recognized
from `Rest_at_guild` through `Done_resting_guild`. These stock activities
guarantee a full heal. Using the entire activity window avoids missing the
brief done-state transition while `InsideBuilding` still prevents ordinary
shop visits from recharging the armor. The Haunt wrapper also clears spent
state unconditionally after calling the stock full-heal function. Merely
losing the active ward or leaving combat does not recharge it.

Frost Armor's generated art sources are:

```text
assets\source\frost-armor-crystal-source-v1.png
assets\source\frost-armor-frozen-casing-source-v3.png
```

Both sources are packaged through palette `161` into 29-frame animations. The
crystal simulates rotation around its vertical axis with horizontal
compression, face reversal, a subtle pulse, and a small hover. The casing
uses small (`58x72`), medium (`82x104`), and large (`116x144`) native TILE
canvases chosen from the attacker's maximum HP, so the visual scales without
editing every unit. The casing uses a tall pointed crystal silhouette with a
mostly transparent interior and sparse diagonal fracture lines, avoiding both
the original archway and the later rectangular dithered block. The visible
casing lasts `2700` milliseconds while the controlling Frozen timer remains
exactly `3000`, ensuring the enemy cannot resume moving before the ice clears.

Run `scripts\create_frost_armor_review.py` after a build to decode the actual
packaged tiles into:

```text
artifacts\reviews\frost-armor-packaged-review.png
```

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

Shadowed building TILEs have an additional segment-boundary requirement; see
[Majesty Building Shadow Encoding](docs/majesty-building-shadow-encoding.md).

### Custom Hero Sprite

The Phantom in-map sprite uses `AVG1Priestess` as the animation and image-record
scaffold, but the visible sprite art should come from generated high-resolution
source art. Direct low-resolution pixel drawing produced poor results and should
not be used for future character, monster, building, or projectile sprite work.

The working art path is:

- Generate a high-resolution source sprite sheet first.
- Chroma-key or otherwise isolate each frame from the source sheet.
- Downscale each source frame into the exact dimensions of the stock tile it
  replaces, keeping the whole sprite in frame.
- Convert transparent pixels to black before TILE v3 encoding, because black is
  treated as transparent by the current RGB-to-tile conversion path.
- Append generated custom tiles under new names.
- Remap only the cloned Phantom `IMAG` entry to the appended tiles.
- Do not alter the stock Priestess image or tiles.

Current build input:

```text
assets\source\phantom-guild-sprite-sheet-smooth.png
assets\source\phantom-guild-construction-proof-v1.png
assets\source\phantom-hero-major-actions-preview-v3.png
assets\source\phantom-gravestone-source.png
assets\source\phantom-interface-panel-source.png
```

`scripts\generate_phantom_hero_sprites.py` slices the hero source sheet, uses
the gravestone source for the late death and persistent dead/grave tiles, and
writes files named like `hero_tile_04650.png` into `dist\temp\hero_sprites`.
The CAM builder then scales those PNGs into the exact original tile dimensions
before appending them to `phantom_maindata.cam`.

The first generated sheet only has one facing, so the generator mirrors that
source for rough opposite directions. A final-quality hero sprite should use a
true directional source sheet, but the generated-source/downscale path is the
right workflow.

Stock hero TILEs carry engine shadow controls at reserved palette indices
247-250. The Phantom does not reuse the Priestess's walking foot-and-robe
silhouettes. Instead, the builder derives a dark-body mask from each rendered
direction's neutral hover frame, excludes bright cyan/white spell effects,
flattens and projects that canonical body mask toward the upper-left, and
offsets the lowest projected pixels from the robe so the shadow remains
detached and the hero reads as floating. Reusing the directional hover caster
keeps attacks, spells, and weapons from changing or deleting the ground
silhouette. The projection length is deliberately constrained to fit the
narrowest native Priestess direction TILE: the visible hero remains enlarged,
while the flattened shadow caster is scaled independently to preserve the
stock canvas margin rather than clipping the projected silhouette at its edge.
It fades through the shared dissolve sequence and emits body/control runs as
separate RLE segments. The purple colors visible in raw review PNGs are
control-key visualization, not painted ground shadow.

After body clearance, keep only the largest connected shadow-control component.
Projection quantization can otherwise strand the hood/head as a small
upper-left island that the engine renders as an implausible detached shadow.

The production hero source now uses six direction slots. Directions 2-5 have
dedicated approved/generated 3x2 major-action sheets; directions 6-7 are exact
opposite-side mirrors of directions 4-3 for costume consistency. The generator
maps them into the real Priestess animation topology: seven floating movement
frames, four-stage attacks, four-stage casts, three-stage specials,
direction-specific death starts, and the shared eight-frame dissolve.

Majesty's populated unit slots rotate from back/north to front/south rather
than following art-generation order: slot 2 is back/north, 3 rear-side,
4 front-side, 5 front/south, 6 opposite front-side, and 7 opposite rear-side.
The generator therefore applies the explicit source permutation
`back, rear-side, front-side, front, mirrored front-side, mirrored rear-side`.

Walk directions occupy eight-TILE blocks beginning at tile 4586. The first
TILE in each block is a header/base pose that the engine periodically displays;
the following seven are the normal Walk sequence. Direction assignment must
therefore use `(tile - 4586) // 8`, including base tiles 4586, 4594, 4602,
4610, 4618, and 4626. Starting at 4587 assigns every later base pose to the
previous direction and causes a recurring one-frame facing flip in-game.

Shared dissolve TILEs `4778-4785` use increasingly large stock effect canvases.
Replacement art must cap their character anchor height instead of fitting each
frame independently, or the dying Phantom grows to several times normal size
before the gravestone appears. Shared frames `4783` and `4784` additionally
require a `-52` pixel vertical correction because their stock effect anchors
sit well below the surrounding death frames.

Tile `4793` in the Priestess scaffold is retained as a useful character/guild
interface-panel reference. The active guild panel background path currently
comes from the AP07 `INTI` to `PHTI` raw-texture remap described above.

## Current Limitations

- The Phantom death sequence is not final. Its shared middle dissolve frames
  still look spatially inconsistent in game even after their gross scale and
  vertical-anchor corrections. Review the actual engine sequence again before
  changing more offsets.
- The current Phantom gravestone is a temporary first pass and is next in line
  for a complete visual redesign.
- `Frost Armor` is packaged for its first full in-game stability and placement
  pass. The current fixed-`240` combat-awareness trigger produced two
  intermittent crashes in the latest test, followed by a longer run with no
  crash. The cause is not yet isolated, so do not treat Frost Armor combat
  entry as stable. A nested `GetAttribute` argument to `compile_enemies` was
  removed because stock GPL never uses that form, but the later intermittent
  crashes mean that change was not a complete diagnosis. `Blizzard` still
  needs its dedicated implementation pass.
- The Phantoms Haunt borrows the stock Elf recruit dialog. This keeps the mod
  Workshop-only, but the Elven Bungalow shares the overridden AP07 dialog art
  while the mod is active.
- The Phantoms Haunt is still a proof of concept rather than a balanced finished
  content mod.

## Next Session

Checkpoint recorded July 25, 2026:

- The building, construction progression, destruction progression, cast
  shadows, shadow seams, and construction pit cleanup are working in game.
- The generated and decoded-CAM validators now reject mixed shadow/body RLE
  runs, missing seams, bounded transparent construction pits, and transparent
  islands enclosed entirely by shadow controls.
- The directional Phantom hero, floating movement, action frames, corrected
  direction mapping, projected detached shadows, movement speed, death and
  dark-ice gravestone sequence, and staff-centered cyan snowflake cast effect
  are approved for the spell pass.
- Cast body geometry and recovery poses are locked directionally across all
  eight Cast records; validators reject the old Priestess swirl, mismatched
  recovery direction, clipping, and frame-size drift.
- Phantom retreat and combat estimates are temporarily set to a fearless
  testing profile so spell behavior can be exercised without frequent retreat.
- Ice Lance now has final-path generated-source projectile/icon art, 32 packaged
  directions, `8` damage, `180` Phantom casting range, native impact animation,
  and a centralized three-second non-stacking movement/action Chill with an
  approved animated cyan snowflake indicator.
- Ice Lance has passed the current in-game art, direction, impact, damage,
  refresh, non-stacking, movement-slow, action-slow, duration, and status-icon
  review. The fixed modifiers deliberately describe a mild Chill rather than
  promising an exact percentage on every unit.
- Frozen Cowl is a non-droppable starter item that displays and grants `+2`
  physical armor. Black Icerod is a non-droppable starter item that displays
  and grants `+5` Parry through the stock magical Parry adjustment. Both are
  cleaned up on death and realm exit.
- Phantom base weapon damage is intentionally `0`. Strength is `8`, producing
  the minimum safe stock `hero_damage` value of `1` through integer `8 / 8`.
  This prevents `target_eval` division by zero without restoring the Icerod's
  obsolete weapon-damage bonus. Ice Lance remains fixed at `8` spell damage.
- Frost Armor learns at level 3, persists until the first qualified attack
  attempt, negates ordinary weapon damage, consumes against units and
  buildings, Freezes unit attackers for three seconds, and recharges after a
  completed full-health rest at the Phantoms Haunt, an Inn, or a Gazebo. Its
  animated octahedral ward and three size-aware frozen casings are packaged
  from generated source art. Its auto-cast currently checks a fixed `240`
  radius, but intermittent crashes during enemy entry remain unresolved.
- Next: isolate Frost Armor's intermittent combat-entry crash before further
  spell work, then retest attack detection, building consumption, ranged
  retaliation, rest recharge, and effect placement before continuing to
  Blizzard.

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Build-PhantomGuildPoc.ps1
```

The build automatically performs a fast structural verification after GPL
compilation. A successful build prints `Verification passed.`; a malformed or
incomplete package stops with the specific archive, entry, size, or reference
that failed verification.

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
