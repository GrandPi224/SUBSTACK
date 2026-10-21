"""Bullchip Banter dialogue cards: round avatar + name + line, one PNG per spoken line.

python assets/banter/make_cards.py <scene.txt> <out_folder_name>
Avatars are cropped from the round-table banner so the whole cast matches.
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
BANNER = r"//SERVER01/Folder Redirection/Chip/Documents/1 SUBSTACK/Bucky DaBull/Blokes round table wood carved.png"
scene_path, out_name = sys.argv[1], sys.argv[2]
OUT = ROOT / "assets" / "banter" / out_name
OUT.mkdir(parents=True, exist_ok=True)

# (center x, center y, side) of each head + name tag in the banner
BOXES = {
    "LEPHEWY": (205, 410, 250), "DUHBURRO": (380, 285, 240), "DUHELEFANTE": (560, 280, 290),
    "BUCKY DABULL": (840, 265, 280), "CAPO DAWOLF": (1080, 280, 260), "BITME DABEAR": (1300, 270, 270),
    "HOOTER": (1525, 370, 260), "BOSS HOG": (1460, 640, 320), "BADASK": (265, 665, 280),
}
NAMES = {
    "LEPHEWY": "LePhewy", "DUHBURRO": "DuhBurro", "DUHELEFANTE": "DuhElefante", "BUCKY DABULL": "Bucky DaBull",
    "CAPO DAWOLF": "Capo DaWolf", "BITME DABEAR": "BitMe DaBear", "HOOTER": "Hooter", "BOSS HOG": "Boss Hog",
    "BADASK": "BadAsk",
}
A, W, PADL = 220, 1200, 40
TX = PADL + A + 40
TW = W - TX - 40
FB = ImageFont.truetype("C:/Windows/Fonts/georgiab.ttf", 40)
FR = ImageFont.truetype("C:/Windows/Fonts/georgia.ttf", 38)
FI = ImageFont.truetype("C:/Windows/Fonts/georgiai.ttf", 34)
LH = {"b": 54, "i": 46, "r": 52}

banner = Image.open(BANNER).convert("RGB")


def avatar(key):
    cx, cy, s = BOXES[key]
    big = A * 4
    crop = banner.crop((cx - s // 2, cy - s // 2, cx + s // 2, cy + s // 2)).resize((big, big), Image.LANCZOS)
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).ellipse((8, 8, big - 8, big - 8), fill=255)
    out = Image.new("RGBA", (big, big), (255, 255, 255, 0))
    out.paste(crop, (0, 0), mask)
    ImageDraw.Draw(out).ellipse((8, 8, big - 8, big - 8), outline=(176, 141, 60, 255), width=16)
    return out.resize((A, A), Image.LANCZOS)


AV = {k: avatar(k) for k in BOXES}
(ROOT / "assets" / "avatars").mkdir(exist_ok=True)
for k, a in AV.items():
    a.save(ROOT / "assets" / "avatars" / (NAMES[k].lower().replace(" ", "-") + ".png"))

_d = ImageDraw.Draw(Image.new("RGB", (1, 1)))


def wrap(text, font):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if _d.textlength(t, font=font) <= TW:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


src = Path(scene_path).read_text(encoding="utf-8").split("\n---")[0]
items, n = [], 0
for para in [p.strip() for p in src.split("\n\n") if p.strip()]:
    m = re.match(r"^([A-Z][A-Z ]+): (.*)$", para, re.S)
    if not m or m.group(1).strip() not in NAMES:
        items.append({"type": "text", "text": para})
        continue
    key, line = m.group(1).strip(), m.group(2).strip()
    stage = tail = None
    sm = re.match(r"^\((.*?)\)\s*(.*)$", line)
    if sm:
        stage, line = sm.group(1), sm.group(2)
    tm = re.match(r"^(.*?)\s*\((.*?)\)$", line)
    if tm:
        line, tail = tm.group(1), tm.group(2)
    rows = [("b", NAMES[key])] + ([("i", stage)] if stage else []) + [("r", l) for l in wrap(line, FR)]
    rows += [("i", l) for l in wrap(tail, FI)] if tail else []
    h = max(A + 40, 30 + sum(LH[t] for t, _ in rows) + 20)
    card = Image.new("RGB", (W, h), "white")
    d = ImageDraw.Draw(card)
    card.paste(AV[key], (PADL, (h - A) // 2), AV[key])
    y = 30
    for t, s in rows:
        d.text((TX, y), s, font={"b": FB, "i": FI, "r": FR}[t], fill={"b": "#1F3864", "i": "#7a6a55", "r": "#1a1a1a"}[t])
        y += LH[t]
    n += 1
    fn = OUT / f"{n:02d}.png"
    card.save(fn, optimize=True)
    alt = f"{NAMES[key]}: " + (f"({stage}) " if stage else "") + line + (f" ({tail})" if tail else "")
    items.append({"type": "card", "file": f"assets/banter/{out_name}/{n:02d}.png", "alt": alt})

(OUT / "cards.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
print(n, "cards;", sum(i["type"] == "text" for i in items), "text blocks")
