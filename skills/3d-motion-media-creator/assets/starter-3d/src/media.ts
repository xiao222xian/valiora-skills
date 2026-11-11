// The film's archival photos and footage. Written by tools/conform.py from the licence register
// (../licenses/assets.json); empty until the film has archival material. Do not edit by hand.
export type MediaItem = {file: string; type: 'photo' | 'video'; w: number; h: number; dur?: number; bw?: boolean;
  credit: string; license: string; title: string; fullCredit: string; pageUrl: string; brand: boolean};

export const MEDIA = {} as const satisfies Record<string, MediaItem>;

export type MediaKey = keyof typeof MEDIA;
