# Visual World and Media System

Use this reference to turn a Brand Spine into a distinctive, trustworthy, and
implementation-ready visual world.

## 1. Existing equity before novelty

Inspect tokens, type, layout, components, icons, Logo use, imagery, product UI,
neighboring pages, and approved brand rules. Classify them as preserve,
strengthen, retire, or unknown. A redesign should build equity, not erase it by
default.

References teach category grammar, interaction patterns, and quality thresholds.
They do not donate their palette, typography, illustration style, motion, or
recognizable trade dress.

## 2. Visual-world contract

Define:

- typographic personality and display/body roles;
- semantic palette and dominant canvas/surface relationship;
- grid, container, negative space, density, and vertical rhythm;
- material language: paper, ink, glass, metal, canvas, screen, fabric, or another
  product-relevant choice;
- borders, corners, shadows, texture, and depth;
- image, screenshot, video, illustration, and icon treatment;
- control, focus, loading, success, and error grammar;
- signature motif, restraint rule, motion, and reduced-motion equivalent.

Every choice should connect to the Brand Spine. Specific constraints outperform
adjectives such as “modern”, “premium”, or “creative”.

### Product-style fit

No style is a global default. Before choosing a visual world, write a compact
rationale across these inputs:

| Input | Decision question |
|-------|-------------------|
| Product category and mechanism | What behavior or material is intrinsic to the product? |
| Audience and readiness | What must feel familiar, aspirational, calm, rigorous, or immediate? |
| Use situation and emotional state | Where, why, and under what pressure is the page viewed? |
| Trust, risk, and accessibility | How much reassurance, evidence, restraint, or legibility is required? |
| Existing brand equity | Which recognizable assets and behaviors must be preserved or repaired? |
| Authentic assets | Which real interfaces, artifacts, people, places, or outputs can carry the world? |

Choose one direction only after weighing these inputs. Name at least two
plausible alternatives and why they are less appropriate for this product. A
style that worked for the previous task has no privileged status here.

### Treat mood as a constraint

Requested adjectives are outcomes to interpret, not theme presets. Translate
them into product-specific materials, artifacts, density, typography,
composition, imagery, and behavior. Do not add visual signals whose only job is
to imitate a category or make the page look fashionable.

## 3. Stage composition

Use content roles to vary composition while retaining one system:

- **Monument:** oversized type/artifact, exceptional whitespace, decisive crop.
- **Workbench:** operable product surface with labels, state, and mechanism.
- **Gallery:** disciplined variations sharing scale or alignment logic.
- **Evidence:** quieter hierarchy, legible sources, dates, and attribution.
- **Bridge:** a shift in scale, surface, or motion that advances the story.
- **Action:** the clearest contrast and simplest decision surface.

Do not render every section as centered title plus three rounded cards. Cards are
appropriate only when each item is a peer object requiring its own boundary.

## 4. Avoid generic AI aesthetics

- default purple-blue gradient on white;
- interchangeable rounded bento grids;
- excessive glass, glow, blur, and floating orbs;
- generated scenes unrelated to product truth;
- every heading centered and every section equally loud;
- mixed icon families or arbitrary emoji;
- oversized slogans without category or product orientation;
- continuous motion without hierarchy or reduced-motion behavior.

Minimalism still needs distinctive type, composition, material, and interaction.
Maximalism still needs reading order, performance, and restraint.

## 5. Product staging

- Use real screenshots, covers, outputs, and demos as evidence.
- Show product content large enough to understand.
- Crop around the meaningful state, not decorative browser chrome.
- Annotate mechanism only when labels remain accurate and accessible.
- Keep HTML copy outside image pixels whenever practical.
- Define mobile recomposition, crop-safe area, and fallback.

## 6. Logo geometry and identity hierarchy

Do not trust an SVG viewBox, PNG canvas, or CSS box to prove a Logo is centered.
Inspect the visible artwork and its actual rendered contexts:

- compare file bounds with opaque/ink bounds and detect asymmetric transparent
  padding or an off-center inner group;
- check mark and wordmark optical alignment rather than only numeric centering;
- render header, hero, footer, favicon, and compact mobile variants at their real
  CSS sizes;
- fix the canonical asset or use one intentional wrapper when possible instead
  of accumulating per-placement negative margins;
- on a product Landing Page, keep the product identity primary and treat the
  maker or parent-brand mark as supporting provenance unless strategy says otherwise.

## 7. Authenticity policy

| Material | AI generation policy |
|----------|----------------------|
| Decorative background/texture | Generate when it serves the visual world |
| Conceptual illustration | Generate; track internally as synthetic |
| Product-stage illustration | Generate only when clearly illustrative |
| Real product UI/output | Capture from the product/source |
| Founder/customer portrait | Use approved real media |
| Customer Logo/testimonial/case | Use verified approved sources |
| Metrics, awards, ratings | Use documented sources only |

Synthetic proof does not reach production.

## 8. Image generation workflow

Use the strongest suitable configured capability rather than freezing the Skill
to a model name. Prompt the system, not isolated decorative images:

```text
Brand thesis and section job;
subject, action, and truthful role;
composition, focal point, and relationship to HTML copy;
camera/rendering language, light, material, texture, and palette;
relationship to product UI and adjacent assets;
aspect ratio, mobile crop-safe area, and negative space;
negative constraints: text, fake logos, artifacts, clichés;
continuity constraints across the asset family.
```

Generate candidates, select one language, carry forward reference/seed controls
where supported, inspect details, then crop, compress, name, and export variants.

## 9. Video and motion jobs

Choose source by truth requirement:

- feature proof → real screen recording;
- guided explanation → edited demo with captions/transcript;
- customer proof → approved footage;
- brand atmosphere → short generated or captured ambient sequence.

Prefer restrained, purposeful motion: reveal mechanism, guide focus, demonstrate
transformation, or carry the signature. Autoplay never uses sound. Provide a
stable first frame and reduced-motion equivalent.

## 10. Hosting by audience

| Primary audience | Preferred route | Fallback |
|------------------|-----------------|----------|
| Overseas | Existing YouTube/Vimeo or reliable host | poster plus direct link |
| Mainland China | Existing Bilibili/domestic CDN/self-hosted | poster plus direct link |
| Mixed | locale-aware host or reliable self-hosted media | explicit host choices |
| Privacy/control sensitive | self-hosted MP4/WebM or click-to-load player | transcript/poster |

Respect existing channels, consent, analytics, review, and performance rules.

## 11. Asset handoff

For each asset record:

- narrative job and source/truth status;
- filename/path, intrinsic size, aspect ratio, and format;
- desktop/mobile focal point and responsive variants;
- alt, empty alt, caption, transcript, credit, or source note;
- priority/lazy behavior, poster, and failure fallback.

For the whole visual system, also record the style-fit rationale, selected
direction, rejected alternatives, and which evidence would require a future
direction change.

Give hero/LCP media explicit dimensions and appropriate priority. Lazy-load
below-the-fold media and heavy players. Prevent motion from shifting copy or CTA.
