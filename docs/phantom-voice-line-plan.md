# Phantom Voice Line Plan

The initial recruitment line uses a dedicated custom route. After
`hero_birth` establishes the Phantom's home, a Phantom born from a
`Phantoms_Haunt` makes exactly one 20-percent roll. A successful roll schedules
`Phantom_Hired` / `Begin` after 250 ms. The per-agent function attribute
prevents repeated birth callbacks from rolling or playing twice.

Majesty has no class-specific recruitment voice phase. Its stock
`Basic_idle` action requests `VFX_SPECIAL1`; the Phantom now uses that phase
for its separate idle/personality line.

The runtime recruitment sound identity is `PH01` / `Phantom_Hired`, registered
through `phantom_sounddesc.cam`. The builder derives its one-phase `DSND`
record from the CAM-tool research's proven `RM01Rage_of_Krolm` template and
maps `Begin` (`EBE0`) to the `PHS1` WAVE through stock voice group `SG14`.

## Initial Audio Validation Baseline

Status: **initial audio valid**, verified in-game on July 30, 2026 in the
Northern Expansion quest Rise of the Ratmen.

- Human take 4 is preserved as
  `assets/audio/phantom-recruitment-clean.wav`.
- Reproducible `v6-game-loud` processing produces
  `assets/audio/phantom-recruitment-game.wav`.
- The output is mono, 22050 Hz, signed 16-bit integer PCM.
- `phantom_voices.cam` stores the WAV as WAVE key `PHS1`.
- `phantom_sounddesc.cam` registers unique runtime sound
  `PH01` / `Phantom_Hired`; loose sound XML alone was insufficient for the
  GPL-callable runtime path.
- The DSND is a size-preserving transformation of the CAM-tool research's
  proven `RM01Rage_of_Krolm` template.
- The mod manifest loads both CAMs for `Dataset base="Any"`, covering Original
  and Expansion datasets.
- Audio-only releases regenerate the processed WAV, voice CAM, DSND CAM, sound
  and unit metadata, and the manifest without rebuilding art archives.
- The full Phantom voice descriptor is a stock-shaped clone registered as
  `PV01` / `Phantom_Voice`; its stock event phases and cooldown groups point
  to the corresponding Phantom WAVE keys.

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

## Pinned Processing Recipe

The provisional human-voice treatment is pinned in
`scripts/process_phantom_voice.py`. The current `v6-game-loud` recipe uses:

- a roughly 1.8-semitone main pitch reduction;
- a close, four-semitone-lower spectral double at 25 percent strength;
- a 4 ms double offset so it reads as overtones rather than an echo;
- five dense, quiet reflections from 18 through 96 ms;
- an intermediate peak normalization of -6 dB;
- 3.5x makeup gain through a smooth -1 dB ceiling limiter, matching the louder
  perceived level of Majesty's stock voices; and
- mono, 22050 Hz, signed 16-bit PCM WAV output.

The approved recruitment take is processed to
`assets/audio/phantom-recruitment-game.wav` and packed as WAVE
key `PHS1`. Keep the clean master in
`assets/audio/phantom-recruitment-clean.wav` so the recipe can
be revised without returning to the Audacity project.

## Approved Lines

| Event | Sound phase / route | Approved line |
|---|---|---|
| Recruitment (initial validated line) | 20% Haunt birth roll → `Phantom_Hired` / `Begin` | “Oh, back again?” |
| Deciding | `VFX_DECIDING` | “The dead have time.” |
| Sees a hostile | `VFX_SEE_HOSTILE` | “Your breath beckons me.” |
| Commits to combat | `VFX_GO_COMBAT` | “Join us in death.” |
| Flees combat | `VFX_FLEE_COMBAT` | “Death may only be delayed.” |
| Pursues a reward flag | `VFX_GO_REWARD` | “Even the dead have debts.” |
| Finds an item | `VFX_FIND_COOL` | “A garnish for my grave.” |
| Casts a spell | `VFX_CAST_SPELL1` | “Tempus mori!” |
| Idle / personality | `VFX_SPECIAL1` | “Do I have time for a snow cone?” |
| Gains a level | `VFX_GAIN_LEVEL` | “The cold grows harsher still.” |
| Reaches level 10 | `VFX_LEVEL_10` | “The secrets of the veil are now mine.” |
| Dies | `Death` | “Not… again…” |
| Easter egg | `Easter_Egg` | “I wasn’t napping. I’m just dead.” |

## Trigger Note

Stock voice packs describe `VFX_SPECIAL1` as an idle/personality line, and the
stock `Basic_idle` action triggers it naturally. Do not bind recruitment audio
to that phase. “Oh, back again?” belongs only to the custom 20-percent
recruitment route; idle and deciding use their separate stock phases.

## Production Status

All approved lines have canonical event-named Audacity projects, clean
masters, processed game WAVs, and packaged WAVE entries. Recruitment is
already validated in game. The remaining recorded lines are packaged and
awaiting in-game event validation. The deliberate pause in “Not… again…” is
preserved as part of the single Death take.
