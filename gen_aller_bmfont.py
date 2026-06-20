# Torii: convert osu!stable's Aller TTF fonts into the BMFont binary (.bin) + atlas (.png)
# format osu!framework's GlyphStore expects (SharpFNT binary v3). Rendered at a nominal where
# lineHeight ~= 100 to match FontStore.ScaleAdjust = 100 (same as the bundled Torus fonts).
import os, struct
from PIL import Image, ImageFont, ImageDraw

SRC = r"C:\Users\megablackito\Favorites\toriiserverlocal\osu-stable-source\osu!ui\Resources"
DST = r"C:\Users\megablackito\Favorites\toriiserverlocal\toriirefresh-resources\osu.Game.Resources\Fonts\Aller"
os.makedirs(DST, exist_ok=True)

# (output weight name, ttf file)
WEIGHTS = [("Regular", "Aller.ttf"), ("Bold", "Aller_Bd.ttf"), ("Light", "Aller_Lt.ttf")]

# ASCII printable; non-ASCII falls back to other registered fonts at runtime.
CHARS = [chr(c) for c in range(0x20, 0x7F)]

ATLAS = 1024
PAD = 2  # transparent padding around each glyph to avoid bilinear bleed

def build(weight, ttf):
    path = os.path.join(SRC, ttf)
    # pick a pixel size so that ascent+descent (line height) is ~100
    probe = ImageFont.truetype(path, 100)
    pa, pd = probe.getmetrics()
    size = max(1, round(100 * 100 / (pa + pd)))
    font = ImageFont.truetype(path, size)
    ascent, descent = font.getmetrics()
    line_height = ascent + descent
    base = ascent

    atlas = Image.new("RGBA", (ATLAS, ATLAS), (255, 255, 255, 0))
    chars = []
    x = y = 0
    row_h = 0

    for ch in CHARS:
        try:
            xadv = round(font.getlength(ch))
        except Exception:
            xadv = 0
        bbox = font.getbbox(ch)  # (l, t, r, b) relative to anchor 'la' (top = ascent line)
        gw = (bbox[2] - bbox[0]) if bbox else 0
        gh = (bbox[3] - bbox[1]) if bbox else 0

        # Zero-ink glyphs (space etc.): a 1x1 transparent cell so the framework can still build a
        # (>0)-sized texture, while keeping the advance width for correct spacing.
        blank = gw <= 0 or gh <= 0
        if blank:
            gw = gh = 1

        cw, chh = gw + 2 * PAD, gh + 2 * PAD
        if x + cw > ATLAS:
            x = 0
            y += row_h
            row_h = 0
        if y + chh > ATLAS:
            raise SystemExit(f"atlas overflow for {weight}; increase ATLAS")

        if not blank:
            glyph = Image.new("L", (gw, gh), 0)
            d = ImageDraw.Draw(glyph)
            d.text((-bbox[0], -bbox[1]), ch, font=font, fill=255)
            rgba = Image.new("RGBA", glyph.size, (255, 255, 255, 0))
            rgba.putalpha(glyph)
            atlas.paste(rgba, (x + PAD, y + PAD))

        xo = 0 if blank else bbox[0]
        yo = 0 if blank else bbox[1]
        chars.append((ord(ch), x + PAD, y + PAD, gw, gh, xo, yo, xadv))
        x += cw
        row_h = max(row_h, chh)

    page_name = f"Aller-{weight}_0.png"
    atlas.save(os.path.join(DST, page_name))

    # ---- write BMFont binary v3 ----
    out = bytearray(b"BMF" + bytes([3]))

    # block 1: info
    name_b = b"Aller\x00"
    info = struct.pack("<hBBHBbbbbBBb", size, 0, 0, 100, 1, 0, 0, 0, 0, 0, 0, 0) + name_b
    out += bytes([1]) + struct.pack("<i", len(info)) + info

    # block 2: common
    common = struct.pack("<HHHHHBBBBB", line_height, base, ATLAS, ATLAS, 1, 0, 0, 0, 0, 0)
    out += bytes([2]) + struct.pack("<i", len(common)) + common

    # block 3: pages
    pages = page_name.encode() + b"\x00"
    out += bytes([3]) + struct.pack("<i", len(pages)) + pages

    # block 4: chars
    cdata = bytearray()
    for (cid, cx, cy, cw_, ch_, xo, yo, xa) in chars:
        cdata += struct.pack("<IHHHHhhhBB", cid, cx, cy, cw_, ch_, xo, yo, xa, 0, 15)
    out += bytes([4]) + struct.pack("<i", len(cdata)) + cdata

    with open(os.path.join(DST, f"Aller-{weight}.bin"), "wb") as f:
        f.write(out)

    print(f"{weight}: render size {size}, lineHeight {line_height}, base {base}, glyphs {len(chars)}")

for w, t in WEIGHTS:
    build(w, t)
print("done ->", DST)
