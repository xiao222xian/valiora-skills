// The film's credits catalogue: every piece of third-party material (photos, footage, 3D models, sounds), in film
// order, once each, written down when the material is taken. Two readers share it, so they cannot drift apart: the
// end card (scenes/S14Outro.tsx) and the description blocks (tools/credits.mjs -> credits-full.txt,
// credits-compact.txt). The card stands on its own: it names each licence with its short URL and never points to the
// description (2026-10-12, the Tesla film: the card sent viewers to the description, and the description the user
// published had no credits). Node imports this file too (tools/credits.mjs): keep it free of imports and of
// TypeScript that does not simply erase (no enums, no namespaces).

export type Credit = {
  author: string;
  /** The title the source gives; leave it out when there is none. */
  title?: string;
  /** 'CC BY 2.0', 'CC BY-SA 4.0', ...; 'CC0', 'PD' (public domain) and 'Pexels' need no attribution. */
  license: string;
  /** Source page; the description blocks print it (required for material that needs attribution). */
  url?: string;
  /** What was changed, printed in the description after the title, e.g. a 3D model whose logos were removed. */
  changed?: string;
};

/** In film order, once each. Example:
 * {author: 'Steve Jurvetson', title: 'Tesla @ Home', license: 'CC BY 2.0',
 *  url: 'https://commons.wikimedia.org/wiki/File:Tesla_(2779858337).jpg'} */
export const CREDITS: Credit[] = [];
/** One line after the attributed list, on the card and in the description; '' when nothing was changed. */
export const CREDITS_CHANGED = '以上素材均经修改';
export const LICENSES_HEAD = '许可';
/** Head of the one line that thanks the material needing no attribution. */
export const OTHER_HEAD = '其余资料';

const FREE = /^(CC0|PD|public domain|公有领域|Pexels|Unsplash|Pixabay)\b/i;
/** True unless the licence asks for no attribution; an unknown licence counts as one that does. */
export const needsCredit = (c: Credit): boolean => !FREE.test(c.license.trim());
export const attributed = (): Credit[] => CREDITS.filter(needsCredit);

/** Short licence URL for the card (no scheme, no trailing slash); null when there is nothing to cite. */
export const licenseUrl = (license: string): string | null => {
  const cc = /^CC (BY(?:-NC)?(?:-SA|-ND)?) (\d\.\d)$/.exec(license.trim());
  if (cc) return `creativecommons.org/licenses/${cc[1].toLowerCase()}/${cc[2]}`;
  if (/^CC0\b/.test(license)) return 'creativecommons.org/publicdomain/zero/1.0';
  if (/^Pexels\b/i.test(license)) return 'pexels.com/license';
  return null;
};

/** Licence as a viewer reads it: 'PD' is written out. */
export const licenseName = (license: string): string => (/^(PD|public domain)$/i.test(license.trim()) ? '公有领域' : license.trim());

/** The material needing no attribution, authors grouped by licence: 「其余资料：NASA、美国国会图书馆（公有领域）；Paul Sladen（CC0）」; '' when none. */
export const otherLine = (): string => {
  const groups = new Map<string, string[]>();
  for (const c of CREDITS) {
    if (needsCredit(c)) continue;
    const k = licenseName(c.license);
    const authors = groups.get(k) ?? [];
    if (!authors.includes(c.author)) authors.push(c.author);
    groups.set(k, authors);
  }
  return groups.size ? `${OTHER_HEAD}：` + [...groups].map(([l, a]) => `${a.join('、')}（${l}）`).join('；') : '';
};
