import sys, os
from PIL import Image, ImageDraw
src, out, starts = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(',')]
offs = list(range(-20, 61, 10))
im0 = Image.open(os.path.join(src, 'element-000.jpeg')); w, h = im0.size
sheet = Image.new('RGB', (len(offs) * (w + 4), len(starts) * (h + 4)), 'white')
d = ImageDraw.Draw(sheet)
for r, s in enumerate(starts):
    for c, o in enumerate(offs):
        f = s + o; i = round(f / 10)
        p = os.path.join(src, f'element-{i:03d}.jpeg')
        if not os.path.exists(p): continue
        x, y = c * (w + 4), r * (h + 4)
        sheet.paste(Image.open(p), (x, y))
        d.rectangle([x, y, x + 52, y + 14], fill='black'); d.text((x + 3, y + 1), str(i * 10), fill='white')
sheet.save(out, quality=85)
print(out, sheet.size)
