"""ヒーロー画像の紙に貼る印影テクスチャ（紙の色＋朱の丸印）を PIL で作る。"""
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"


def make(path, text="ぴこ", w=1400, h=1000):
    paper = (237, 232, 219)
    im = Image.new("RGB", (w, h), paper)
    ink = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(ink)
    cx, cy, r = int(w * 0.38), int(h * 0.42), 120
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=255, width=14)
    f = ImageFont.truetype(FONT, 96)
    for i, ch in enumerate(text):
        bb = d.textbbox((0, 0), ch, font=f)
        d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], cy - 100 + i * 100 - bb[1] + 2), ch, font=f, fill=255)
    # かすれ
    rnd = random.Random(3)
    px = ink.load()
    for _ in range(9000):
        x, y = rnd.randrange(cx - r - 10, cx + r + 10), rnd.randrange(cy - r - 10, cy + r + 10)
        px[x, y] = int(px[x, y] * 0.2)
    ink = ink.filter(ImageFilter.GaussianBlur(1.2))
    red = Image.new("RGB", (w, h), (196, 40, 32))
    im = Image.composite(red, im, ink.point(lambda v: int(v * 0.9)))
    # 罫線（薄い）
    dd = ImageDraw.Draw(im)
    for y in range(640, 960, 70):
        dd.line((120, y, w - 120, y), fill=(200, 196, 186), width=3)
    im.save(path)
