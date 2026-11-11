// The only layout constants for the 1080×1920 vertical cut. WeChat Channels covers the top ~160 px
// (notch / status bar / nav) and the bottom ~260 px (description, progress, actions).
export const W = 1080;
export const H = 1920;
export const SAFE = { top: 160, bottom: 260, side: 46 };

export const BAR = { top: SAFE.top + 10, height: 70 };
export const TAG_TOP = BAR.top + BAR.height + 18; // location tag, equation callouts
export const CAPTION_CENTER_Y = 1395; // caption centre line
export const NAMETAG_TOP = 1120;
export const CALLOUT_TOP = 1010; // faces sit in the upper half: numbers / stamps / arrows go on the chest area, above captions

// Palette: this is the first case's (deep indigo + a glowing accent + warm amber, from that film's subject).
// Re-derive it per film from the subject, not from a brand UI kit; the rgba() overlays in Film, Cover and
// CoverWide repeat these RGB values, so change them together.
export const C = {
  ink: '#0A0D24',
  indigo: '#151A4A',
  blue: '#4C7DFF',
  glow: '#7FA3FF',
  amber: '#FFC23D',
  white: '#FFFFFF',
};

export const FONT = {
  sans: 'InterviewSans', // public/fonts/sans.ttf (a heavy CJK sans, e.g. Noto Sans SC variable)
  title: 'InterviewTitle', // public/fonts/title.ttf (a display face, e.g. Smiley Sans)
};
