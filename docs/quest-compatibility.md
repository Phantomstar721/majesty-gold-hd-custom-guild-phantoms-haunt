# Quest Compatibility

The Phantoms Haunt is treated as a temple-tier arcane guild when matching stock
quest restrictions. A restriction against non-human settlements alone does not
exclude it.

## Embassy and Outpost

The stock `Random_Hero_Type` route is retained. Embassy, Outpost, and the
Friendly Heroes special event can select Phantoms. When a player has placed a
Haunt, Paladins are removed from the random pool and Phantoms remain available.
The Mausoleum uses a separate stock pool and is unchanged.

## Restricted Original Quests

- The Barren Waste
- The Bell, the Book, and the Candle
- The Dark Forest, until the stock Temple to Fervus restoration event
- The Day of Reckoning
- Slay the Mighty Dragon
- The Forsaken Land
- Vengeance of the Liche Queen
- Rescue the Prince
- The Wizard's Curse

Slay the Mighty Dragon seeds one foreign Phantoms Haunt before the stock
rescue-building setup runs. It cannot be constructed, but can be found and
recovered like the quest's Warriors, Rogues, Wizards, Agrela, Lunord, and Dwarf
buildings.

## Restricted Expansion Quests

- Vigil for a Fallen Hero

The Siege intentionally allows the Haunt: Phantoms do not fill the Wizard's
building-demolition role that the quest removes.

## Balance of Twilight

Balance of Twilight is a separately packaged downloadable quest. Its editable
GPL source is not included in the SDK; it loads the closed
`XQD1_Bytecode.bcd`. The quest does not expose ordinary guild restrictions in
that bytecode, so the Haunt remains available.

The quest's enemy Black Phantoms define generic `Phantom_Birth` and
`Phantom_Death` functions. Our hero uses the unique
`Phantom_Hero_Birth` and `Phantom_Hero_Death` names to avoid overriding those
quest functions.
