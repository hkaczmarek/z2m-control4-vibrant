"""Draw simple original A19 bulb icons for the Zigbee2MQTT frontend.

Shape: flat, wide dome on top, straight taper, E26 screw base (a generic modern
A19 silhouette). No logos, lettering or product markings.

Usage: python3 draw_icons.py OUTPUT_DIR [SIZE]   (SIZE default 256; 512 for zigbee2mqtt.io)
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

S = 4                      # supersampling factor
W = H = 256 * S
CX = W // 2


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


# Silhouette measured as proportions of a generic flat-dome A19 (units: px of a
# 1680 px tall reference, x = half width from the center line).
REF_H = 1680
P = {
    "top": 0,            # top center of the dome
    "dome_widest": 230,  # where the dome is widest
    "seam": 420,         # dome / body seam
    "body_bot": 1020,    # body meets the screw base
    "bottom": 1480,      # tip of the contact (base slightly shortened for the icon)
    "w_dome": 455,       # widest dome half width
    "w_seam": 425,       # half width at the seam
    "w_body_bot": 300,   # half width at the bottom of the body
}
SCALE = 0.90 * H / P["bottom"]
SLIM = 0.85          # overall width factor (1.0 = reference proportions)
CROWN = 2.8          # dome top flatness: 2 = elliptical, higher = flatter top
BASE_SLIM = 0.85     # screw base width relative to the bottom of the body
Y0 = int(0.05 * H)


def ry(v):
    return Y0 + int(P[v] * SCALE) if isinstance(v, str) else Y0 + int(v * SCALE)


def rx(v):
    return int((P[v] if isinstance(v, str) else v) * SCALE * SLIM)


def shape_masks():
    """Return (dome_mask, body_mask, base_info) for the bulb silhouette.

    Body: straight cone. Dome: flares slightly outward above the seam, then
    closes with an elliptical crown (rounded shoulders, gently arched top)."""
    top, widest, seam, body_bot = ry("top"), ry("dome_widest"), ry("seam"), ry("body_bot")
    w_dome, w_seam, w_bot = rx("w_dome"), rx("w_seam"), rx("w_body_bot")

    # dome outline: right side up, elliptical crown, left side down
    pts = [(CX + w_seam, seam), (CX + w_dome, widest)]
    a, b = w_dome, widest - top
    for i in range(1, 60):
        t = math.pi / 2 * (i / 60)            # from 0 (side) to pi/2 (top)
        # superellipse: rounded shoulders, flatter crown (CROWN=2 is a plain ellipse)
        pts.append((CX + a * math.cos(t) ** (2 / CROWN), widest - b * math.sin(t) ** (2 / CROWN)))
    pts.append((CX, top))
    pts += [(2 * CX - x, y) for x, y in reversed(pts[:-1])]
    dome = Image.new("L", (W, H), 0)
    ImageDraw.Draw(dome).polygon(pts, fill=255)

    body = Image.new("L", (W, H), 0)
    ImageDraw.Draw(body).polygon(
        [(CX - w_seam, seam), (CX + w_seam, seam), (CX + w_bot, body_bot), (CX - w_bot, body_bot)], fill=255)
    return dome, body, (seam, body_bot, w_bot, w_seam)


def paint(mask, fn):
    layer = Image.new("RGBA", (W, H))
    px = layer.load()
    box = mask.getbbox()
    for y in range(box[1], box[3], 2):
        for x in range(box[0], box[2], 2):
            c = fn(x, y, box)
            for dx in (0, 1):
                for dy in (0, 1):
                    px[x + dx, y + dy] = c
    return layer


def draw_bulb(dome_fn, glow_rgb, out: Path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dome_m, body_m, (dome_bot, body_bot, half_bot, half_seam) = shape_masks()

    # glow behind the lit dome
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([CX - int(W * .34), int(H * .0), CX + int(W * .34), int(H * .48)], fill=glow_rgb + (120,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(26 * S)))

    # body: matte white, slightly shaded toward the edges and the bottom
    def body_fn(x, y, box):
        nx = abs((x - CX) / ((box[2] - box[0]) / 2))
        ny = (y - box[1]) / (box[3] - box[1])
        shade = 0.10 * nx ** 2 + 0.10 * ny
        return lerp((246, 246, 244, 255), (200, 202, 205, 255), shade * 2.2)

    img.paste(paint(body_m, body_fn), (0, 0), body_m)
    img.paste(paint(dome_m, dome_fn), (0, 0), dome_m)

    d = ImageDraw.Draw(img)
    # thin seam between dome and body
    d.line([(CX - half_seam, dome_bot), (CX + half_seam, dome_bot)], fill=(210, 212, 215, 255), width=2 * S)

    # E26 base: collar, threads, insulator and contact, scaled to the reference
    bw = int(2 * half_bot * BASE_SLIM)
    y = body_bot
    base_h = ry("bottom") - body_bot
    collar = int(base_h * 0.08)
    # collar narrows from the body width down to the screw base width
    d.polygon([(CX - half_bot, y), (CX + half_bot, y), (CX + bw // 2, y + collar), (CX - bw // 2, y + collar)],
              fill=(150, 156, 164, 255))
    y += collar
    n, th = 4, int(base_h * 0.15)
    for i in range(n):
        tw = bw + 6 * S if i % 2 == 0 else bw - 2 * S
        col = (200, 204, 210, 255) if i % 2 == 0 else (128, 134, 142, 255)
        d.rounded_rectangle([CX - tw // 2, y, CX + tw // 2, y + th], radius=th // 2, fill=col)
        y += th
    ins = ry("bottom") - y
    d.polygon([(CX - bw // 2 + 2 * S, y), (CX + bw // 2 - 2 * S, y), (CX + bw // 5, y + int(ins * 0.7)), (CX - bw // 5, y + int(ins * 0.7))], fill=(60, 64, 70, 255))
    d.ellipse([CX - bw // 6, y + int(ins * 0.45), CX + bw // 6, ry("bottom")], fill=(150, 156, 164, 255))

    # soft highlight on the dome
    hl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse([CX - int(W * .19), int(H * .09), CX - int(W * .06), int(H * .20)], fill=(255, 255, 255, 110))
    img.alpha_composite(hl.filter(ImageFilter.GaussianBlur(7 * S)))

    img.resize((SIZE, SIZE), Image.LANCZOS).save(out)
    print("wrote", out)


def dome_ftw(x, y, box):
    # tunable white: cool at the top, warm toward the seam
    t = (y - box[1]) / (box[3] - box[1])
    return lerp((236, 243, 255, 255), (255, 214, 158, 255), t)


def dome_rgbtw(x, y, box):
    # hue sweeps left to right, fading to white at the top
    h = (x - box[0]) / (box[2] - box[0])
    h6 = (h * 6) % 6
    i, f = int(h6), h6 - int(h6)
    rgb = [(1, f, 0), (1 - f, 1, 0), (0, 1, f), (0, 1 - f, 1), (f, 0, 1), (1, 0, 1 - f)][i]
    sat = 0.25 + 0.75 * (y - box[1]) / (box[3] - box[1])
    return tuple(int(255 * (1 - sat + sat * v)) for v in rgb) + (255,)


out = Path(sys.argv[1])
SIZE = int(sys.argv[2]) if len(sys.argv) > 2 else 256
out.mkdir(parents=True, exist_ok=True)
draw_bulb(dome_ftw, (255, 214, 160), out / "control4-vibrant-ftw.png")
draw_bulb(dome_rgbtw, (190, 170, 255), out / "control4-vibrant-rgbtw.png")
