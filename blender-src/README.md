# blender-src

Blender で絵をつくるゲームの元データ。1ゲーム = 1フォルダ。

- `<slug>/render.py` … Blender（`pip install bpy`）で素材をレンダリングして `out/` に書き出す（`--fast` で半分の解像度）
- `<slug>/game.html` … ゲーム本体。`/*KIT*/` と `__IMG_name__` が build で置きかわる
- `<slug>/assets.json` … どの素材をどの形式・サイズで埋め込むか
- `common/build.py <slug>` … 素材を埋め込んだ1ファイルの `<slug>.html` をリポジトリ直下に作る
- `common/kit.js` … BGM（自動作曲）・効果音・保存・シェアの共通部品
- `common/shot.js` … Playwright で動作確認とスクリーンショット

```
cd blender-src/hanko && python3 render.py && cd .. && python3 common/build.py hanko
```
