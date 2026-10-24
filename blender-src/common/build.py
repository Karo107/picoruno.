"""ゲームの game.html に KIT と Blender 素材を埋め込んで、リポジトリ直下の <slug>.html を作る。

  python3 blender-src/common/build.py hanko

<slug>/assets.json の例:
  {"bg": {"src": "out/bg.png", "fmt": "jpg", "w": 1080, "q": 82},
   "hanko": {"src": "out/hanko.png", "fmt": "webp", "w": 300, "q": 88}}
game.html の中の  /*KIT*/  と  __IMG_bg__  が置きかわる。
"""
import base64, io, json, os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))


def encode(path, fmt, w=None, q=85, crop=None, gain=None):
    im = Image.open(path)
    if gain:
        from PIL import ImageEnhance
        a = im.getchannel("A") if im.mode == "RGBA" else None
        im = ImageEnhance.Brightness(im.convert("RGB")).enhance(gain)
        if a:
            im.putalpha(a)
    if crop:
        im = im.crop(crop)
    if w and im.width != w:
        im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    if fmt == "jpg":
        im.convert("RGB").save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        mime = "image/jpeg"
    elif fmt == "webp":
        im.save(buf, "WEBP", quality=q, method=6)
        mime = "image/webp"
    else:
        im.save(buf, "PNG", optimize=True)
        mime = "image/png"
    return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode(), len(buf.getvalue())


def build(slug):
    src = os.path.join(ROOT, "blender-src", slug)
    html = open(os.path.join(src, "game.html"), encoding="utf-8").read()
    kit = open(os.path.join(HERE, "kit.js"), encoding="utf-8").read()
    html = html.replace("/*KIT*/", kit)
    assets = json.load(open(os.path.join(src, "assets.json")))
    total = 0
    for name, a in assets.items():
        if a.get("fmt") == "json":
            html = html.replace(f"__JSON_{name}__", open(os.path.join(src, a["src"])).read().strip())
            continue
        uri, n = encode(os.path.join(src, a["src"]), a.get("fmt", "webp"), a.get("w"), a.get("q", 85), a.get("crop"), a.get("gain"))
        total += n
        print(f"  {name:12s} {n/1024:7.1f} KB")
        html = html.replace(f"__IMG_{name}__", uri)
    if "__IMG_" in html:
        i = html.index("__IMG_")
        raise SystemExit("未解決の素材: " + html[i:i + 30])
    out = os.path.join(ROOT, f"{slug}.html")
    open(out, "w", encoding="utf-8").write(html)
    print(f"{out}: {os.path.getsize(out)/1024:.0f} KB (images {total/1024:.0f} KB)")


if __name__ == "__main__":
    for s in sys.argv[1:]:
        build(s)
