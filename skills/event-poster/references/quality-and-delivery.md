# Poster Quality and Delivery Gates

Read this reference whenever a poster contains QR codes, external images, an
interactive channel-name generator, clipboard export, or a revision to an
already approved design.

## 1. Lock the accepted baseline

When the user approves a version and later asks for a localized fix, record the
accepted version as the baseline and list its invariants: canvas ratio, section
order, geometry, palette, typography, imagery, and unaffected copy.

- Change only the requested region unless the user explicitly asks for a redesign.
- A rejected experiment is negative evidence; revert its unrelated effects.
- Re-render the whole artifact after the local change and compare it with the
  accepted baseline outside the changed region.
- If scanability or legibility cannot be fixed inside the locked geometry,
  explain the tradeoff before changing the layout.

## 2. QR payload and rendering

Use `lov-create-qrcode` for deterministic QR generation and scan verification.

1. Confirm the exact destination. Prefer an official, stable short URL supplied
   by the organizer or event platform when it resolves to the same destination.
   Do not silently introduce a third-party shortener or alter query parameters.
2. Generate the QR at high contrast with a quiet zone of at least four modules.
   Avoid logos, gradients, low-contrast accent colors, filters, and CSS scaling
   until a plain code has passed scan verification.
3. Reduce payload density before enlarging the surrounding card. Then tune the
   QR inside the existing card. Redesign the card or footer only as a last step.
4. Keep each QR square; use `object-fit: contain` and integer rendered dimensions.
5. When several codes appear together, normalize their card, code, label, and
   caption geometry. Decorative color may differ only after scan verification.

## 3. Verify the final rendered artifact

Passing the source QR check is insufficient. Verify the exact poster PNG after
all CSS, scaling, compression, and export steps:

- decode every QR from the full-resolution output and compare the payload byte
  for byte;
- downscale the poster to representative phone widths (360, 390, and 414 CSS
  pixels) and decode again;
- inspect the QR quiet zone, contrast, square geometry, and nearby visual noise;
- for a remote/CDN delivery, download the published image and repeat the same
  checks on that exact file.

Report `scan verified` only when the final artifact decoded. Structural checks,
visual inspection, and successful source-QR decoding must be named accurately.

## 4. Asset completeness

Before capture or export:

- inline local and remote images as data URLs when practical;
- await `document.fonts.ready` and every image's `decode()` promise;
- resolve CSS background images as well as `<img>` elements;
- fail loudly when a required portrait, logo, QR, or background is missing;
- do not treat a browser preview with loaded local files as proof that the
  copied or downloaded raster contains those assets.

## 5. Interactive generator exports

Static posters remain plain HTML/CSS. If the user explicitly requests a poster
generator, JavaScript is allowed in the generator shell, but its export path
must create a fresh immutable snapshot for every action.

1. Persist the split-button action selection and mirror it on the primary button.
2. Permit export with an empty channel/inviter value; omit the invitation block
   instead of disabling the action.
3. On copy or download, increment a render request ID, freeze current form state,
   await fonts and assets, render a new canvas/blob, and use only that blob.
4. Do not reuse a cached canvas or previous blob after any state change.
5. Disable concurrent export actions until the current snapshot is written.
6. Keep copy and download on the same rendering function so their output is
   byte-equivalent for the same state.

When clipboard read-back is unavailable, show the completed snapshot's current
name, dimensions, and request ID; never claim clipboard verification without it.
