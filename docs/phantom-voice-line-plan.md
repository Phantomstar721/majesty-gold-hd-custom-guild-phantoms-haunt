# Phantom Voice Line Plan

## Voice Direction

The Phantom should sound like a restrained, melancholy revenant who continues
adventuring largely for their own amusement. The performance should be weary,
intimate, and quietly entertained rather than growling, theatrical, or
generically monstrous.

- Use a medium-low human voice with clear diction.
- Deliver menace calmly rather than by shouting.
- Treat death as tiresome and familiar, not frightening.
- Deliver jokes completely deadpan.
- If post-processing is used, keep any spectral double subtle enough that the
  words remain as intelligible as stock Majesty hero lines.

The first synthetic-voice sample pass was rejected. Future production should
use a directed human recording.

## Approved Lines

| Event | Sound phase / route | Approved line |
|---|---|---|
| Recruitment | Explicit Phantom birth sound | “Oh, back again?” |
| Deciding | `VFX_DECIDING` | “The dead have time.” |
| Sees a hostile | `VFX_SEE_HOSTILE` | “Your breath beckons me.” |
| Commits to combat | `VFX_GO_COMBAT` | “Join us in death.” |
| Flees combat | `VFX_FLEE_COMBAT` | “Death may only be delayed.” |
| Pursues a reward flag | `VFX_GO_REWARD` | “Even the dead have debts.” |
| Finds an item | `VFX_FIND_COOL` | “A garnish for my grave.” |
| Casts a spell | `VFX_CAST_SPELL1` | “Tempus mori!” |
| Rare idle joke | Custom explicit idle route, if added | “Do I have time for a snow cone?” |
| Gains a level | `VFX_GAIN_LEVEL` | “The cold grows harsher still.” |
| Reaches level 10 | `VFX_LEVEL_10` | “The secrets of the veil are now mine.” |
| Dies | `Death` | “Not… again…” |
| Easter egg | `Easter_Egg` | “I wasn’t napping. I’m just dead.” |

## Trigger Note

Stock voice packs describe `VFX_SPECIAL1` as an idle/personality line, but the
current Phantom implementation explicitly plays that phase at birth. Bind
`VFX_SPECIAL1` to the recruitment line unless and until recruitment receives a
different custom phase. Do not bind the snow-cone joke to `VFX_SPECIAL1`, or it
will play for every recruited Phantom. The joke should remain unused until a
genuinely occasional idle route is proven.

