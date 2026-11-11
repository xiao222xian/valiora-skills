# Changelog

## [1.3.1] - 2026-09-25

### Added

- 合并本地未提交改动到上游 1.3.0 之上
- 本地改动：统一展示名为「人人字幕」，保持调用 ID 与能力契约。

## [1.3.0] - 2026-08-24

### Added

- add the shared feedback-classification and approval-invalidation gate used by every LovStudio Skill

## 1.2.11 - 2026-08-11

- Rename the Chinese public display name to “人人字幕” while retaining the stable Skill identifier and English name “Subtitle Freedom”.

## 1.2.10 - 2026-08-10

- Add deterministic glossary coverage reporting for literal matches, applied annotations, unmatched terms, and suppressed terms with reasons.
- Add a CLI regression test covering phrase overlap and per-cue annotation density.

## 1.2.9 - 2026-08-10

- Make the text-watermarked ASS sidecar the default companion to the clean learner SRT.
- Keep character cards and scene cards opt-in, while retaining `--no-watermark` and `--no-watermark-logo` overrides.

## 1.2.8 - 2026-08-10

- Shorten the cinematic rule relative to the text and restore the darker text depth used by the reference composition.

## 1.2.7 - 2026-08-10

- Make the Logo opt-in while retaining the explicit Logo option; align the cinematic rule with the text side so it stays independent from the Logo.

## 1.2.6 - 2026-08-10

- Restore the cinematic horizontal rule above Logo-and-text watermark lockups, keeping the shared center anchor in ASS and raster PGS/SUP output.

## 1.2.5 - 2026-08-10

- Enlarge the default dialogue subtitle style to 58 ASS pixels and reduce the cinematic watermark to 24-pixel text with a 24-pixel source-ratio-preserving Logo.
- Add `--logo-height` to raster PGS/SUP output so the original Logo can be scaled without changing its proportions.

## 1.2.4 - 2026-08-10

- Clarify that `metadata.dependencies` lists embedded Skill dependencies; keep the Pillow runtime requirement in the dependency documentation instead.

## 1.2.3 - 2026-08-10

- Increase the default original-Logo lockup micro-gap to 8 pixels for a more breathable visual separation.

## 1.2.2 - 2026-08-10

- Set a restrained 4-pixel default micro-gap between the original Logo and brand text in ASS and PGS/SUP lockups.

## 1.2.1 - 2026-08-10

- Preserve the source aspect ratio for embedded ASS Logo paths by default and expose an explicit renderer-only horizontal scale override.
- Tighten the default Logo/text lockup and expose small gap/vertical-offset controls for renderer alignment.

## 1.2.0 - 2026-08-10

- Make original-raster Logo delivery sidecar-only: generate a combined PGS/SUP Logo-and-text subtitle and do not create a replacement MKV.

## 1.1.9 - 2026-08-10

- Add `scripts/raster_pgs_subtitle.py` for original raster Logo image subtitles that can be muxed with `-c copy` without video re-encoding.

## 1.1.8 - 2026-08-10

- Add `--watermark-end` so image-based video overlays can keep the ASS text watermark aligned with the full video duration.

## 1.1.7 - 2026-08-10

- Add `--no-watermark-logo` for image-based video overlays that keep the ASS text watermark while reserving the Logo for the original raster asset.

## 1.1.6 - 2026-08-10

- Combine all Logo paths into one shadow-free ASS vector block and restore text shadow only after the Logo spacer.

## 1.1.5 - 2026-08-10

- Correct the renderer-specific horizontal stretch of the embedded Logo vector and align its vertical center with the brand text.

## 1.1.4 - 2026-08-10

- Add a transparent ASS text spacer after inline Logo vectors so renderers that assign zero advance to drawings keep the Logo adjacent to the brand text.

## 1.1.3 - 2026-08-10

- Merge the brand Logo vector and watermark text into one ASS event so renderers keep the lockup adjacent instead of re-anchoring a separate Logo layer.

## 1.0.0 - 2026-08-10

- Rename the stable Skill identifier to `lov-subtitle-freedom-skill` and the source repository to `subtitle-freedom-skill`.
- Keep the public names “人人字幕” and “Subtitle Freedom” while publishing the renamed Skill as a new channel entry.

## 0.9.2 - 2026-08-10

- Rename the English public display name to “Subtitle Freedom” while keeping the Chinese name “人人字幕” and stable internal identifier `lov-subtitle-gloss`.
- Synchronize the English display name across the Skill Card, catalog metadata, WorkBuddy package, and SkillPay handoff.

## 0.9.1 - 2026-08-10

- Rename the public display name to “人人字幕” while retaining `lov-subtitle-gloss` as the stable internal identifier.
- Synchronize the display name across the Skill Card, catalog metadata, WorkBuddy package, and SkillPay handoff.

## 0.9.0 - 2026-08-10

- Define the selected learner Profile as a minimum difficulty floor: CET4 keeps CET4, B2, CET6, and advanced items instead of limiting output to one exact bucket.
- Add optional per-item glossary `level` labels and deterministic filtering for entries below the selected floor.
- Retain ungraded legacy glossary items and report them explicitly for backwards compatibility.
- Add `scripts/test_profile_floor.py` regression coverage and expose candidate, eligible, filtered, and ungraded counts in the CLI result.

## 0.8.0

- Codified the successful renderer-compatible watermark layout as a hard invariant: `Watermark` style alignment, text event, and vector-rule event all use one bottom-center anchor.
- Added `scripts/test_watermark_layout.py` regression coverage for default, short, long mixed-script, and disabled-watermark cases.
- Documented the rule in the runtime workflow, README, and ASS reference so future style changes do not reintroduce left/right drift.

## 0.7.3

- Changed the `Watermark` ASS style itself to bottom-center alignment so both text and vector rules retain one stable anchor in players that ignore or reinterpret inline `\\an` tags.

## 0.7.2

- Made cinematic-serif and signature rule placement robust for players that apply the `Watermark` style's right alignment to ASS vector drawings.
- Updated the visual style board so B and E decorative rules are centered on the rendered brand text rather than on its right edge.

## 0.7.1

- Fixed watermark alignment: the brand text and decorative rule now share a center anchor, keeping B-style watermarks symmetric for mixed Chinese/Latin text and custom brand names.
- Added mixed-script text-width estimation so the right edge remains within the configured margin when the brand text changes.

## 0.7.0

- Added six selectable watermark directions based on the visual board: minimal, cinematic serif, soft glow, glass, signature, and gold title.
- Made `cinematic_serif` (direction B) the default watermark style while keeping character-card styling separate.
- Added a thin accent-rule event for cinematic serif and signature watermarks.

## 0.6.0

- Added the restrained `elegant` visual profile and retained `classic` as an explicit legacy option.
- Reduced default art-card and watermark prominence: warm-white color, smaller type, thin outline, subtle fade, light spacing, and no decorative box.
- Added configurable art/watermark fonts and letter spacing.

## 0.5.0

- Added an optional ASS brand watermark, enabled by default only when the artistic layer is generated.
- Added custom watermark text and `--no-watermark` support.
- Set the default brand text to `手工川工作室 Agent 字幕组`.

## 0.4.0

- Made character art subtitles an explicit opt-in; ordinary learner subtitle output remains SRT-only by default.
- Added `off`, `identity_after`, `name_only`, and `full_visual` card modes.
- Separated visual first appearance, identity reveal, literal-name evidence, and final display timing.
- Added a conservative Arwen-style fallback: legacy video-review times are not shown early in `identity_after` mode.

## 0.3.0

- Added `character_evidence.py` for one-pass literal and semantic subtitle evidence.
- Added contextual semantic groups to avoid false matches from generic dialogue.
- Added optional narrow video contact sheets; full-film frame scanning is not the default.
- Kept literal-name time, semantic-context time, web identity evidence, and visual display time separate.

## 0.2.0

- Added Profile-aware, spoiler-safe character cards for meaningful first appearances.
- Added deterministic `character_cards.py` to resolve subtitle anchors into ASS art cues.
- Documented optional web research, evidence types, source retention, and unresolved-card handling.

## 0.1.0

- Added profile-aware English learner subtitle workflow for video and subtitle inputs.
- Added deterministic SRT annotation and validation script.
- Added ASS/SSA conversion with positioned scene-card and full-screen art cues.
## 0.8.1

- Expand learner explanations from isolated vocabulary to necessary language
  units: fixed phrases, idioms, proverbs, slang, culture-bound expressions,
  and genuinely difficult sentences.
- Add glossary `kind` and optional `label` fields; exact sentence phrases can
  now receive concise contextual explanations without changing cue timing.
- Add the LovStudio Skill Card, user case, dimension map, pricing basis, and
  distribution records for catalog presentation.
