"""Draw simple original A19 bulb icons for the Zigbee2MQTT frontend.

Shape: flat, wide dome on top, straight taper, E26 screw base (a generic modern
A19 silhouette). No logos, lettering or product markings.

Usage: python3 draw_icons.py OUTPUT_DIR
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


def shape_masks():
    """Return (dome_mask, body_mask, base_info) for the bulb silhouette.

    A cone from the screw base up to the seam; above it the dome keeps flaring
    slightly outward and closes with large rounded shoulders."""
    from PIL import ImageChops

    top, dome_bot, body_bot = int(H * 0.05), int(H * 0.36), int(H * 0.70)
    half_bot = int(W * 0.115)          # half width where the body meets the base
    half_seam = int(W * 0.235)         # half width at the dome/body seam
    half_top = int(W * 0.255)          # the dome flares slightly wider toward the top
    corner = int(W * 0.17)             # roundness of the dome's shoulders

    cone = Image.new("L", (W, H), 0)
    ImageDraw.Draw(cone).polygon(
        [(CX - half_top, top), (CX + half_top, top), (CX + half_seam, dome_bot),
         (CX + half_bot, body_bot), (CX - half_bot, body_bot), (CX - half_seam, dome_bot)], fill=255)
    rounded = Image.new("L", (W, H), 0)
    ImageDraw.Draw(rounded).rounded_rectangle(
        [CX - half_top, top, CX + half_top, body_bot + corner], radius=corner, fill=255)
    silhouette = ImageChops.multiply(cone, rounded)

    upper = Image.new("L", (W, H), 0)
    ImageDraw.Draw(upper).rectangle([0, 0, W, dome_bot], fill=255)
    dome = ImageChops.multiply(silhouette, upper)
    body = ImageChops.subtract(silhouette, upper)
    return dome, body, (dome_bot, body_bot, half_bot, half_seam)


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

    # E26 base: short collar + threads + contact
    bw = 2 * half_bot
    y = body_bot
    d.rectangle([CX - bw // 2, y, CX + bw // 2, y + 6 * S], fill=(150, 156, 164, 255))
    y += 6 * S
    for i in range(4):
        tw = bw + 6 * S if i % 2 == 0 else bw
        col = (196, 200, 206, 255) if i % 2 == 0 else (128, 134, 142, 255)
        d.rounded_rectangle([CX - tw // 2, y, CX + tw // 2, y + 9 * S], radius=4 * S, fill=col)
        y += 9 * S
    d.polygon([(CX - bw // 2 + 2 * S, y), (CX + bw // 2 - 2 * S, y), (CX + bw // 4, y + 12 * S), (CX - bw // 4, y + 12 * S)], fill=(110, 116, 124, 255))
    d.ellipse([CX - 9 * S, y + 8 * S, CX + 9 * S, y + 18 * S], fill=(70, 74, 80, 255))

    # soft highlight on the dome
    hl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse([CX - int(W * .19), int(H * .09), CX - int(W * .06), int(H * .20)], fill=(255, 255, 255, 110))
    img.alpha_composite(hl.filter(ImageFilter.GaussianBlur(7 * S)))

    img.resize((256, 256), Image.LANCZOS).save(out)
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
out.mkdir(parents=True, exist_ok=True)
draw_bulb(dome_ftw, (255, 214, 160), out / "control4-vibrant-ftw.png")
draw_bulb(dome_rgbtw, (190, 170, 255), out / "control4-vibrant-rgbtw.png")
