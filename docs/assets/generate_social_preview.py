# -*- coding: utf-8 -*-
"""
Generate social-preview.png for PandaSpool GitHub repository.
Size: 1280 x 640 (GitHub social preview spec).
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

OUT = Path(__file__).parent / "social-preview.png"
W, H = 1280, 640

# ---------- Color palette (Bambu Lab + dark tech vibe) ----------
BG_TOP   = (15, 18, 24)        # near-black
BG_BOT   = (28, 36, 50)        # deep slate
ACCENT   = (0, 174, 66)        # Bambu green
ACCENT2  = (255, 111, 0)       # 3D-print orange
TEXT     = (240, 242, 245)
MUTED    = (170, 178, 190)
PANEL    = (32, 40, 56, 220)


def font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def cn_font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def draw_gradient(img):
    for y in range(H):
        t = y / H
        r = int(BG_TOP[0] * (1 - t) + BG_BOT[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOT[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOT[2] * t)
        ImageDraw.Draw(img).line([(0, y), (W, y)], fill=(r, g, b))


def draw_panel(d, x, y, w, h, color=PANEL, radius=18):
    d.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=color)


def draw_icon_spool(d, cx, cy, size, color=ACCENT):
    """Top-down spool icon."""
    r = size // 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=4)
    d.ellipse([cx - r // 3, cy - r // 3, cx + r // 3, cy + r // 3], fill=color)
    # filament thread lines
    for ang in range(0, 360, 20):
        import math
        x1 = cx + int(r * 0.45 * math.cos(math.radians(ang)))
        y1 = cy + int(r * 0.45 * math.sin(math.radians(ang)))
        x2 = cx + int(r * 0.92 * math.cos(math.radians(ang)))
        y2 = cy + int(r * 0.92 * math.sin(math.radians(ang)))
        d.line([(x1, y1), (x2, y2)], fill=color, width=2)


def draw_icon_sensor(d, cx, cy, size, color=ACCENT2):
    """Temperature/humidity sensor icon (rounded square + wave)."""
    s = size
    d.rounded_rectangle(
        [cx - s // 2, cy - s // 2, cx + s // 2, cy + s // 2],
        radius=10, outline=color, width=4,
    )
    # bar graph inside
    bar_w = s // 9
    heights = [0.4, 0.7, 0.5, 0.9, 0.6]
    for i, h in enumerate(heights):
        bx = cx - s // 3 + i * (bar_w + 3)
        by_top = cy + s // 4 - int(s * h * 0.4)
        d.rectangle([bx, by_top, bx + bar_w, cy + s // 4], fill=color)


def draw_icon_fan(d, cx, cy, size, color=(120, 180, 255)):
    """Exhaust fan icon."""
    import math
    r = size // 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=4)
    d.ellipse([cx - r // 6, cy - r // 6, cx + r // 6, cy + r // 6], fill=color)
    # 3 fan blades
    for ang in (30, 150, 270):
        x1 = cx + int(r * 0.18 * math.cos(math.radians(ang)))
        y1 = cy + int(r * 0.18 * math.sin(math.radians(ang)))
        x2 = cx + int(r * 0.85 * math.cos(math.radians(ang)))
        y2 = cy + int(r * 0.85 * math.sin(math.radians(ang)))
        d.line([(x1, y1), (x2, y2)], fill=color, width=5)
        d.ellipse([x2 - 6, y2 - 6, x2 + 6, y2 + 6], fill=color)


def draw_printer_silhouette(d, cx, cy, scale=1.0):
    """Stylized 3D printer outline (Bambu X1-ish)."""
    s = int(200 * scale)
    # frame
    d.rounded_rectangle(
        [cx - s, cy - s, cx + s, cy + s],
        radius=12, outline=MUTED, width=3,
    )
    # top gantry
    d.line([(cx - s, cy - s + 30), (cx + s, cy - s + 30)], fill=MUTED, width=4)
    d.line([(cx - s + 30, cy - s + 30), (cx - s + 30, cy - s + 60)], fill=MUTED, width=4)
    d.line([(cx + s - 30, cy - s + 30), (cx + s - 30, cy - s + 60)], fill=MUTED, width=4)
    # build plate
    d.rounded_rectangle(
        [cx - s + 30, cy + 10, cx + s - 30, cy + s - 30],
        radius=6, outline=ACCENT, width=2,
    )
    # a small printed object on the plate
    d.rectangle(
        [cx - 25, cy + s - 60, cx + 25, cy + s - 45], fill=ACCENT2,
    )
    d.polygon(
        [(cx - 25, cy + s - 60), (cx, cy + s - 75), (cx + 25, cy + s - 60)],
        fill=ACCENT2,
    )
    # AMS top block
    d.rounded_rectangle(
        [cx - s + 30, cy - s - 30, cx + s - 30, cy - s],
        radius=4, outline=MUTED, width=2,
    )
    for i in range(4):
        sx = cx - s + 50 + i * 38
        d.rounded_rectangle(
            [sx, cy - s - 22, sx + 30, cy - s - 6], radius=2, outline=ACCENT, width=1,
        )


def main():
    img = Image.new("RGB", (W, H), BG_TOP)
    draw_gradient(img)

    # Soft glow circle behind printer
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([720 - 260, 320 - 260, 720 + 260, 320 + 260], fill=(0, 174, 66, 28))
    glow = glow.filter(ImageFilter.GaussianBlur(60))
    img.paste(glow, (0, 0), glow)

    d = ImageDraw.Draw(img)

    # ===== Left panel: text =====
    # Brand mark
    d.ellipse([60, 50, 130, 120], fill=ACCENT)
    d.text((82, 64), "P", font=font(54, bold=True), fill=(0, 0, 0))

    # Title
    d.text((150, 56), "PandaSpool", font=font(56, bold=True), fill=TEXT)
    d.text((152, 122), "Bambu Lab 3D-Print Ecosystem · Control Hub",
           font=font(20), fill=MUTED)

    # Chinese subtitle (big)
    d.text((60, 175), "拓竹生态自托管中控",
           font=cn_font(38, bold=True), fill=TEXT)

    # Pain-point chips
    chips = [
        ("第三方耗材编号", ACCENT),
        ("机箱环境监控", ACCENT2),
        ("耗材研发实验", (120, 180, 255)),
    ]
    y0 = 245
    for i, (txt, col) in enumerate(chips):
        cy = y0 + i * 60
        draw_panel(d, 60, cy, 460, 48, color=(40, 48, 64, 220), radius=10)
        d.ellipse([76, cy + 14, 96, cy + 34], fill=col)
        d.text((116, cy + 11), txt, font=cn_font(22, bold=True), fill=TEXT)

    # Tech stack line
    d.text((60, 460), "Go 1.22+  ·  SQLite  ·  MQTT  ·  eWeLink  ·  Ezviz  ·  WebGL",
           font=font(18), fill=MUTED)

    # Bottom bar
    d.rectangle([0, H - 50, W, H], fill=(10, 12, 18))
    d.text((60, H - 38), "github.com/aiy365/PandaSpool",
           font=font(18, bold=True), fill=ACCENT)
    d.text((W - 360, H - 38), "MIT License  ·  Self-hosted  ·  Independent",
           font=font(18), fill=MUTED)

    # ===== Right side: printer silhouette + icons =====
    draw_printer_silhouette(d, 990, 340, scale=0.95)

    # 3 feature icons in a row at the bottom of right area
    icon_y = 540
    for i, fn in enumerate([draw_icon_spool, draw_icon_sensor, draw_icon_fan]):
        ix = 800 + i * 130
        fn(d, ix, icon_y, 44)

    img.save(OUT, "PNG", optimize=True)
    print("OK", OUT, OUT.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
