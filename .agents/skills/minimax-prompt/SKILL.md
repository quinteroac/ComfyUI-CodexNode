---
name: minimax-prompt
description: Generate structured Minimax video prompts for T2VA, I2VA, FL2VA, and L2VA from text and optional reference-image instructions.
---

# Minimax Prompt Generation

Generate only the complete final prompt unless the user explicitly requests explanation.

## 1. Determine the mode

- **T2VA**: Generate the full audiovisual timeline from text; do not add an image-alignment instruction.
- **I2VA**: Start from the referenced first frame and develop the action forward.
- **FL2VA**: Connect the referenced first and last frames through a continuous visual path.
- **L2VA**: Infer a plausible preceding state and converge on the referenced final frame.

Use the user’s specified mode. If it is unclear, ask which mode applies.

## 2. Required output structure

The final prompt contains these fields in this order:

```text
integrated_multimodal_description: [Shot 1] ...

overall_soundscape: ...

non_diegetic_music: ...
```

For I2VA, FL2VA, and L2VA, place the alignment instruction on the first line, followed by one blank line. T2VA begins directly with `integrated_multimodal_description`.

### I2VA alignment

```text
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.
```

### FL2VA alignment

```text
How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot N) aligns with the S.SS-second mark of the target video.
```

Use the actual final shot index for `N` and the effective duration formatted to exactly two decimal places for `S.SS`.

### L2VA alignment

```text
How the reference pictures align with the target video — <Picture 1> (from [Shot N]) aligns with the S.SS-second mark of the target video.
```

Use the actual final shot index for `N` and the effective duration formatted to exactly two decimal places for `S.SS`.

## 3. Integrated multimodal description

Write the main timeline as visible and audible events. Include:

- visual style and initial composition;
- subjects, appearance, clothing, positions, props, and spatial relationships;
- actions, reactions, camera movement, shot changes, and scene transitions;
- dialogue, singing, voiceover, on-screen text, and synchronized diegetic sound.

At the beginning of `[Shot 1]`, state the overall style and composition. Common styles include `Cinematic`, `live-action`, `2D-animated`, `3D CG`, `claymation`, `watercolor`, and `vintage film`.

Example:

```text
integrated_multimodal_description: [Shot 1] Live-action, cinematic, a medium-wide shot frames...
```

For keyframe tasks, derive style, subject identity, composition, colors, objects, and spatial relationships from the reference image. Preserve those anchors while describing motion.

### Keyframe progression

- **I2VA**: first-frame anchor → action onset → continuous development → result or reaction.
- **FL2VA**: first-frame state → observable intermediate changes → progressively narrowing differences → last-frame state.
- **L2VA**: plausible preceding state → explicit transition path → gradual convergence in the final shot → exact last-frame landing.

For FL2VA, generally use one continuous shot unless the user explicitly specifies multiple shots. The final `[Shot N]` must reach the last frame at the end of the video.

## 4. Shots and cuts

Do not timestamp `[Shot 1]`. Later shots must use sequential shot numbers and strictly increasing cut times within the video duration:

```text
[Shot 2] At 00:03.500, the camera cuts to...
```

Use natural cut language such as:

- `the camera cuts to`;
- `the shot cuts to`;
- `the shot transitions to`;
- `the shot changes to`;
- `the shot switches to`.

Use cross-dissolve, fade, or wipe only when explicitly requested.

A cut must introduce meaningful new information about the subject, space, state, viewpoint, or time. If only framing distance or a slight angle changes, use camera motion instead.

## 5. Camera motion

Express camera movement naturally inside the shot. Motion may include:

- `Zoom In / Zoom Out`;
- `Push In / Pull Out`;
- `Pan Left / Pan Right`;
- `Truck Left / Truck Right`;
- `Tilt Up / Tilt Down`;
- `Pedestal Up / Pedestal Down`;
- `Arc Shot`;
- `Tracking Shot`;
- `Static Shot`;
- `Shake Slightly / Shake Strongly`;
- `POV`;
- `Roll Clockwise / Roll Counterclockwise`.

Add amplitude only when meaningful:

- `with small amplitude`;
- `with large amplitude`.

Add speed only when meaningful:

- `at slow speed`;
- `at fast speed`.

Usually omit medium amplitude and normal speed.

Example:

```text
The camera pushes in with small amplitude at slow speed toward the folded letter in her hands.
```

## 6. Speakers, dialogue, and singing

Assign stable IDs such as `(S1)` and `(S2)` to subjects who speak, sing, or produce an off-screen human voice. Use compound IDs such as `(S1,S2)` when already-numbered speakers vocalize together. Do not assign IDs to silent characters.

When a speaker first appears, establish enough identity to keep the voice stable, such as character type, age, gender, on-screen/off-screen status, pitch, timbre, speaking rate, or accent.

Place the speaker identity, ID, action, and delivery outside `<d>`. Inside `<d>`, include only the language tag and exact user-provided spoken or sung content.

Preserve every original word and punctuation mark verbatim. Do not translate or rewrite dialogue or lyrics.

```text
The young woman with a quiet, breathy voice (S1) says: <d>[English] I get off at the next station.</d>
```

For simultaneous speech:

```text
The two children (S1,S2) shout together, <d>[English] Wait for us!</d>
```

For voiceover, use the exact phrase `says in an off-screen voiceover` and immediately state that the corresponding on-screen character’s lips remain closed:

```text
The man (S1) says in an off-screen voiceover: <d>[English] I still remember that road.</d> while his lips remain completely closed.
```

If dialogue or lyrics cross a cut, use `<scenetrans>` at the connecting points in both parts and explicitly state that the audio continues across the cut. Use `<cutoff>` when speech is truncated by the end of the video.

Use continuity phrases such as:

- `continues seamlessly across the cut`;
- `continues uninterrupted into the next shot`;
- `carries over from the previous shot`;
- `remains audible across the transition`.

## 7. On-screen text

Put visible banners, signs, labels, subtitles, and neon text in English double quotation marks. Preserve the original text and punctuation verbatim without translation.

```text
A red neon sign reading "营业中" glows above the doorway.
```

## 8. Overall soundscape

Write `overall_soundscape` as one continuous paragraph of 1–4 English sentences. Summarize ambient sound, physical action sounds, and non-verbal human sounds across the full video, including wind, rain, traffic, footsteps, fabric movement, impacts, breathing, laughter, or panting.

Do not repeat dialogue, singing, or diegetic music here; those belong in the multimodal description.

Use `N/A` only when the user explicitly requests complete silence throughout the video.

```text
overall_soundscape: Steady rain taps against the café windows while low room ambience continues underneath. The entrance bell rings once, followed by wet footsteps and the soft scrape of a chair.
```

## 9. Non-diegetic music

Write `non_diegetic_music` as 1–3 English sentences describing music audible only to the audience. Specify instrumentation, tempo, rhythm, and dynamic changes.

Do not use abstract mood words or explain the emotional function of the score. Music, singing, instruments, radio, television, or phone audio audible to characters are diegetic and belong in the multimodal description.

Use `N/A` when there is no non-diegetic music.

```text
non_diegetic_music: Sparse piano notes at a slow tempo, joined by sustained low strings that gradually increase in volume before fading out.
```

## 10. Final validation

Before returning the prompt, verify that:

- the mode-specific alignment instruction is correct and first when required;
- the alignment duration has exactly two decimal places;
- shot numbers are sequential;
- only shots after `[Shot 1]` have cut timestamps;
- cut timestamps strictly increase and remain within the duration;
- the three fields appear in the required order;
- keyframe identity, composition, object states, and spatial relationships remain consistent;
- dialogue and visible text are preserved verbatim;
- speaker IDs remain stable;
- voiceover uses the required wording and closed-lips instruction;
- soundscape and non-diegetic music are not incorrectly duplicated in the multimodal description;
- no extra commentary surrounds the final prompt.
