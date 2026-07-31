# Phantom Voice Production

The Phantom voice set uses event-specific human performances processed through
one reproducible revenant treatment. The public `assets/audio` directory
contains only the final game-ready outputs.

## Asset convention

Production used one Audacity project, one clean export, and one processed
output per event:

```text
phantom-<event>-source.aup3
phantom-<event>-clean.wav
phantom-<event>-game.wav
```

The clean master contains the selected performance without effects, and
`scripts/process_phantom_voice.py` creates the game-ready WAV. The raw
`.aup3` projects and clean intermediate WAVs are retained privately; they are
not required to build the public repository.

## Processing contract

The approved treatment applies:

- a roughly 1.8-semitone main pitch reduction;
- a close four-semitone-lower spectral layer at 25 percent strength;
- a 4 ms layer offset;
- five quiet ambience reflections from 18 through 96 ms;
- intermediate peak normalization;
- 3.5x makeup gain through a smooth limiter;
- mono, 22050 Hz, signed 16-bit PCM output.

The close lower layer adds spectral weight without behaving like a separate
echo. The final format matches the stock game's voice archive expectations.

## Runtime routing

The hero uses a stock-shaped multi-event DSND registered as `PV01` /
`Phantom_Voice`. Its phases point to dedicated Phantom WAVE keys for:

- entering and fleeing combat;
- deciding and idle personality;
- pursuing rewards and finding items;
- casting;
- seeing hostiles;
- gaining levels and reaching level 10;
- death and the Easter egg.

Recruitment is intentionally separate. Majesty has no class-specific recruit
phase, so a dedicated `PH01` / `Phantom_Hired` descriptor maps `Begin` to the
recruitment WAVE. The Phantom birth callback makes one 20-percent roll after
the hero receives its Haunt home.

Both DSND entries retain stock voice cooldown groups and spatial behavior.

## Approved lines

| Event | Line |
| --- | --- |
| Recruitment | “Oh, back again?” |
| Deciding | “The dead have time.” |
| Sees a hostile | “Your breath beckons me.” |
| Commits to combat | “Join us in death.” |
| Flees combat | “Death may only be delayed.” |
| Pursues a reward | “Even the dead have debts.” |
| Finds an item | “A garnish for my grave.” |
| Casts a spell | “Tempus mori!” |
| Idle personality | “Do I have time for a snow cone?” |
| Gains a level | “The cold grows harsher still.” |
| Reaches level 10 | “The secrets of the veil are now mine.” |
| Dies | “Not… again…” |
| Easter egg | “I wasn’t napping. I’m just dead.” |

## Incremental packaging

After one complete package exists, the checked-in game-ready WAVs can be
packaged and validated without rebuilding the sprite archives:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Build-CustomGuildPhantomsHaunt.ps1 -AudioOnly
```
