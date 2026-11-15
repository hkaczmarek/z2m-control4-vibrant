"""Draw simple original A19 bulb icons for the Zigbee2MQTT frontend."""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

S = 4  # supersampling
W = H = 256 * S


def bulb(fill_fn, glow_rgb, out: Path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # soft glow
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy, r = W // 2, int(H * 0.40), int(W * 0.30)
    gd.ellipse([cx - r - 40 * S // 4, cy - r - 40 * S // 4, cx + r + 40 * S // 4, cy + r + 40 * S // 4], fill=glow_rgb + (110,))
    glow = glow.filter(ImageFilter.GaussianBlur(28 * S))
    img.alpha_composite(glow)

    # glass: circle + tapered neck (A19 silhouette)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    neck_top = cy + int(r * 0.55)
    neck_bot = int(H * 0.72)
    md.polygon(
        [(cx - int(r * 0.83), neck_top), (cx + int(r * 0.83), neck_top),
         (cx + int(r * 0.42), neck_bot), (cx - int(r * 0.42), neck_bot)],
        fill=255,
    )
    glass = Image.new("RGBA", (W, H))
    gp = glass.load()
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            c = fill_fn((x - cx) / r, (y - cy) / r)
            for dx in (0, 1):
                for dy in (0, 1):
                    gp[x + dx, y + dy] = c
    img.paste(glass, (0, 0), mask)

    # highlight
    hl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hd.ellipse([cx - int(r * 0.62), cy - int(r * 0.70), cx - int(r * 0.12), cy - int(r * 0.25)], fill=(255, 255, 255, 120))
    hl = hl.filter(ImageFilter.GaussianBlur(6 * S))
    img.alpha_composite(hl)

    # base: collar + threads + tip
    d = ImageDraw.Draw(img)
    bw = int(r * 0.84)
    top = neck_bot
    d.rounded_rectangle([cx - bw // 2 - 2 * S, top, cx + bw // 2 + 2 * S, top + 14 * S], radius=4 * S, fill=(205, 210, 216, 255))
    y = top + 16 * S
    for i in range(3):
        d.rounded_rectangle([cx - bw // 2, y, cx + bw // 2, y + 11 * S], radius=5 * S, fill=(170, 176, 184, 255) if i % 2 == 0 else (140, 146, 154, 255))
        y += 12 * S
    d.pieslice([cx - bw // 4, y - 10 * S, cx + bw // 4, y + 14 * S], 0, 180, fill=(60, 64, 70, 255))

    img.resize((256, 256), Image.LANCZOS).save(out)
    print("wrote", out)


def ftw(nx, ny):
    # tunable white: warm (bottom) to cool (top)
    t = max(0.0, min(1.0, (ny + 1) / 2))
    warm, cool = (255, 196, 120), (225, 238, 255)
    c = tuple(int(cool[i] + (warm[i] - cool[i]) * t) for i in range(3))
    return c + (255,)


def rgbtw(nx, ny):
    # color wheel blended toward white in the center
    ang = (math.atan2(ny, nx) / (2 * math.pi)) % 1.0
    h6 = ang * 6
    i = int(h6) % 6
    f = h6 - int(h6)
    q, t = 1 - f, f
    rgb = [(1, t, 0), (q, 1, 0), (0, 1, t), (0, q, 1), (t, 0, 1), (1, 0, q)][i]
    sat = min(1.0, math.hypot(nx, ny) * 0.95)
    c = tuple(int(255 * (1 - sat + sat * v)) for v in rgb)
    return c + (255,)


out = Path(sys.argv[1])
bulb(ftw, (255, 210, 150), out / "control4-vibrant-ftw.png")
bulb(rgbtw, (200, 170, 255), out / "control4-vibrant-rgbtw.png")
