# Implementation and Acceptance

Use the target repository's framework, design system, package manager, and test
commands. These gates define outcomes rather than a fixed stack.

## 1. Repository inspection

Before editing, identify:

- project instructions and current git state;
- homepage route and public/authenticated rendering;
- design tokens, typography, shared primitives, icons, and layout system;
- content/data source and localization convention;
- metadata, sitemap, robots, analytics, consent, and structured data patterns;
- image/video pipeline, relevant tests, and production build command.

Modify the smallest coherent surface. Preserve user changes and avoid parallel
components that duplicate existing primitives.

## 2. Brand implementation acceptance

- The Brand Spine is traceable to copy, hierarchy, tokens, media, and behavior.
- The visual direction has a product-specific style-fit rationale covering
  audience, use situation, trust/risk, existing equity, and authentic assets;
  it is not inherited from a trend or previous project.
- Existing equity marked `preserve` remains intact.
- The signature motif appears in a small number of meaningful moments.
- Typography, surfaces, controls, icons, imagery, and states share one grammar.
- Product value and mechanism remain dominant over platform, package, and install
  choices; distribution is staged as availability/action unless it materially
  changes the promise.
- A logo-swap, headline-spine, silhouette, and behavior review have been run.
- Visible Logo artwork is optically aligned at actual header, hero, footer, and
  compact sizes; transparent canvas or viewBox centering alone is insufficient.
- Metadata, sharing, loading, success, error, and footer do not fall back to a
  generic or contradictory identity.

## 3. Interaction semantics

| Intent | Preferred element | Acceptance |
|--------|-------------------|------------|
| Navigation | link | real destination, current state when applicable |
| Primary action | labeled button/link | one high-emphasis goal per surface |
| Prompt/action input | form with label and submit | real handler, IME-safe, success/error states |
| Status | text/badge | non-interactive unless it opens real detail |
| Toggle | checkbox/switch/pressed button | persistent visible state |
| Video | button/facade plus player | keyboard, title, poster, captions/fallback |

Do not style a `div` as a control or rely on toast alone for durable state.

## 4. Content and evidence

- Public copy contains product-relevant information, not planning conversation.
- Claims have visible proof or source records.
- Testimonials have approved attribution.
- Metrics retain definition, date, and source internally.
- Generated visuals do not impersonate customers or product screenshots.
- Pricing, availability, downloads, and badges lead to current targets.
- Legal/privacy surfaces match actual forms, embeds, cookies, and analytics.

## 5. Responsive acceptance

Verify 320 px, a common tablet width, and intended desktop. Include at least one
common 1280-1440 px desktop width rather than checking only an extra-wide canvas:

- no horizontal overflow or clipped action;
- heading wraps intentionally and preserves headline hierarchy;
- Logo/wordmark placement remains optically centered and consistently scaled;
- DOM and reading order agree;
- media focal points, product text, and overlays remain legible;
- touch targets and spacing remain usable;
- localized text does not overlap or disappear;
- sticky/fixed elements do not hide content or feedback;
- mobile recomposes monuments, workbenches, galleries, and evidence rather than
  shrinking the desktop composition.

## 6. Accessibility acceptance

- Semantic landmarks, one clear H1, logical headings, and keyboard order.
- Visible focus, no traps, and programmatic names for controls.
- Explicit labels; placeholder is not the only label.
- Instructions/errors are associated; dynamic feedback is announced.
- Meaning does not rely on color or motion alone.
- Informative images have useful alt; decorative images use empty alt.
- Meaningful speech has captions or transcript.
- Motion respects `prefers-reduced-motion`.
- During IME composition, Enter accepts the candidate rather than submitting.

## 7. Performance acceptance

Current Core Web Vitals targets at the 75th percentile:

- LCP ≤ 2.5 seconds;
- INP ≤ 200 milliseconds;
- CLS ≤ 0.1.

Label field targets unverified until real-user data exists. Prioritize optimized
LCP media/font loading, explicit dimensions, responsive sources, lazy media,
limited client JavaScript, stable server/client content, and main-thread restraint.

## 8. SEO and sharing

- Concise title aligned with visible H1, category, brand, and locale.
- Specific meta description rather than keyword stuffing.
- Canonical and locale alternates when real localized routes exist.
- Accurate share image and copy built from the same brand system.
- Correct preview/production indexing behavior.
- Structured data only for visible, supported entities/content.
- Real favicon, site identity, contact, legal, and footer links.

Do not add rating, FAQ, review, product, organization, or software schema solely
to pursue rich results.

## 9. Analytics and conversion

Define a short chain:

1. landing/campaign entry;
2. meaningful product, proof, demo, or use-case engagement;
3. form start or product-intent submit when useful;
4. primary conversion success;
5. failure state needed for diagnosis.

Distinguish click from success, prevent duplicates, and never send personal or
free-form input values. Use existing consent and analytics conventions.

## 10. Technical command order

Run what the repository supports:

1. focused formatting/lint;
2. typecheck;
3. focused unit/integration tests;
4. production build;
5. route/HTTP checks;
6. headless interactions and screenshots;
7. accessibility and performance checks.

When the user asked to publish or the public page changed, inspect the final
production URL after deployment. A local screenshot or successful build does not
verify production copy, assets, routing, or CSS.

Do not start or stop a persistent dev server unless required and not already
managed by the project.

## 11. Final visitor-path gate

Test navigation → first-viewport meaning → headline/product progression → proof →
primary action/input → next state → feedback → return/recovery. Repeat for real
public/authenticated states, mobile/desktop, keyboard, IME, slow/broken media,
and form errors.

Completion is the observed brand and user outcome, not successful compilation.
