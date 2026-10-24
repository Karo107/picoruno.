# Packs the renders into webp data URLs and writes them into gyakuso-button.html between the ART markers.
# python3 build.py <render-dir> <html>
import sys, io, base64, json, re
from PIL import Image
src, html = sys.argv[1], sys.argv[2]

def url(name, size=None, q=82, mode='webp'):
    im = Image.open(f'{src}/{name}')
    if size: im = im.resize(size, Image.LANCZOS)
    b = io.BytesIO()
    if mode == 'jpeg': im.convert('RGB').save(b, 'JPEG', quality=q); mt = 'jpeg'
    else: im.save(b, 'WEBP', quality=q, method=6); mt = 'webp'
    return f'data:image/{mt};base64,' + base64.b64encode(b.getvalue()).decode()

art = {
  'board': url('board.png', None, 80, 'jpeg'),
  'chick': [url(f'chick{d}.png', (192, 192)) for d in range(4)],
  'hurt': url('chick_hurt.png', (192, 192)),
  'coin': [url(f'coin{i}.png', (112, 112), 80) for i in range(12)],
  'egg': url('egg.png', (112, 112)),
  'spike': url('spike.png', (160, 160)),
}
js = 'const ART=' + json.dumps(art, separators=(',', ':')) + ';'
s = open(html, encoding='utf-8').read()
s, n = re.subn(r'/\*ART\*/.*?/\*/ART\*/', lambda m: '/*ART*/' + js + '/*/ART*/', s, flags=re.S)
assert n == 1, 'markers not found'
open(html, 'w', encoding='utf-8').write(s)
print('art bytes', len(js))
