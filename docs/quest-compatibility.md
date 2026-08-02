# Quest Compatibility

Custom Guild: Phantoms Haunt loads through `Dataset base="Any"` and is designed
for both Original Majesty and the Northern Expansion.

## Availability

The Haunt uses Majesty's native `DATA/BDEP` building dependency table. Its
stock-shaped four-character building ID, `PHG1`, has the same Palace condition
as the Wizard Guild and level-2 temple guilds:

```text
PHG1 : ABJ2 ABJ3 NOT NOT ||
```

The engine therefore hides the Haunt at Palace level 1 and exposes it at level
2 or 3 before any construction order exists. There is no placement deletion,
refund, Palace polling thread, or Palace lifecycle override.

Majesty resolves `DATA/BDEP` as one whole CAM resource; it does not merge
individual dependency lines supplied by different mods. A second mod that also
provides BDEP therefore needs a combined compatibility record. This affects only
mods that replace the building dependency table, not ordinary content mods.

Confirmed in game on 2026-08-01: A Deal with a Demon hides the Haunt at Palace
level 1, exposes it immediately after the Palace reaches level 2, and peasants
construct it normally. Rise of the Rat King exposes it from its starting
level-2 Palace.

## Dark Forest

Dark Forest uses the quest's literal stock guild progression. Its `DARK_FOREST`
entry point places `$DisableUnitType("Phantoms_Haunt")` directly beside the
stock guild, temple, and non-human settlement locks. When the Temple to Fervus
is discovered, `dark_forest_victory` places the matching
`$EnableUnitType("Phantoms_Haunt")` directly in the same stock unlock list.
There is no polling thread, helper indirection, registration replay, or
construction interception.

After the stock unlock, the ordinary BDEP Palace requirement still applies, so
the Haunt appears only at Palace level 2 or 3. Confirmed in game on 2026-08-01:
the Haunt remains unavailable before the Fervus event and becomes normally
buildable afterward under the same quest transition that restores stock guilds,
temples, and Elven availability.

The Haunt is treated as a temple-tier arcane guild when matching stock quest
restrictions. Restrictions aimed only at non-human settlements do not exclude
it.

## Unique identities

The mod uses namespaced description, image, tile, action, unit, sound, WAVE,
text, item, and GPL identities. It does not replace the Wizard Guild, Wizard,
Priestess, or their spell art.

The few intentionally shared stock entry points retain their complete stock
behavior and add narrowly scoped Phantom handling.

## Embassy and Outpost

The stock random-hero route remains in place. Phantom is added as an eligible
result for Embassies and Outposts.

Paladin eligibility follows the same Haunt exclusivity rule used by ordinary
recruitment:

- without a placed Haunt, Paladins remain eligible;
- while a Haunt foundation or completed Haunt exists, Paladins are omitted;
- Phantom remains eligible through the ordinary and quest-special fallback
  routes.

## Palace and quest startup

The mod does not override Palace birth or upgrade callbacks. Palace-level
availability never calls `DisableUnitType` or `EnableUnitType`; it is evaluated
by `BDEP`, just like stock guild dependencies. Quest scripts that deliberately
forbid a class of buildings continue to use Majesty's ordinary unit-type
restriction calls through shared lock/unlock helpers.

## Priestess and Paladin interactions

Priestess behavior keeps the complete Northern Expansion decision order and
adds the Phantom-specific support opportunity at the stock support point.
Phantoms are treated as undead for the Haunt-enhanced Drain Life interaction.

Placing a Haunt disables future Paladin recruitment. Completing a Haunt
dismisses living player-owned Paladins through the game's ordinary dismissal
route. Destroying the final Haunt restores future recruitment.

## Validation

The release validator checks:

- `Dataset base="Any"` packaging;
- unique custom identities;
- native `BDEP` Palace-level gating and preservation of the stock table;
- documentation of the whole-record BDEP compatibility requirement;
- Embassy and Outpost selection;
- Paladin exclusion and restoration;
- Priestess support routing;
- Original and Northern Expansion quest aliases used by the mod.

No quest-specific files are shipped in the package.
