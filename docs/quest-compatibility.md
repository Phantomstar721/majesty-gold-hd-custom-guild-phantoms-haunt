# Quest Compatibility

Custom Guild: Phantoms Haunt loads through `Dataset base="Any"` and is designed
for both Original Majesty and the Northern Expansion.

## Availability

The Palace owns a lightweight availability watcher. It exposes the Haunt when
the current quest permits its building category and the player's Palace has
reached level 2.

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

The Palace begins the Haunt availability watcher during its birth callback.
The watcher then reevaluates the current Palace level and quest restrictions
without requiring changes to individual quest files.

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
- Palace-level availability behavior;
- Embassy and Outpost selection;
- Paladin exclusion and restoration;
- Priestess support routing;
- Original and Northern Expansion quest aliases used by the mod.

No quest-specific files are shipped in the package.
