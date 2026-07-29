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
  - `Black Icerod`, item ID `81`, retains its in-game-confirmed stable `+8`
    weapon damage, grants `+5 Parry` through the same
    `MagicalAdjustAttribute(Parry)` path used by Majesty's Ring of Protection,
    and provides `+10` casting range through the safe prototype-backed path.
  - Blacksmith and Wizard Guild purchases use Majesty's four stock structural
    and magical equipment attributes. The Cowl and Icerod each have sixteen
    internal special-item variants so their visible name and tooltip can mirror
    all four structural tiers and all four independent enchantment tiers.
  - `Frost Armor`, item ID `82`, is granted at level 3 as a visible,
    non-droppable class-effect marker and grants the spell's persistent `+10`
    physical armor.
  - Phantom class items are removed by `Phantom_death` before normal gravestone
    handling and by a class guard in the stock-compatible realm-exit inventory
    disposal path.
- Phantom baseline balance: `8` Vitality, `8` Strength, `25` Magic Resistance,
  `25` Dodge, and `180` conceptual base casting range. Artifice remains `8`;
  Majesty uses it for equipment-shopping choices, stealing checks, and
  Gambling Hall fallback rolls, not spell damage, casting speed, range, or
  cooldown.
- Generated placeholder voice/soundbite WAVs. A dedicated Phantom spell-audio
  pass is intentionally deferred until the rest of the content is complete.
- Wizard-style hero stats and Wizard decision-tree behavior through
  `Phantom_tree`.
- A Phantom-only `Ice Lance` spell entry, generated-source directional
  projectile and icon art, a copied Frost Field hit overlay, and a timed Chill
  debuff.
- A level-3 `Frost Armor` spell with a persistent crystal ward, one-hit damage
  negation against normal weapon and spell damage, a three-second retaliatory
  Freeze, and rest-to-recharge behavior.
- A level-4, melee-gated `Icy Touch` which combines one normal weapon attack
  with `30` spell power, refreshes Chill, and applies Gravechill.
- A level-5 `Call to Grave` which is mechanically a direct
  Wizard Teleport clone with custom ghostly ice-portal art.
- A finalized level-6 `Eternal Soul` combat self-buff with custom ghost-flame
  cast and status art plus empowered Chill.
- A finalized level-7 `Endless Winter` action built from the stock Wizard Meteor
  Storm behavior with Phantom-only visual units. At cast time it uses the
  stock `compile_enemies` helper, which returns enemy monsters and heroes but
  not buildings, then stock `Pick_Closest` to select the nearest eligible unit
  within the Phantom's current Icerod-aware casting range. After that stock
  selection, an eligible live current combat target wins only when its stock
  `DistanceBetweenAgents` value exactly ties the selected closest distance;
  otherwise the closest result is unchanged. The custom-art storm
  unit is created at that unit through the stock `CreateSpellUnit` target path;
  validation prevents a building-only encounter from consuming the cooldown.
  `CreateSpellUnit` passes that original unit into the stock-style unit-created
  callback. The callback records it through Majesty's engine-managed
  parent/child relationship, so the repeating thread does not retain a raw
  target argument after that unit dies. Stock `TeleportToUnit` relocates an
  invisible spell anchor exactly onto the still-live original target before
  each pulse scan; if that target is gone, the anchor remains at its last valid
  center. An exact world-coordinate comparison skips relocation only when the
  anchor and target occupy the same X/Y coordinates. `DistanceBetweenAgents`
  cannot guard this path because it measures edge/range separation and can
  report zero for nearby agents whose centers are still different, suppressing
  tracking. The coordinate guard is required because Majesty's stock movement
  routine divides by the requested travel distance and crashes on an exact
  zero-distance move. The visible vortex is a single long-lived overlay
  attached to that anchor, preventing each teleport from resetting its
  rotation animation. Because the parented moving anchor does not reliably
  inherit stock Meteor Storm's timeout/thread teardown, a one-shot cleanup
  callback runs 100 ms after the overlay ends. It kills that anchor's periodic
  damage and tracking threads and deletes the invisible host; the engine
  spell-unit timeout remains 500 ms later as a safety net. This prevents
  invisible tornado pulses after the vortex art expires without truncating the
  last pulse at 20.8 seconds. Visual tracking runs independently every 25 ms,
  while damage retains the stock 1600 ms pulse cadence. The blank anchor can
  therefore request up to 40 attached-vortex position updates per second
  without multiplying damage or resetting the overlay's rotation. This keeps
  the follow motion visually smooth without the unnecessary script overhead of
  the discarded 10 ms stress-test value. No retargeting or travel leash is
  applied; the storm follows its original living target and remains at that
  target's last position after death. Its explicit spell-data entry runs the
  active loop.
  A Phantom-only unit-created callback performs the
  immediate first pulse through the same custom path as every later pulse,
  preventing the stock Wizard missile and impact from leaking into frame one.
  The loop uses a stock-speed four-phase snowflake-flick missile and a custom
  tornado impact. The vortex uses 15 phases which advance its internal
  ice-flow arms in the fixed elliptical ground plane while preserving the
  outer rim, footprint, and center; each impact grows and roils through 8
  bottom-anchored phases on fixed canvases to avoid sprite bounce.
  Phantom-only `PHW4` and `PHW5` particle systems replace the stock `XL20`
  storm and `XL21` missile attachments embedded in the cloned IMAG records.
  Their 13-frame and 7-frame cyan snowflakes preserve the stock emitter
  motion without leaking the separate orange meteor orb or smoke-ring art.
  It retains the stock 175-unit pulse scan, 21-second duration, and 55-second
  cooldown. Damage restores the original staged Endless Winter design instead
  of Meteor Storm's `5`-to-`25` random roll: targets within the fixed
  `24`-unit Icy Touch/melee range take `8`, targets through `80` take `6`, and
  all remaining targets in the `175`-unit scan take `4` per pulse. The storm
  anchor measures center-to-center world distance before launch using stock
  `DistanceBetweenCoords(LocationOf(anchor), LocationOf(target))`, then encodes
  the selected tier through one of three visually identical Phantom
  projectiles. `DistanceBetweenAgents` is deliberately not used here because
  it measures edge/range separation; the large storm-anchor footprint can make
  a visibly distant target report zero distance. Tiering also cannot be
  deferred to impact because a projectile callback runs after that projectile
  has reached the victim, where its measured distance is effectively zero.
  Every surviving impact uses the shared non-stacking
  three-second Chill state: the `0-24` inner tier requests empowered tier-2
  Chill, while both collateral tiers request standard tier-1 Chill. Repeated
  impacts refresh the applicable tier through the same watcher used by Ice
  Lance and Icy Touch; a standard hit cannot weaken or extend an already-active
  empowered Chill. Custom IDs and CAM entries are used throughout, so the
  Wizard's stock action, units, missiles, impacts, and artwork are not
  overridden.
- Healers exclude Phantoms from ordinary healing. A Priestess's Drain Life
  secondary heal treats allied Phantoms as undead: Priestess self-healing
  remains first priority, followed by the most-injured Phantom, then controlled
  Skeletons.

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
- The complete six-spell Phantom progression is implemented and verified:
  Ice Lance at level 1, Frost Armor at level 3, Icy Touch at level 4, Call to
  Grave at level 5, Eternal Soul at level 6, and Endless Winter at level 7.
  Icy Touch additionally requires a completed level-2 Haunt; Endless Winter
  additionally requires a completed level-3 Haunt. Losing the last qualifying
  Haunt removes the gated spells until the requirement is restored.
- `Phantoms Haunt` has a stock-native three-level upgrade chain. Level 2
  activates Gravekeeper, doubling allied Priestess Drain Life healing. The
  level-3 Rush unto Death implementation uses a stock-shaped clone of Lunord's
  Winged Feet begin/end mechanics for each allied Priestess. The current tuning
  uses mild offsets (`-22 MovementRateModifier` and `-10 ActionRateModifier`),
  uses the same `HasEffectWingedFeet` anti-stacking
  flag, and applies the exact inverse offsets when the level-3 requirement is
  lost. The clone is persistent and deliberately creates no icon, visual
  effector, or speed trail. Direct runtime writes to `ATTRIB_Speed` compiled
  but did not alter
  existing heroes' locomotion; fractional negative `MovementRateModifier`
  offsets caused alternating burst/slow displacement; and a rejected private
  unit-type transformation caused a Phantom recruitment crash. None of those
  disproved routes remains.
  Phantom escort behavior uses a deliberately stock-shaped implementation: the
  mod replaces
  `Priestess_tree` by its stock name, retains the complete Northern Expansion
  Priestess decision order, and inserts the generic stock
  support decision immediately after `Build_Horde`. The one-follower
  experiment routes only Priestesses through
  `Phantom_Priestess_Follow_Support_Check`, a line-for-line clone of the proven
  stock selector except that its local nearby-supporter threshold is `2`
  instead of global `#support_max` (`3`). The stock query counts the evaluating
  Priestess, leaving room for only one established follower. Rangers and
  Wizards remain on the original function and original cap. After filtering,
  the Priestess uses the stock `Pick_Closest` helper instead of arbitrary list
  order, selecting the nearest Phantom with an available escort slot. Once
  selected, Priestesses use `Phantom_Priestess_Follow_Support`, a stock active-follow
  clone with one anti-stutter substitution. Stock passes the moving target
  agent directly to `$Move`; the Priestess clone snapshots the Phantom's
  current location, sets `Target = ThisAgent` for coordinate-mode
  `Travel_To`, and walks to that stable coordinate. On arrival, the stock
  backscript cycle refreshes the snapshot. This avoids moving-agent travel
  terminating whenever `$IsMoving` briefly reports false while preserving the
  stock distance threshold, combat, boredom, and disengagement behavior.
  The full-strength stock Winged Feet path and its invisible clone were
  confirmed smooth in-game before these milder values were selected.
  The stock
  `follow_support_check` path rejects only Phantoms, preventing their borrowed
  Wizard decision tree from making them follow Barbarians or Monks while
  preserving ordinary Ranger and Wizard support behavior.
- Level 2 and 3 use complete custom world-art sets: upgrade construction,
  inactive, eight-frame active pulse, two damage phases, collapse, and final
  destroyed states. Every state is independently fitted, palette-mapped, and
  given a geometry-derived cast shadow before its custom TILE is appended and
  remapped into the corresponding `PHG2` or `PHG3` IMAG.
- `Phantoms Haunt` now has a generated Phantom-only building sprite set wired
  through appended tile records, without modifying the stock Wizard Guild art.
- Occupied Haunts use an eight-frame full-building active animation so
  the cyan windows and arcane highlights pulse while heroes are inside.

Confirmed Paladin/Haunt interaction:

- Placing a player-owned `Phantoms Haunt` foundation immediately disables stock
  Paladin recruitment while leaving the Dauros-gated Paladin entry visible in
  the Warriors Guild. If living Paladins exist, the first placed foundation
  posts a map message flag, plays the stock advisor alert, and records a plain,
  readable chat warning; cancelling or destroying the final placed Haunt
  restores recruitment.
- Completing a Haunt irreversibly dismisses that player's living Paladins
  through stock `Unit_Dismissed`/`flee_map`. Destroying the completed Haunt
  restores future recruitment but does not recall Paladins already leaving.
  The Embassy and Outpost random selectors also omit Paladins while any Haunt
  foundation exists; the stock quest-special-event fallback remains intact.
- Known timing edge: a Paladin already queued but not yet spawned when the first
  Haunt foundation is placed does not cause the warning to appear. Recruitment
  is still disabled immediately, and the Paladin leaves after spawning.
- `A Deal with the Demon` is patched for testing so it starts with a Phantoms
  Haunt, a Temple to Dauros, and an Embassy. These player-owned test buildings
  do not run `Hero_Generator`; the stock generator remains attached only to the
  quest's `#NotMyPlayer` guild list.
- Expansion quest `Rise of the Ratmen` is the full compatibility test bed. It
  starts with a Phantoms Haunt, Temple to Dauros, Temple to Fervus, Temple to
  Krypta, Warriors Guild, and Embassy while preserving the quest's stock
  victory and event threads. This allows direct Paladin, Priestess, Phantom,
  upgrade, stock-Fervus-panel, and Priestess-support testing in one run.

Next planned work:

- Give the completed spell suite its dedicated custom audio pass.
- Restore or reattach proper Phantom hero sprite shadows.
- Revisit the Phantom death dissolve and gravestone art.
- Continue balance testing without changing the now-stable spell plumbing.

## Custom Special Items

The stable path for giving Phantoms custom special items is the same basic
pattern used by Majesty's quest and Bazaar inventory items:

1. Define a unique numeric item constant in `phantom_gpl()`:

   ```gpl
   expression #Phantom_Item_FrozenCowl 80
   expression #Phantom_Item_BlackIcerod 81
   expression #Phantom_Item_FrostArmorBonus 82
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
   automatically add its stats to the owner. The current item grants therefore
   apply their bonuses explicitly:

   ```gpl
   $AdjustAttribute (thisagent, #ATTRIB_Armor_Basic_Damage, 2);
   $AdjustAttribute(thisagent, #ATTRIB_Weapon_Basic_Damage, 8);
   $MagicalAdjustAttribute (thisagent, #ATTRIB_Parry, 5);
   $AdjustAttribute(thisagent, #ATTRIB_Armor_Basic_Damage, 10);
   ```

   Frozen Cowl and the level-3 Frost Armor marker use the ordinary armor
   adjustment from the stock Ring of Protection path. Black Icerod retains its
   stable weapon-damage adjustment and uses the Ring's exact
   `MagicalAdjustAttribute` path for its Parry bonus. Their `QITM` strings
   display the current structural, magical, Parry, and casting-range values;
   Majesty does not generate those descriptions from the GPL changes, so
   validation keeps every tier's displayed text and mechanical values
   synchronized.

5. Add the display name to `QITM` in `phantom_gpltext.cam`. `QITM` is an
   indexed STRT table, so the table must physically extend to the item ID. For
   example, item ID `80` needs a real slot 80, not only a string record whose ID
   is 80.

The current generator handles step 5 in `write_gpltext_cam()` by extending
`QITM` through `patch_indexed_strt_strings()`. This was required to avoid
`Unknown Item` in the hero Items panel.

### Tiered Cowl and Icerod upgrades

The Phantom declares stock `Staff` and `Leather` equipment eligibility so
Majesty's unmodified `Purchase_Equipment` decision tree will consider all four
normal equipment paths. Both upgrade chances are `100` during testing. This
also means the ordinary equipment rows may describe the underlying slots as a
Staff and Leather Armor; the separate Special Items rows remain the
player-facing Cowl and Icerod representation.

The durable mechanical state stays in Majesty's normal attributes:

- `Weapon_Struct_Bonus` selects the Icerod's Blacksmith tier and contributes
  normal structural weapon damage.
- `Weapon_Magic_Bonus` contributes normal magical weapon damage and adds `10`
  Icerod casting range per enchantment.
- `Armor_Struct_Bonus` selects the Cowl's Blacksmith tier and contributes
  normal structural armor.
- `Armor_Magic_Bonus` contributes the Cowl's normal magical defense.

The Blacksmith tier controls the visible four-name path:

```text
Frozen Cowl -> Icy Cowl -> Hardened Ice Cowl -> Eternal Ice Cowl
Black Icerod -> Dark Icerod -> Deep Icerod -> Eternal Icerod
```

Structural and magical levels are independent, producing sixteen possible
states for each item family. IDs `80`, `81`, and `82` retain their existing
meanings for save compatibility. Cowl variants use IDs `83-97`; Icerod
variants use IDs `98-112`. A successful stock grant deletes the previous
family marker and creates the one selected by
`structural_level * 4 + magical_level`. Item replacement never reapplies the
starter `+2` armor or `+8` damage bonuses.

Icerod Blacksmith grants also apply `5 * (new tier - old tier)` Parry through
`MagicalAdjustAttribute`. The delta is required because stock Majesty may buy
several building-supported upgrade levels during one visit. Resulting Icerod
Parry bonuses are `+5`, `+10`, `+15`, and `+20`.

Active Frost Armor temporarily adds `10000` to `Armor_Magic_Bonus`, the same
attribute used by Cowl enchantment. The Phantom-specific Wizard Guild check
subtracts that temporary ward amount when determining the real enchantment
level. If a Cowl is enchanted while the ward is active, the grant stores
`10000 + new enchantment level`; consuming the ward later subtracts `10000`
and leaves the legitimate enchantment intact.

Stock `Weapon_Magic_Bonus` increases weapon damage and AI weapon evaluation;
it does not increase Ice Lance spell damage. Icerod enchantment instead adds
range through `Phantom_effective_casting_range`: `190`, `200`, `210`, and
`220`. The Phantom branches in stock-compatible `attack_object` and
`getattackrange` use that computed value. The implementation does not mutate
the runtime `castingrange` prototype field.

Healing-potion shopping is centralized in stock `Potion_Check`, called from
`Purchase_Equipment` for both Marketplaces and Trading Posts. The mod overrides
that stock function by name, the same supported replacement mechanism already
used for `DEAL_DEMON`. The first check returns `False` when the buyer's title is
`Phantom`, before a shop target, task name, or purchase intent can be assigned.
The remainder of the function retains the stock checks and task setup for every
other hero. Phantoms therefore continue using the unmodified stock
`Wizard_tree` and never start a healing-potion shopping trip.
In-game verification confirms that Phantoms continue normal decision-making,
do not get stuck thinking, and do not enter the healing-potion purchase path.

Two earlier attempts masked the Phantom's potion count through a copied Wizard
tree and a custom equipment wrapper. Both left the hero permanently stuck in
its thinking state, including the version that used stock `AdjustAttribute`
counter mutation. Do not retry tree-level interception; the narrow
`Potion_Check` replacement is the stock-compatible class hook.

The Magic Bazaar does not sell ordinary healing potions. Rangers have
class-specific herb behavior, while several quests grant potions only to
explicitly spawned Wizards, Paladins, or Elves. No generic stock quest grant
was found that applies to a normally recruited Phantom.

### Phantom healing compatibility

Stock Healers use `Eval_For_Healing` for both their long-range rescue decision
and their nearby combat heal. The replacement retains the stock loyalty,
distance, injury, and intelligence scoring but omits heroes whose title is
`Phantom`. `Healer_Heal_Effect` repeats the Phantom guard immediately before
the effect and HP change, then resets the Healer's task. This second guard
prevents a stale or externally assigned Phantom target from receiving natural
healing or trapping the Healer in a repeated cast attempt.

Priestess undead healing is the secondary effect of a successful Drain Life
hit against a unit. The stock order is Priestess self-healing followed by a
controlled Skeleton. The Phantom extension preserves the attack and its
five-point stock heal while using this order:

1. Heal the Priestess if she is injured.
2. Otherwise heal the allied, in-sight Phantom missing the most HP.
3. Otherwise heal the controlled, in-sight Skeleton missing the most HP.

The implementation deliberately does not override global `Healing_Shared`;
doing that would block the Priestess heal along with every other heal. Instead,
the two stock entry points now carry narrow class rules:

- `Heal` rejects a Phantom target unless the caster's title is `Priestess`.
  This blocks Healers, healing potions acquired outside normal shopping, and
  the Legendary Heroes Rune of Healing while preserving Drain Life's
  five-point undead heal.
- `Player_Heal` always rejects a Phantom target. Both the Agrela and Fervus
  player-cast healing spells use this function, so their normal spell visuals
  may still play but they restore no Phantom HP.

The expansion's Regeneration Elixir bypasses both functions by modifying
`HealingRateModifier`. The stock `Bazaar_Item_Check` replacement rejects only
item four when the shopper is a Phantom, before assigning a destination,
intent, or purchase task; all five other Bazaar items retain their stock
logic. `Regeneration_elixer_effect` also consumes an externally granted elixir
without applying its effect, preventing quest or scripted grants from
bypassing the purchase check. The global `Healing_Wind` random event similarly
skips Phantoms while retaining its stock effect for every other living hero.

The healing audit intentionally preserves these separate mechanics:

- full healing while resting in a guild, inn, gazebo, Royal Gardens, or other
  lived-in building, which also drives Frost Armor recharge;
- HP gained together with Max HP from leveling, the Shard of Health, or a
  temporary transformation;
- resurrection and reanimation, which operate on dead units rather than
  healing a living Phantom;
- class-self effects that a Phantom's Wizard-derived decision tree cannot
  normally request, including Meditation;
- Hall of Champions `Champion's Vigor` regeneration, intentionally treated as
  an internal champion power rather than an external healing effect.

Do not use the earlier birth-thread transfer approach for Phantom starter gear.
Creating string-named custom inventory items through a delayed hero thread was
unstable and caused crashes after Phantom spawn.

Phantom class gear should also be removed before normal hero death item-drop
logic runs. The current build does that with `Phantom_death`, which deletes
every Cowl and Icerod tier plus `#Phantom_Item_FrostArmorBonus`, then calls the
stock `gravestone` flow so other legitimate inventory items still behave
normally. Add any future Phantom-only starter or class gear to
`Phantom_remove_starter_items` at the same time it is granted.

Class gear that must never become loot also needs
`<Attribute ID="CanDropItem" Value="0"/>` in its unit description. Majesty's
stock `flee_map` path calls `Hero_Drop_Quest_Items` after a departing hero
enters the palace. `CanDropItem=1` makes that function delete the inventory
entry and spawn its world-item agent beside the palace; `0` makes it delete the
entry without spawning anything in the documented stock path. In practice,
Majesty's native inventory lookup still classified the custom Phantom IDs as
droppable even though their deployed unit descriptions contained
`CanDropItem=0`.

The package therefore replaces `Hero_Drop_Quest_Items` by name using the same
supported stock-function replacement mechanism as `Potion_Check`. For a
Phantom, the wrapper first stops the class watcher and invokes
`Phantom_remove_starter_items`; stopping the watcher prevents the level-3 Frost
Armor marker from being recreated between cleanup and deletion. The remainder
of the function preserves Majesty's stock loop exactly: all other inventory
items are deleted, exempt Marketplace items stay non-droppable, and legitimate
droppable quest items are spawned normally. Other hero classes enter the
unchanged stock portion immediately. This realm-exit path is verified and
needs no special downstream handling. Keep the explicit `Phantom_death`
cleanup, which is a separate verified requirement.

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

The current Workshop-only compromise retains the stock Elf recruit handler:

```text
AP07
```

The Phantoms Haunt uses `AP07` because that ID already has the right recruit
behavior. To expose a native upgrade control, the mod now emits the stock AP10
Temple-to-Fervus menu layout under the AP07 name. It replaces the strings and
redirects the raw texture reference from `INTIraw textures` to
`PHTIraw textures`. The AP10 menu references the Cultist guild member/count
icon through image token `AVC1`, so the generator rewrites:

```text
AVC1 -> PHM1
INTI -> PHTI
```

This makes the Phantoms Haunt use the Phantom icon and the portions of the
custom background that the AP10 layout addresses. Because AP07 is shared, the
stock Elven Bungalow also inherits those AP07 visual overrides while this mod
is active. The newer `PHTI` technique does prevent any global overwrite of the
stock `INTIraw textures` image and therefore does not mutate the Elf art assets
themselves, but it cannot make one global `SMNU/AP07` resource render two
different layouts. Restoring a truly stock Elf panel while retaining this
Haunt panel requires either a distinct recruit-capable executable dialog
handler or moving the collision to another stock guild, which is not an
acceptable data-only fix.

AP07 does not dynamically populate AP10's level-number field; it leaves the
stock placeholder `1` at every Haunt level. Those label, number, and tooltip
strings are intentionally blanked. The backend `Level` values, native upgrade
button, upgrade chain, and perk watcher remain correct. AP07 also has no safe
callback for AP10's temple Spell window: clicking that control crashes. The
generator therefore blanks its strings and writes a zero-sized hitbox into the
guarded stock AP10 control rectangle while leaving Upgrade and Heroes intact.

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

- Clone the stock upgradable temple dialog `SMNU` entry from `AP10`, emit it as
  `AP07`, and remove the AP10-only level readout and Spell control as described
  above.
- Rewrite its raw texture image token from `INTI` to `PHTI`.
- Clone the stock `INTIraw textures` image record as `PHTIraw textures`.
- In the cloned `PHTI` image, remap AP07's backing tile `466` plus AP10's
  primary and secondary Fervus backing tiles `474` and `495` to one newly
  appended tile. AP10's primary tile is the bright green layer that otherwise
  survives behind the Haunt controls.
- Encode the appended tile from the generated Phantom panel source art.
- Emit only `PHTIraw textures` and the appended backing tile in
  `phantom_interfacedata.cam`; leave the stock `INTI` and `INBg` records alone.

The key correction to the earlier investigation is that tile `466` belongs to
the original AP07 Elf layout. After AP10 was cloned under AP07 to gain its
upgrade control, the visible Fervus layers came from raw-texture animation sets
whose frames reference tiles `474` and `495`. Searching only the old AP07 tile
could never remove the green AP10 panel. The reliable diagnostic is to resolve
the raw-texture animation-set IDs embedded in the selected `SMNU` back to their
TILE frames, rather than guessing from a contact sheet. The replacement remains
inside the private `PHTIraw textures` clone, so stock `INTIraw textures` art is
not modified.

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
BUILDING_DIALOG_BACKING_TILES = (466, 474, 495)
BUILDING_DIALOG_BACKING_TEMPLATE_TILE = 466
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
Phantom's conceptual unequipped casting range is `180`; Black Icerod raises the
effective value to `190`, still below the Wizard's `240`. Majesty stores
`castingrange` as a GPL prototype field rather than a normal engine attribute.
Stock scripts read that field during combat but do not mutate it. An earlier
`thisagent's "castingrange" += 10` item grant caused an access violation when
`attack_object` began, so the current safe implementation stores the guaranteed
Icerod-equipped value `190` directly in `Phantom_Hero_Data.dat`. Enchanted
Icerod range is calculated without changing that field:
`190 + Weapon_Magic_Bonus * 10`. Phantom-only branches in the stock-compatible
combat and travel-range helpers use the resulting `190-220` value. Every
living Phantom receives the Icerod at birth and keeps it until death or realm
departure, so the base prototype value and inventory presentation remain
aligned.

Casting range belongs to the hero rather than the individual spell, so the
Icerod technically affects the Phantom's complete spell kit; Frost Armor is
self-targeted. Icy Touch deliberately uses its
fixed `24`-unit melee gate, so the Icerod's casting-range bonus affects Ice
Lance but does not extend Icy Touch. Custom special items are stored as
inventory IDs and do not automatically transfer XML attributes to their owner.
Frozen Cowl therefore uses the stock Ring-of-Protection pattern to apply `+2`
basic-damage armor when granted. The Cowl passed combat, treasure, and gold
tests independently.
Earlier Black Icerod Parry tests replaced rather than supplemented the stable
`+8` weapon damage. That overlapped a separate stock `target_eval`
divide-by-zero hazard and did not isolate Parry as the cause. Stock
`target_eval` divides enemy HP by `hero_damage`; that helper totals basic,
structural, and magical weapon damage, then adds integer
`Strength / strength_div`. For the original Strength-2 caster with no Icerod
damage, every term was `0`, causing the crash on entering combat. Majesty's
`strength_div` is `8`, so the Phantom now uses Strength `8` with base weapon
damage `0`. Integer division supplies the required AI-evaluation floor of `1`,
and the retained Icerod damage supplies a further stable floor while equipped.
The separate XML `Attack` value remains `30`, and Ice Lance damage remains its
independent fixed value of `8`.

The current Icerod implementation keeps the confirmed `+8` weapon-damage
adjustment and adds `+5 Parry` with the exact
`MagicalAdjustAttribute(Parry)` native used by the stock Ring of Protection.
Both mutations occur inside the same inventory-item absence guard, so neither
can stack during the birth path. Package validation requires both bonuses and
rejects an ordinary `AdjustAttribute(Parry)` substitution.

On a non-building target, `Ice_Lance_Hit` starts or refreshes a three-second
per-target Chill counter and adds `50` to
`ATTRIB_MovementRateModifier` and `500` to `ATTRIB_ActionRateModifier`.
These engine modifiers use different scales rather than percentages: the
movement value provides a gentler slow, while the larger action value follows
stock Majesty slow effects closely enough to make action delay observable.
`Phantom_Chill_Watch` reverses both values when the counter reaches zero.
On a repeated hit, only `PhantomChillRemaining` is reset to three seconds; the
modifiers, watcher, and icon are not created a second time.

Normal Chill uses the `PHo4` overlay and packaged `PHo4chill_icon` image.
Empowered Chill uses the otherwise identical `PH11` overlay and
`PHc3emp_chill_icon` image. Both are infinite-duration visuals while the
separate per-target watcher owns duration and modifier cleanup, but only one
can exist on a target. A tier upgrade deletes the old icon, waits `200`
milliseconds through the existing watcher, and only then creates the new tier
icon. This avoids Majesty briefly rendering both entries while an effector
deletion is still leaving its overlay list. Ordinary refreshes never delete or
recreate the active icon.

Both images use the larger stock animated-status canvas and the same 29-frame
geometry: the snowflake spins around its vertical axis through horizontal
perspective compression, with a subtle scale pulse and vertical bob. Normal
Chill retains layered dark-blue, bright-cyan, and pale-cyan strokes. Empowered
Chill keeps every silhouette, hotspot, and animation frame unchanged while
shifting the palette to navy, medium blue, and muted blue highlights with no
white high points.

### Chill and status-effect implementation notes

Majesty's rate modifiers are fixed engine offsets, not percentage inputs.
`ATTRIB_MovementRateModifier` and `ATTRIB_ActionRateModifier` also use different
numeric scales; assigning the same number to both does not produce the same
slow and can make it appear that both modifiers affected movement. The working
Ice Lance values are therefore intentionally different (`+50` movement and
`+500` action). Positive values slow the corresponding rate, and the watcher
cleanup applies the exact negatives. Because units have different base
movement classes and action timings, one fixed modifier can produce different
effective percentage changes between units. No dependable GPL path was found
for converting the live speed/action class into an exact percentage reduction,
and stock effects such as Medusa-style slows likewise use fixed modifiers.
Treat this as a mild Chill, not a guaranteed numeric-percent debuff.

Stock Medusa Slow uses a `HasEffect` attribute to reject repeat applications;
it does not refresh. Deleting and immediately recreating a timed effector is
not a stock refresh mechanism: deletion invokes cleanup while a same-named
replacement may already be entering the overlay list. Closely spaced hits can
therefore overlap icons or cross modifier cleanup.

The safe refreshable sequence follows the counter/watcher status pattern used
by Majestic Majesty:

1. Use `HasAttribute` to add per-target `PhantomChillRemaining`,
   `PhantomChillActive`, `PhantomChillTier`, and `PhantomChillWatch`
   attributes exactly once.
2. Set `PhantomChillRemaining` to the requested duration on a same-tier hit.
   Empowered hits upgrade and refresh normal Chill; normal hits do not replace
   or extend an active empowered Chill.
3. Only when `PhantomChillActive` is false, apply the two modifiers. Independently
   require `CheckEffector` to be false before creating the tier's one
   infinite-duration icon, making the engine's attached-effector list the
   authoritative visual deduplication guard.
4. Start one 100 ms watcher if it is not already running. The watcher decrements
   the counter, removes the modifiers and icon at zero, and kills itself.

Same-tier rehits never recreate their icon and never apply another set of
modifiers, so multiple Phantoms refresh rather than stack. A tier-1 to tier-2
upgrade applies only the modifier delta and swaps the visible icon once. The
three-second duration lives on the `ice_lance` action as `EffectorDuration`;
both Ice Lance and Icy Touch pass that value to the shared counter helper
through `$GetSpellAttribute`.

`Phantom_Apply_Chill` owns that refresh sequence for both Ice Lance and Icy
Touch, keeping the three-second duration, refresh behavior, and non-stacking
modifiers identical between the two attacks.

For floating buff/debuff symbols, cloning an existing animated status-image
layout is more reliable than inventing overlay geometry. Both Chill tiers clone
the 29-frame `XR25plague_icon` image record, append custom remapped TILE
records, and keep the template's canvas, hotspot, and timing. The snowflake
needs stronger scale and line weight than an isolated review suggests because
in-game terrain and sprites reduce legibility. Its approved animation
simulates rotation around the vertical axis by compressing the horizontal
dimension, plus a small bob, pulse, and sweeping glint. Rotating the entire
snowflake in the image plane reads as a wheel and was rejected.

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

### Icy Touch

Phantoms learn Icy Touch at level 4 as a melee-gated Attack spell. Its action
follows the stock scripted-attack-spell presentation used by
abilities such as Double Attack and Super Strike: the Phantom's directional
`Attack` animation drives the existing GPL callback. It retains the stock
`Fire_Blast` sound, rank `3`, and five-second timeout.

`Icy_Touch_Cast` is now one self-contained monster-style action callback. It
re-reads the Phantom's current `"Target"` into a local agent instead of relying
on the callback's supplied target argument, validates that current target, and
invokes one stock `$make_attack(thisagent, target)`, matching the established
Double Attack and Super Strike weapon pattern. This performs a complete
ordinary weapon attack with the Phantom's current hit chance, Strength, weapon
damage/upgrades/enchantment, and the target's dodge, parry, and armor. If the
target survives, the same callback performs the magic hit and applies both
debuffs directly. It does not rebuild an enemy list, invoke a secondary hit
helper, or depend on a missile-arrival callback. The earlier invisible PHp2
carrier still allowed the weapon half to execute but never called its hit
script in game, which was why every impact and debuff experiment appeared
inert. PHp2 and its 128 blank tiles have been removed. The profile and
spell-list icons still copy stock Fire Blast art.

Icy Touch uses a stock-style Attack-spell validation callback modeled on the
expansion's `Multiple_Attack_Check`. `Icy_Touch_Check` copies the Phantom's
current target into a local agent, rejects invalid/dead targets and
buildings/lairs, and returns available only when that specific target is
within the fixed `24`-unit `Phantom_Icy_Touch_Range`. This check runs inside
`getbestspell` before `attack_object` chooses its movement range. Outside
melee range Icy Touch is therefore excluded and the Phantom continues using
Ice Lance at its ordinary casting range; Icy Touch never requests movement
toward its target.

After the weapon strike, `Icy_Touch_Cast` directly calls
`$spell_attack(thisagent, target, 30)` and the same `Phantom_Apply_Chill`
helper used by Ice Lance with Ice Lance's three-second duration. The inherited
Fire Blast `Does_Resist_Fire` gate and player-cast Wither impact have been
removed: neither belongs in a frost attack, and both obscured whether the
monster action callback itself was applying the effect. The Chill helper
resets its per-target counter, so subsequent hits refresh Chill without
recreating its icon or stacking its modifiers.

The hit also applies the custom `Gravechill` debuff for eight seconds.
`Phantom_Apply_Gravechill` uses the same single-instance counter/watcher
lifecycle as Chill. Its first application reduces Strength by `5` through
`MagicalAdjustAttribute`, Defence by `2` through `ATTRIB_Parry`, and Resistance
by `2` through `ATTRIB_MagicResistance`, then creates one infinite-duration
`gravechill_icon`. Reapplication only resets
`PhantomGravechillRemaining` to eight seconds. It does not recreate the icon or
apply another set of modifiers. The sole 100 ms watcher restores the exact
attribute values and removes the icon when the counter reaches zero, so hits
from multiple Phantoms refresh one shared debuff rather than stacking it.
As with Chill, dynamic state is initialized only behind `HasAttribute`, and
`CheckEffector` must report no existing skull before icon creation.

The weapon half may miss, be dodged, or be parried while the directly invoked
magic half still resolves through `$spell_attack`; the magic/debuff half is
skipped only if the weapon hit has already killed the target. The callback
creates a separate zero-duration `gravechill_hit_effector` using PHg2, a
six-frame one-shot animation which runs through every source stage from the
ghostly skull forming to the completed crystal skull cracking into flying
shards. It has no end callback and owns no modifiers. The animated PHg1 status
symbol remains the persistent cyan crystalline skull, while the per-target
watcher owns its eight-second duration and cleanup. Both use:

```text
assets\source\icy-touch-impact-skull-source-v1-transparent.png
```

The icon uses the fully formed skull stage, removes detached source shards,
and packages it through the same 29-frame animation structure as the proven
Chill symbol. It has a subtle pulse, hover, and vertical-axis turn. There is
currently no custom cooldown effector, Phantom watcher trigger, or
modification to global combat/travel logic.

After a build, decode the actual packaged palette art with:

```powershell
.\scripts\create_gravechill_review.py
```

This writes
`artifacts\reviews\gravechill-icon-packaged-review.png`.

### Call to Grave

Phantoms automatically learn Call to Grave at level 5 through the stock
`AllowedSpells` and action `CharacterLevel` path. Its action retains the stock
Wizard Teleport travel path: spell type `4`, rank `4`, a `1200` ms effect, and
a `5000` ms cooldown. It is selected through Majesty's normal travel-spell
logic, with custom validation limiting it to home-bound travel.

`Call_To_Grave_Check` preserves the stock target-or-destination validation
shape, but first requires the stock home-bound task state:
`TaskName == "go_home"` and `Target == Home`. The ordinary `go_home` decision
sets both fields before entering `use_building -> travel_to -> TryTravelSpell`.
Terror-fleeing sets the same task only when the selected refuge is the hero's
actual home; fleeing to an inn or another shelter remains a `"visiting"` task
and cannot select Call to Grave. The task name persists throughout travel and
is cleared by stock `use_building` only after the hero enters home.

After that home-only gate, the checker compares the resulting trip distance
directly against `#Phantom_Call_To_Grave_Min_Distance`, currently `500`. Stock
`main_teleport_check` divides its supplied range by five, producing only a
`100`-unit cutoff for Teleport Short and a `280`-unit cutoff for Wizard
Teleport. A direct `500`-unit cutoff matches the full travel range of a
Marketplace teleportation amulet: Phantoms walk when an amulet could have
covered the trip and cast Call to Grave only for longer travel.

Phantom terror fleeing is redirected at the stock refuge-selection boundary.
The mod overrides `flee_part_II` with its stock body plus one title-specific
choice: when the fleeing agent is a Phantom and its home is valid, `go_here`
is always the Phantom's home. All non-Phantoms—and Phantoms whose home has
been destroyed—retain stock closest-refuge selection and the stock berserk
fallback. The remainder of the routine is unchanged: home selection sets
`TaskName = "go_home"`, preserves the original fleeing intent and danger
effect, and enters `use_building_safe`, where the ordinary travel-spell path
can select Call to Grave. Normal `flee`, `flee_absolute`, evaluation,
`use_building_safe`, and travel functions are not overridden.

Stock normal fleeing has an earlier safety case when home is within `125`
units of nearby enemies; it may choose berserk before reaching refuge
selection. This is already inside Call to Grave's `500`-unit no-cast radius.

The effect creates one attached effector for the full action duration, waits
until the midpoint, then uses the stock point-target or unit-target teleport
path with the Phantom's current destination, target, and casting range. The
movement call receives the custom range `50000`, which is effectively
map-spanning while remaining within values already used safely by stock game
scripts. Because the effect remains attached to the caster, the same portal
animation begins at departure and finishes at the arrival point.

The portal now preserves Wizard Teleport's native three-set overlay structure
instead of mapping a six-frame Frost Field hit loop over the full effect
duration. Eight frames open the rift, eight identical full-width frames hold it
open without rotation or cycling, and seven frames close it. The shared fully
open transition leaves `22` unique custom TILEs. Every phase uses the same
`84x116` canvas and `(42,31)` hotspot, preventing the inherited Frost Field
anchors from moving the portal left and right between frames. The generated
art sources are:

```text
assets\source\call-to-grave-portal-source-v1-chroma.png
assets\source\call-to-grave-portal-source-v1-transparent.png
```

Decode the actual packaged palette animation with:

```powershell
.\scripts\create_call_to_grave_review.py
```

This writes:

```text
artifacts\reviews\call-to-grave-portal-packaged-review.png
```

#### Call to Grave implementation postmortem

The first implementation tried to build a separate recall system around the
desired outcome. It introduced custom return-home detection and movement
helpers, intercepted `use_building` / `use_building_safe`, and attempted to
teleport directly to home from custom callbacks. That design did not produce a
working spell because it bypassed the stock travel action's selection,
validation, target state, animation timing, and midpoint movement lifecycle.
Its range behavior was also inferred from constant names before tracing
`main_teleport_check`, which silently divides its supplied value by five.

The completed implementation started again from the closest proven stock
feature: Wizard Teleport. It preserved the native action type, spell rank,
effector duration, midpoint movement thread, point/unit target handling, and
ordinary `TryTravelSpell` selection. Changes were then made one dimension at a
time:

1. Replace only the portal art while retaining the three native animation
   phases and fixed hotspot.
2. Give the movement thread a map-spanning range.
3. Add a direct, explicitly understood minimum-distance check.
4. Gate spell validation on the canonical stock home state,
   `TaskName == "go_home"` and `Target == Home`.
5. Change only the Phantom's refuge choice at the narrow stock
   `flee_part_II` boundary, preserving the complete stock fallback for every
   other hero and for a Phantom without a valid home.

The reusable rule is to trace a comparable stock behavior from decision
through action completion before inventing hooks. Begin with that action
unchanged, prove it works, and alter one contract at a time. Prefer a
validation callback for eligibility and the narrowest existing decision
boundary for class-specific behavior. Read helper bodies before interpreting
their constants, preserve native animation timing and anchors, and add build
validation that rejects temporary learning bypasses and obsolete broad
overrides. This is the default implementation approach for future custom
spells and hero behaviors.

### Eternal Soul

Eternal Soul follows the stock Shield of Light action and effector lifecycle.
It is an Attack-type self-buff selected by the ordinary combat spell path,
lasts `25000` milliseconds, and has a `30000`-millisecond cooldown. It is
learned at its production level 6 and retains Shield of Light's proven action
and effector lifecycle,
but its visuals are custom: a ghostly cyan-blue ice flame grows around the
Phantom, pulses, and fades in a six-frame one-shot cast effect. A compact
29-frame version of the same flame gently pulses as the persistent status
icon. Both are built from
`assets/source/eternal-soul-icy-flame-source-v1-transparent.png`.
The cast tiles share one fixed `103x99` canvas and use a translated hotspot
to center the growing flame over the Phantom instead of inheriting Frost
Field's southeast-biased target placement.

While active it grants `+15` Parry and `+15` Magic Resistance through
`MagicalAdjustAttribute`. It also stores and grants 30 percent of the
Phantom's current Max HP. Current HP is scaled by the same ratio on application
and removal, so a full `100/100` Phantom becomes `130/130`, while an injured
Phantom keeps approximately the same health percentage. This avoids turning
the temporary health ceiling into permanent healing after repeated casts.
The exact stored Max HP delta is removed on expiry, preserving unrelated level
or item gains that occur while the buff is active.

Chill remains one shared, non-stacking target state. Each application records
only an integer tier; it does not attach a dynamic caster-agent reference to
stock enemy units. An Eternal Soul caster applies tier 2 Chill, doubling the
fixed movement and action modifiers from `50/500` to `100/1000`. An empowered
hit upgrades and refreshes a normal Chill in place without creating a second
icon. A normal hit cannot overwrite or extend an active empowered Chill. Tier
2 expires through the same three-second watcher as ordinary Chill, after which
a normal hit can apply tier 1 again. Expiry reverses only the active tier's
exact modifier values.

All persistent visible status symbols use `StackPriority=1`, including the
Frost Armor crystal, Eternal Soul, Chill, and Gravechill. This places them in
Majesty's shared status-effect layout alongside stock buffs and debuffs rather
than letting the Frost Armor ward occupy the same non-stacking world-effect
anchor as the first status icon. One-shot cast and impact visuals retain
`StackPriority=0`.

After a build, decode the actual packaged Eternal Soul frames with:

```powershell
..\.tools\python.cmd .\scripts\create_eternal_soul_review.py
```

The review is written to
`artifacts/reviews/eternal-soul-packaged-review.png`.

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

At level 3, the same Phantom-owned watcher grants a visible `Frost Armor`
special item once. Its item-presence guard is the persistent-state marker, and
the grant applies `+10` basic-damage armor through the same ordinary
`AdjustAttribute` path proven by Frozen Cowl and the stock Ring of Protection.
This makes the bonus visible in the Items panel and included in Majesty's
displayed armor total. The first-pass item icon deliberately reuses Frozen
Cowl's armor icon. It is intrinsic class gear rather than loot and is included
in Phantom death cleanup.

Separately, the active one-hit ward adds both `10000` basic-damage armor and
`10000` magical-armor bonus. The first value zeroes a normal weapon attack;
the second zeroes Majesty's ordinary `spell_attack` damage path, which subtracts
twice the defender's magical-armor bonus after the Magic Resistance roll.
Consuming the ward—or dying while it is active—removes both temporary
adjustments as a matched pair; the persistent item-backed `+10` basic armor
remains. Direct scripted HP loss that bypasses both `damage` and `spelldamage`
is outside this protection.

The Phantom's existing `Hostiles` list acts as the local attack-attempt signal:
the ward clears that list when cast, then its recurring watcher consumes the
ward when the first valid attacker appears. Majesty's
`react(attacker, target)` adds the attacker just before the hit roll, but other
AI paths can leave broader combat relationships in the same list. The watcher
therefore also requires that the reported hostile currently targets the
Phantom and is within its own maximum attack range (plus a small 24-unit
movement/geometry tolerance). Nonqualifying entries are cleared so a later
real attack can report itself again. This prevents the Phantom's first attack
against a distant melee target from consuming the ward. The local filter
avoids modifying global attack/damage functions and requires no changes to
enemy definitions. It intentionally reacts to the first qualified attack
attempt, even when the engine's hit roll would otherwise miss.

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

The Priestess scaffold has eight populated direction records in every primary
animation set, not six. The production art supplies four approved/generated
3x2 major-action sheets—front, front-right, rear-right, and back—plus mirrored
front-left and rear-left views. Exact side-on paintings do not yet exist, so
the nearest three-quarter view is deliberately shared by each adjacent side
slot. The eight engine slots therefore use:

`back, rear-right, rear-right, front-right, front, front-left, rear-left, rear-left`.

That identical mapping is applied independently to Stand, Walk, Attack, Cast,
Special, and Die. No action borrows another direction's pose, so its recovery
and completion cannot flip to a differently facing art view.

The stock source TILE ranges are exact and must not drift by one:
Walk `4586-4649`, Stand `4650-4657`, Special `4658-4689`, Attack
`4690-4721`, directional Die `4722-4745`, Cast `4746-4777`, and shared
dissolve `4778-4785`. The earlier six-direction implementation misclassified
the first Special and Die tiles as the preceding set and left the last two
engine directions clamped to one art view.

Walk directions occupy eight-TILE blocks beginning at tile 4586. The first
TILE in each block is a header/base pose that the engine periodically displays;
the following seven are the normal Walk sequence. Direction assignment must
therefore use `(tile - 4586) // 8`, including all eight base tiles from 4586
through 4642 in steps of eight. Starting at 4587 assigns every later base pose
to the previous direction and causes a recurring one-frame facing flip in-game.

The stock Priestess Walk and Cast canvases vary substantially by direction;
several side and rear-side records are shorter than the approved Phantom Stand
art and clip an attempted scale increase. Generated Walk and Cast bodies are
therefore normalized to the packaged Stand height for their own direction:
`61, 55, 52, 50, 50, 56, 60, 61` pixels. When a native action canvas is too
small, the builder expands it upward and translates the hotspot by the same
amount, preserving world position and robe baseline. Validators allow at most
one pixel of palette-rounding drift and reject action art touching the expanded
canvas boundary.

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
- Spell mechanics and visual effects are complete, but spell audio still uses
  stock or placeholder sounds pending the final dedicated audio pass.
- The Phantoms Haunt borrows the stock Elf recruit dialog. This keeps the mod
  Workshop-only, but the Elven Bungalow shares the overridden AP07 dialog art
  while the mod is active.
- The Phantoms Haunt is still a proof of concept rather than a balanced finished
  content mod.

## Spell Completion Checkpoint

Final spell checkpoint recorded July 27, 2026:

- The building, construction progression, destruction progression, cast
  shadows, shadow seams, and construction pit cleanup are working in game.
- The generated and decoded-CAM validators now reject mixed shadow/body RLE
  runs, missing seams, bounded transparent construction pits, and transparent
  islands enclosed entirely by shadow controls.
- The directional Phantom hero, floating movement, action frames, corrected
  direction mapping, projected detached shadows, movement speed, death and
  dark-ice gravestone sequence, and staff-centered cyan snowflake cast effect
  are approved for the current build.
- Cast body geometry and recovery poses are locked directionally across all
  eight Cast records; validators reject the old Priestess swirl, mismatched
  recovery direction, clipping, and frame-size drift. Walk and Cast now also
  match each direction's approved Stand height within one pixel, using
  hotspot-preserving upward canvas expansion where stock Priestess action
  records were too short.
- Phantom retreat and combat estimates are temporarily set to a fearless
  testing profile so spell behavior can be exercised without frequent retreat.
  Threat selection now uses stock `eval_enemies_nearby`, so Phantoms no longer
  inherit the Wizard's unconditional fear of targets above `60` Magic
  Resistance or targets protected by Magic Mirror. Stock
  `spell_extra_value` retains all eight stock weights and adds Phantom-only
  confidence for learned custom spells: Ice Lance `10`, Frost Armor `10`, Icy
  Touch `25`, Call to Grave `10`, Eternal Soul `25`, and Endless Winter `30`.
  Eternal Soul now learns at its finalized level 6; its availability check
  contributes `25` to recognized spell value only after it is learned.
- Ice Lance now has final-path generated-source projectile/icon art, 32 packaged
  directions, `8` damage, `180` conceptual base / `190` Icerod-equipped Phantom
  casting range, native impact animation, and a centralized three-second
  non-stacking movement/action Chill with an approved animated cyan snowflake
  indicator.
- Ice Lance has passed the current in-game art, direction, impact, damage,
  refresh, non-stacking, movement-slow, action-slow, duration, and status-icon
  review. The fixed modifiers deliberately describe a mild Chill rather than
  promising an exact percentage on every unit.
- Icy Touch is level 4, rank 3, and uses a 5-second cooldown with the
  Phantom's scale-stable directional attack animation and a persistent animated
  cyan Gravechill skull. Its single monster-style action callback re-reads the
  scheduler-selected current target, resolves one complete stock `$make_attack`
  weapon strike, then directly invokes `$spell_attack(..., 30)` and refreshes
  the established three-second non-stacking Chill. In that same callback it
  directly creates and applies a refreshable, non-stacking eight-second
  `-5 Strength` / `-2 Defence` / `-2 Resistance` Gravechill debuff, following
  the stock Medusa Slow path. A separate six-frame PHg2 skull
  formation-and-shatter overlay plays once on each successful application.
  Its stock-style validation callback makes
  it available only when that specific unit target is within the fixed
  24-unit melee radius, allowing Ice Lance to remain selected at range without
  making the Phantom move closer for Icy Touch.
- Call to Grave is a level-5 spell using stock Wizard Teleport travel
  behavior: rank 4, an effectively map-wide
  `50000` movement range, `5000` ms cooldown, an explicit `500`-unit
  minimum-use threshold matching a teleportation amulet's full range, a
  validation gate requiring stock `TaskName == "go_home"` and `Target == Home`,
  and stock midpoint point/unit movement. A Phantom-only branch in the
  stock-compatible `flee_part_II` refuge selector makes terror fleeing choose
  home; all non-Phantom refuge selection remains stock.
  Its custom portal uses Wizard Teleport's native
  eight-frame open, eight-frame hold, and seven-frame close sets with one fixed
  hotspot; only the name and ghostly ice artwork differ.
- Eternal Soul is finalized at level 6/rank 5. It follows Shield of Light's
  stock combat self-buff selection and grants `+15` Parry, `+15` Magic
  Resistance, and a proportional 30-percent temporary Max HP increase for
  `25000` ms on a `30000`-ms cooldown. While active, the caster applies the
  mutually exclusive tier-2 empowered Chill. The spell contributes `25` to
  `spell_extra_value` once learned. Its custom six-frame ghostly ice flame and
  29-frame pulsing status icon are approved in game, stack with other status
  symbols, and use the corrected caster-centered hotspot.
- Endless Winter is finalized at level 7/rank 7 with a 55-second cooldown and
  21-second lifetime. It casts on the closest eligible enemy unit, preserves
  the Phantom's current combat target as the winner of an exact closest-distance
  tie, and tracks the original target at 25-ms visual cadence while pulsing
  damage every 1600 ms. The storm uses a 175-unit radius with center-distance
  tiers of `8` damage plus empowered Chill through 24 units, `6` plus normal
  Chill through 80, and `4` plus normal Chill through 175. Three visually
  identical projectile definitions carry those fixed tiers safely into their
  impact callbacks. Explicit cleanup terminates both threads and deletes the
  invisible anchor after the visible storm expires.
- Frozen Cowl displays and grants `+2` physical armor. Black Icerod displays
  and grants `+8` weapon damage, `+5` Parry, and `+10` casting range. Their
  Blacksmith/Wizard Guild upgrade variants, stat mutations, names, tooltips,
  death cleanup, and realm-exit cleanup use the verified stock-compatible
  paths.
- Phantom base weapon damage remains `0`, while Strength `8` keeps stock
  `hero_damage` above zero before the Icerod's `+8` weapon damage is applied.
  This avoids the target-evaluation divide-by-zero crash.
- Frost Armor is finalized at level 3 with persistent `+10` physical armor,
  a visible class-effect item, a one-hit physical/magical ward, three-second
  retaliatory Freeze against unit attackers, and full-rest recharge at a
  Phantoms Haunt, Inn, or Gazebo.
- Ordinary Healers, healing potions, and player healing spells do not heal
  Phantoms. Priestess undead healing is the intentional exception and
  prioritizes the Priestess, then injured Phantoms, then other undead minions.
- The Phantom-only stock `Potion_Check` replacement prevents healing-potion
  purchases without trapping the hero's shopping decision or blocking other
  items.
- The remaining spell-suite task is audio only; mechanics, progression,
  targeting, debuffs, custom status art, cast/impact art, and package
  validation are complete.

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

The generated manifest exposes one selectable mod with a single
`<Dataset base="Any">`. This is intentional: the same package loads in both
Original Majesty and Northern Expansion quests. Do not represent compatibility
as sibling `Majesty` and `MajestyExpansion` datasets inside one mod entry; the
game recognizes only the first sibling and silently excludes the other mode.
The post-build validator enforces the universal single-dataset layout.

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
