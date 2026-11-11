/** Rasterise text into a coarse boolean grid (for pixel / dot-matrix typography).
 * Results are cached only once every webfont has loaded, so a fallback-font raster from an
 * early render never sticks. Callers should gate on useFontsReady(). */
import {fontsReady} from './fonts';

const cache = new Map<string, boolean[][]>();

export const bitmap = (text: string, font: string, cols: number, rows: number, threshold = 0.42): boolean[][] => {
  const key = `${text}|${font}|${cols}|${rows}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const sx = 12;
  const cv = document.createElement('canvas');
  cv.width = cols * sx;
  cv.height = rows * sx;
  const ctx = cv.getContext('2d')!;
  ctx.fillStyle = '#000';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = `${rows * sx * 0.92}px '${font}'`;
  const m = ctx.measureText(text);
  const scale = Math.min(1, (cols * sx * 0.98) / Math.max(1, m.width));
  ctx.setTransform(scale, 0, 0, 1, (cols * sx * (1 - scale)) / 2, 0);
  ctx.fillText(text, (cols * sx) / 2, rows * sx * 0.54);
  const data = ctx.getImageData(0, 0, cv.width, cv.height).data;
  const grid: boolean[][] = [];
  for (let r = 0; r < rows; r++) {
    const row: boolean[] = [];
    for (let c = 0; c < cols; c++) {
      let on = 0;
      for (let y = 0; y < sx; y++)
        for (let x = 0; x < sx; x++) if (data[((r * sx + y) * cv.width + c * sx + x) * 4 + 3] > 128) on++;
      row.push(on / (sx * sx) > threshold);
    }
    grid.push(row);
  }
  if (fontsReady) cache.set(key, grid);
  return grid;
};
