"""小袋の印刷（ラベル）テクスチャを PIL で作る。袋の正面全体に貼る透過PNG。"""
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
W, H = 900, 1300            # 袋 4.5cm x 6.5cm


def font(sz):
    return ImageFont.truetype(FONT, sz)


def make(path, name, sub, color, ink=(255, 255, 255)):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # 上の注意書き（シールの少し下）
    d.text((W / 2, 255), "こちら側のどこからでも切れます", font=font(42), fill=(60, 50, 45, 235), anchor="mm")
    d.polygon([(110, 300), (170, 300), (140, 330)], fill=(200, 40, 35, 235))
    d.polygon([(W - 170, 300), (W - 110, 300), (W - 140, 330)], fill=(200, 40, 35, 235))
    # 真ん中の帯
    d.rounded_rectangle((90, 560, W - 90, 860), 40, fill=(*color, 240))
    d.text((W / 2, 680), name, font=font(96 if len(name) <= 5 else 78), fill=(*ink, 255), anchor="mm")
    d.text((W / 2, 790), sub, font=font(40), fill=(*ink, 230), anchor="mm")
    d.text((W / 2, 1110), "内容量 5g", font=font(34), fill=(60, 50, 45, 200), anchor="mm")
    im.save(path)


PACKS = [
    ("shoyu", "しょうゆ", "こいくち", (120, 40, 25)),
    ("karashi", "からし", "ねり", (210, 160, 30)),
    ("ketchup", "ケチャップ", "トマト", (200, 40, 40)),
    ("goma", "ごまドレ", "ドレッシング", (150, 110, 60)),
    ("soup", "液体スープ", "とんこつ", (60, 60, 70)),
]


def make_bump(path):
    """シール部分の細かいギザギザ（凹凸用のグレースケール）。"""
    im = Image.new("L", (W, H), 128)
    d = ImageDraw.Draw(im)
    top = 220          # 上のシール 1.1cm
    side, bot = 70, 90
    for x in range(0, W, 12):
        d.line((x, 0, x, top), fill=200, width=5)
    for y in range(top, H, 12):
        d.line((0, y, side, y), fill=200, width=5)
        d.line((W - side, y, W, y), fill=200, width=5)
    for x in range(0, W, 12):
        d.line((x, H - bot, x, H), fill=200, width=5)
    im.save(path)
