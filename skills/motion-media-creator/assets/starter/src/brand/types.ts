import type React from 'react';

/** Props every brand seal variant accepts; `at` is the frame the stamp lands. */
export type SealProps = {at: number; size: number; color?: string; paper?: string; style?: React.CSSProperties};
