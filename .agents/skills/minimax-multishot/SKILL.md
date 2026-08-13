---
name: minimax-multishot
description: Generate reusable Minimax T2VA, I2VA, FL2VA, or L2VA prompts for long videos, with one complete prompt per shot separated by a standalone `---` line.
---

# Minimax Multishot Prompt Generation

Convert the user's story, shot list, script, or visual references into independent Minimax video prompts. Generate exactly one prompt per shot, separating prompts with:

```text
---
```

Do not add commentary, numbering outside the prompts, or explanatory text.

## Prompt format

Each shot prompt must contain these fields in order:

```text
[optional image-alignment instruction]

integrated_multimodal_description: [Shot N] ...

overall_soundscape: ...

non_diegetic_music: ...
```

Use one blank line after the image-alignment instruction and between core fields when appropriate.

## Model modes

Select the mode from the user's request or available references.

### T2VA

Use no image-alignment instruction. Begin directly with the three core fields.

### I2VA

Start every applicable prompt with:

```text
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot N]) is fully referenced.
```

Begin the multimodal description by anchoring the image's style, subjects, composition, clothing, colors, objects, and spatial relationships. Then describe continuous forward development:

`first-frame anchor → action onset → continuous development → result or reaction`.

### FL2VA

Start with:

```text
How the reference pictures align with the target video — Picture 1 (from [Shot N]) aligns with the 0.00-second mark of the target video; Picture 2 (from [Shot N]) aligns with the D.DD-second mark of the target video.
```

Describe the observable path from the first frame to the last frame rather than two static descriptions:

`first-frame state → intermediate changes → progressively narrowing differences → last-frame state`.

Ensure the final action reaches the last-frame composition exactly. Prefer a single continuous shot unless multiple shots are explicitly requested.

### L2VA

Start with:

```text
How the reference pictures align with the target video — <Picture 1> (from [Shot N]) aligns with the D.DD-second mark of the target video.
```

`N` must be the actual final shot, and `D.DD` must be the effective video duration formatted to exactly two decimal places. Infer a plausible opening state, then describe a continuous path that gradually converges on the reference image:

`plausible preceding state → explicit transition → gradual convergence → final-frame landing`.

## Integrated multimodal description

This is the main visual and audible timeline. At the beginning of each shot, establish the visual style and composition, such as cinematic live-action, 2D animation, 3D CG, claymation, watercolor, or vintage film.

Use:

```text
[Shot 1] Live-action, cinematic, ...
```

For later shots, include a strictly increasing cut time within the total duration:

```text
[Shot 2] At 00:03.500, the camera cuts to ...
```

A cut must introduce new information about the subject, space, state, viewpoint, or time. Use camera motion instead of cutting for minor changes in distance or angle. Use cross-dissolves, fades, or wipes only when explicitly requested.

Describe actions in chronological order and maintain continuity of identities, clothing, props, lighting, positions, and object states across shots.

## Camera motion

Write camera movement as natural English and include amplitude or speed only when meaningful. Available expressions include:

- Zoom In / Zoom Out
- Push In / Pull Out
- Pan Left / Pan Right
- Truck Left / Truck Right
- Tilt Up / Tilt Down
- Pedestal Up / Pedestal Down
- Arc Shot
- Tracking Shot
- Static Shot
- Shake Slightly / Shake Strongly
- POV
- Roll Clockwise / Roll Counterclockwise

Optional modifiers are `with small amplitude`, `with large amplitude`, `at slow speed`, and `at fast speed`.

Example:

```text
The camera pushes in with small amplitude at slow speed toward the folded letter.
```

## Speakers, dialogue, and singing

Assign stable IDs such as `(S1)` and `(S2)` to every speaking or singing subject. Preserve each speaker's ID across shots. Use compound IDs such as `(S1,S2)` when numbered speakers speak or sing together.

When a speaker first appears, establish their visible identity and vocal traits outside the dialogue block:

```text
The young woman with a quiet, breathy voice (S1) says: <d>[English] I get off at the next station.</d>
```

Inside `<d>`, include only the language tag and the user's exact words and punctuation. Never translate, rewrite, or omit user-provided dialogue or lyrics.

For voiceover, use the exact phrase `says in an off-screen voiceover` and immediately state that the character's lips remain closed:

```text
The man (S1) says in an off-screen voiceover: <d>[English] I still remember that road.</d> while his lips remain completely closed.
```

When dialogue or lyrics cross a cut, use `<scenetrans>` at the connecting points, state that the audio continues across the cut, and use `<cutoff>` when speech is truncated by the video ending.

## On-screen text

Put every visible sign, banner, label, subtitle, or neon message in English double quotation marks. Preserve the original text and punctuation verbatim without translation.

```text
A red neon sign reading "营业中" glows above the doorway.
```

## Sound fields

`overall_soundscape` must be one continuous paragraph of 1–4 English sentences summarizing ambient sounds, physical action sounds, and non-verbal human sounds across the shot or video. Do not repeat dialogue, singing, or diegetic music. Use `N/A` only for explicitly requested complete silence.

`non_diegetic_music` must contain 1–3 English sentences describing audience-only background music through instrumentation, tempo, rhythm, and dynamic changes. Do not describe abstract emotions. Treat singing, radios, televisions, phones, and audible instruments as diegetic events in the multimodal description. Use `N/A` when no non-diegetic music is requested.

## Final validation

Before responding, verify that:

- There is exactly one complete prompt per shot.
- Prompts are separated by a standalone `---` line.
- Every prompt contains the three core fields in the required order.
- Alignment instructions match T2VA, I2VA, FL2VA, or L2VA.
- Shot numbers and cut times are sequential and valid.
- Speaker IDs remain consistent.
- Dialogue and visible text remain verbatim.
- Visual, action, camera, and sound details are temporally consistent.
- L2VA and FL2VA prompts land on their required final references.
