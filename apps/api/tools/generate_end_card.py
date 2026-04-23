"""Render a ~3s branded end card (720x1280 @ 30fps) from a client's branding.json.

Stack: Pillow for per-frame compositing, raw RGB24 piped to ffmpeg for encoding.
No intermediate PNG files.

Usage:
    python tools/generate_end_card.py --client dan-balkun
    python tools/generate_end_card.py --client example-realty --out path.mp4
    python tools/generate_end_card.py --path assets/_fixtures/test-client/branding.json
    python tools/generate_end_card.py --client dan-balkun --force-rebuild --verbose
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import portalocker
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_branding import BrandingError, validate, ASSETS_DIR  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
CACHE_DIR = ROOT / "output" / "_cache" / "end_cards"
LOCK_DIR = ROOT / ".locks"

TEMPLATE_VERSION = 2
MOTION_VARIANT = "subtle_reveal_v2"
RENDERER_ID = "pillow-ffmpeg@1.1"

WIDTH = 720
HEIGHT = 1280
FPS = 30
DURATION_SEC = 3.0
N_FRAMES = int(FPS * DURATION_SEC)

PAD_PCT = 0.08
LOGO_MAX_H_PCT = 0.44
SOCIAL_ICON_SIZE = 76
SOCIAL_ICON_GAP = 38
CONTACT_ICON_SIZE = 32
CONTACT_ICON_GAP = 14
LINE_GAP = 24
GROUP_GAP = 40
SOCIALS_TOP_GAP = 84
DIVIDER_WIDTH_PCT = 0.32
DIVIDER_THICKNESS = 2
DIVIDER_GAP = 30

HEADING_FONT_SIZE = 56
BODY_FONT_SIZE = 38
HANDLE_FONT_SIZE = 28

ASSETS_ROOT = ROOT / "assets"


def hex_to_rgb(hex_str: str) -> tuple:
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def relative_luminance(hex_str: str) -> float:
    """WCAG relative luminance in [0, 1]."""
    def chan(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = hex_to_rgb(hex_str)
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    l1 = relative_luminance(fg_hex)
    l2 = relative_luminance(bg_hex)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def frame_t(frame_idx: int) -> float:
    """Time in seconds of the given frame (at its midpoint)."""
    return (frame_idx + 0.5) / FPS


def animation_state(t: float, row_present: bool, name_present: bool = True) -> dict:
    """Return animation state dict for a given time t (0..3s).

    Keys: logo_scale, logo_opacity, divider_opacity, divider_scale_x,
          name_dy, name_opacity, contact_opacities (list of 3),
          contact_dys (list of 3), socials_opacity, socials_scale
    """
    state = {}

    p = ease_out_cubic((t - 0.00) / 0.40) if t >= 0.00 else 0.0
    p = min(p, 1.0)
    state["logo_scale"] = lerp(0.94, 1.00, p)
    state["logo_opacity"] = lerp(0.0, 1.0, p)

    p = ease_out_cubic((t - 0.40) / 0.30) if t >= 0.40 else 0.0
    p = min(p, 1.0)
    state["divider_opacity"] = lerp(0.0, 1.0, p)
    state["divider_scale_x"] = lerp(0.5, 1.0, p)

    if name_present:
        p = ease_out_cubic((t - 0.50) / 0.30) if t >= 0.50 else 0.0
        p = min(p, 1.0)
        state["name_dy"] = lerp(14.0, 0.0, p)
        state["name_opacity"] = lerp(0.0, 1.0, p)
    else:
        state["name_dy"] = 0.0
        state["name_opacity"] = 0.0

    base_start = 0.62 if name_present else 0.55
    contact_starts = [base_start, base_start + 0.04, base_start + 0.08]
    contact_dur = 0.18
    state["contact_opacities"] = []
    state["contact_dys"] = []
    for s in contact_starts:
        p = ease_out_cubic((t - s) / contact_dur) if t >= s else 0.0
        p = min(p, 1.0)
        state["contact_opacities"].append(lerp(0.0, 1.0, p))
        state["contact_dys"].append(lerp(10.0, 0.0, p))

    if row_present:
        socials_start = base_start + 0.20
        p = ease_out_cubic((t - socials_start) / 0.25) if t >= socials_start else 0.0
        p = min(p, 1.0)
        state["socials_opacity"] = lerp(0.0, 1.0, p)
        state["socials_scale"] = lerp(0.96, 1.00, p)
    else:
        state["socials_opacity"] = 0.0
        state["socials_scale"] = 1.0

    return state


def pick_logo_variant(bg_hex: str, preference: str, light_path: Path, dark_path: Path) -> Path:
    if preference == "light":
        return light_path
    if preference == "dark":
        return dark_path
    return light_path if relative_luminance(bg_hex) > 0.5 else dark_path


def load_logo(path: Path, max_height: int, max_width: int,
              key_white_threshold: int = 240) -> Image.Image:
    """Load logo, convert to RGBA, key out near-white bg if needed, then scale to fit."""
    img = Image.open(path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    alpha = img.split()[3]
    alpha_min, alpha_max = alpha.getextrema()
    if alpha_min == 255 and alpha_max == 255:
        import numpy as np
        arr = np.array(img)
        rgb = arr[:, :, :3]
        near_white = (rgb[:, :, 0] >= key_white_threshold) & \
                     (rgb[:, :, 1] >= key_white_threshold) & \
                     (rgb[:, :, 2] >= key_white_threshold)
        arr[:, :, 3] = np.where(near_white, 0, 255).astype(arr.dtype)
        img = Image.fromarray(arr, "RGBA")

    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    w, h = img.size
    scale = min(max_height / h, max_width / w)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    if (new_w, new_h) != (w, h):
        img = img.resize((new_w, new_h), Image.LANCZOS)
    return img


def load_font(font_path: Path, size: int, variation_name: str | None = None):
    font = ImageFont.truetype(str(font_path), size)
    if variation_name:
        try:
            font.set_variation_by_name(variation_name)
        except Exception:
            pass
    return font


def paste_with_opacity(base: Image.Image, overlay: Image.Image, pos: tuple, opacity: float):
    if opacity <= 0.0:
        return
    if opacity >= 1.0:
        base.alpha_composite(overlay, dest=pos)
        return
    if overlay.mode != "RGBA":
        overlay = overlay.convert("RGBA")
    alpha = overlay.split()[3].point(lambda a: int(a * opacity))
    tmp = overlay.copy()
    tmp.putalpha(alpha)
    base.alpha_composite(tmp, dest=pos)


def format_phone_national(e164: str) -> str:
    import phonenumbers
    try:
        parsed = phonenumbers.parse(e164, None)
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
    except Exception:
        return e164


def text_box(draw: ImageDraw.ImageDraw, text: str, font) -> tuple:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_text_centered(base: Image.Image, text: str, font, y: int, color: tuple, opacity: float, dy: float = 0.0):
    if opacity <= 0.0:
        return
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    w, _h = text_box(dl, text, font)
    x = (base.size[0] - w) // 2
    dl.text((x, int(y + dy)), text, font=font, fill=color)
    if opacity >= 1.0:
        base.alpha_composite(layer)
    else:
        alpha = layer.split()[3].point(lambda a: int(a * opacity))
        layer.putalpha(alpha)
        base.alpha_composite(layer)


def _rounded_mask(size: tuple, radius: int) -> Image.Image:
    """Return an 'L' mode image with a rounded-rect mask (255 inside, 0 outside)."""
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    return mask


def _linear_gradient_rgba(size: tuple, stops: list, angle_deg: float = 135.0) -> Image.Image:
    """Create an RGBA image filled with a linear gradient. Stops: [(t0, (r,g,b,a)), (t1, (r,g,b,a)), ...]."""
    import numpy as np
    w, h = size
    import math
    rad = math.radians(angle_deg)
    dx = math.cos(rad)
    dy = math.sin(rad)

    xs = np.linspace(-0.5, 0.5, w)
    ys = np.linspace(-0.5, 0.5, h)
    xg, yg = np.meshgrid(xs, ys)
    t = (xg * dx + yg * dy)
    tmin, tmax = t.min(), t.max()
    t = (t - tmin) / (tmax - tmin)

    stops = sorted(stops, key=lambda s: s[0])
    out = np.zeros((h, w, 4), dtype=np.float32)
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        mask = (t >= t0) & (t <= t1)
        denom = max(1e-9, (t1 - t0))
        local = (t[mask] - t0) / denom
        for ch in range(4):
            out[..., ch][mask] = c0[ch] + (c1[ch] - c0[ch]) * local

    return Image.fromarray(out.astype("uint8"), "RGBA")


def _tinted_silhouette(text: str, font_path: Path, font_size: int, color: tuple) -> Image.Image:
    font = ImageFont.truetype(str(font_path), font_size)
    try:
        font.set_variation_by_name("Bold")
    except Exception:
        pass
    dummy = Image.new("L", (4, 4))
    dd = ImageDraw.Draw(dummy)
    bbox = dd.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    img = Image.new("RGBA", (max(1, w), max(1, h)), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((-bbox[0], -bbox[1]), text, font=font, fill=color)
    return img


def draw_instagram(size: int) -> Image.Image:
    radius = int(size * 0.24)
    gradient = _linear_gradient_rgba(
        (size, size),
        stops=[
            (0.0, (248, 140,  55, 255)),
            (0.3, (246,  79,  89, 255)),
            (0.6, (220,  45, 150, 255)),
            (1.0, (120,  55, 180, 255)),
        ],
        angle_deg=135.0,
    )
    mask = _rounded_mask((size, size), radius)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    img.paste(gradient, (0, 0), mask=mask)

    d = ImageDraw.Draw(img)
    stroke = max(3, size // 18)
    white = (255, 255, 255, 255)
    r_outer = int(size * 0.22)
    d.rounded_rectangle(
        [int(size * 0.22), int(size * 0.22), int(size * 0.78), int(size * 0.78)],
        radius=r_outer, outline=white, width=stroke,
    )
    cx, cy = size // 2, size // 2
    r_center = int(size * 0.14)
    d.ellipse([cx - r_center, cy - r_center, cx + r_center, cy + r_center], outline=white, width=stroke)
    dr = max(3, size // 22)
    dx = int(cx + size * 0.16)
    dy = int(cy - size * 0.16)
    d.ellipse([dx - dr, dy - dr, dx + dr, dy + dr], fill=white)
    return img


def draw_facebook(size: int) -> Image.Image:
    radius = int(size * 0.24)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mask = _rounded_mask((size, size), radius)
    bg = Image.new("RGBA", (size, size), (24, 119, 242, 255))
    img.paste(bg, (0, 0), mask=mask)
    font_path = ROOT / "assets" / "fonts" / "Manrope-Bold.ttf"
    glyph = _tinted_silhouette("f", font_path, int(size * 0.72), (255, 255, 255, 255))
    gx = (size - glyph.size[0]) // 2
    gy = (size - glyph.size[1]) // 2 - int(size * 0.02)
    img.alpha_composite(glyph, (gx, gy))
    return img


def draw_linkedin(size: int) -> Image.Image:
    radius = int(size * 0.20)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mask = _rounded_mask((size, size), radius)
    bg = Image.new("RGBA", (size, size), (10, 102, 194, 255))
    img.paste(bg, (0, 0), mask=mask)
    font_path = ROOT / "assets" / "fonts" / "Manrope-Bold.ttf"
    glyph = _tinted_silhouette("in", font_path, int(size * 0.48), (255, 255, 255, 255))
    gx = (size - glyph.size[0]) // 2
    gy = (size - glyph.size[1]) // 2 - int(size * 0.02)
    img.alpha_composite(glyph, (gx, gy))
    return img


def draw_youtube(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rect_top = int(size * 0.24)
    rect_bottom = int(size * 0.76)
    radius = int(size * 0.22)
    red = (255, 0, 0, 255)
    bg = Image.new("RGBA", (size, rect_bottom - rect_top), red)
    mask = _rounded_mask((size, rect_bottom - rect_top), radius)
    img.paste(bg, (0, rect_top), mask=mask)
    d = ImageDraw.Draw(img)
    cx = size // 2
    cy = (rect_top + rect_bottom) // 2
    tri_w = int(size * 0.18)
    tri_h = int(size * 0.24)
    d.polygon([(cx - tri_w // 2, cy - tri_h // 2),
               (cx - tri_w // 2, cy + tri_h // 2),
               (cx + tri_w // 2, cy)], fill=(255, 255, 255, 255))
    return img


def draw_tiktok(size: int) -> Image.Image:
    radius = int(size * 0.24)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mask = _rounded_mask((size, size), radius)
    bg = Image.new("RGBA", (size, size), (16, 16, 16, 255))
    img.paste(bg, (0, 0), mask=mask)

    font_path = ROOT / "assets" / "fonts" / "Manrope-Bold.ttf"
    glyph_white = _tinted_silhouette("d", font_path, int(size * 0.62), (255, 255, 255, 255))
    glyph_cyan = _tinted_silhouette("d", font_path, int(size * 0.62), (37, 244, 238, 255))
    glyph_pink = _tinted_silhouette("d", font_path, int(size * 0.62), (254, 44, 85, 255))

    gx = (size - glyph_white.size[0]) // 2
    gy = (size - glyph_white.size[1]) // 2

    img.alpha_composite(glyph_cyan, (gx - 3, gy - 3))
    img.alpha_composite(glyph_pink, (gx + 3, gy + 3))
    img.alpha_composite(glyph_white, (gx, gy))
    return img


def draw_x(size: int) -> Image.Image:
    radius = int(size * 0.24)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mask = _rounded_mask((size, size), radius)
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    img.paste(bg, (0, 0), mask=mask)
    font_path = ROOT / "assets" / "fonts" / "Manrope-Bold.ttf"
    glyph = _tinted_silhouette("X", font_path, int(size * 0.60), (255, 255, 255, 255))
    gx = (size - glyph.size[0]) // 2
    gy = (size - glyph.size[1]) // 2 - int(size * 0.02)
    img.alpha_composite(glyph, (gx, gy))
    return img


ICON_DRAWERS = {
    "instagram": draw_instagram,
    "tiktok":    draw_tiktok,
    "facebook":  draw_facebook,
    "youtube":   draw_youtube,
    "linkedin":  draw_linkedin,
    "x":         draw_x,
}


def draw_phone_icon(size: int, color: tuple) -> Image.Image:
    """Modern smartphone silhouette: rounded portrait rectangle with speaker slit + home dot."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = max(2, size // 12)
    x0 = int(size * 0.30)
    x1 = int(size * 0.70)
    y0 = int(size * 0.08)
    y1 = int(size * 0.92)
    radius = int(size * 0.10)
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, outline=color, width=w)
    cx = size // 2
    slit_w = int(size * 0.14)
    slit_y = int(size * 0.18)
    d.line([(cx - slit_w // 2, slit_y), (cx + slit_w // 2, slit_y)],
           fill=color, width=max(2, w - 1))
    dot_r = max(2, size // 22)
    dot_y = int(size * 0.82)
    d.ellipse([cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r], fill=color)
    return img


def draw_email_icon(size: int, color: tuple) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = max(2, size // 10)
    x0 = int(size * 0.14)
    x1 = int(size * 0.86)
    y0 = int(size * 0.26)
    y1 = int(size * 0.74)
    d.rounded_rectangle([x0, y0, x1, y1], radius=int(size * 0.06), outline=color, width=w)
    mx = (x0 + x1) // 2
    my = int(y0 + (y1 - y0) * 0.44)
    d.line([(x0 + w, y0 + w), (mx, my), (x1 - w, y0 + w)], fill=color, width=w)
    return img


def draw_globe_icon(size: int, color: tuple) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = max(2, size // 12)
    cx, cy = size // 2, size // 2
    r = int(size * 0.36)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=w)
    d.line([(cx, cy - r), (cx, cy + r)], fill=color, width=max(1, w - 1))
    d.line([(cx - r, cy), (cx + r, cy)], fill=color, width=max(1, w - 1))
    er = int(r * 0.58)
    d.arc([cx - er, cy - r, cx + er, cy + r], start=270, end=90, fill=color, width=max(1, w - 1))
    d.arc([cx - er, cy - r, cx + er, cy + r], start=90, end=270, fill=color, width=max(1, w - 1))
    return img


CONTACT_ICON_DRAWERS = {
    "phone":   draw_phone_icon,
    "email":   draw_email_icon,
    "website": draw_globe_icon,
}


def canonicalize_for_hash(doc: dict, logo_bytes: bytes) -> dict:
    logo_sha = hashlib.sha256(logo_bytes).hexdigest()

    socials = {k: v for k, v in doc["social"].items() if v}
    socials = dict(sorted(socials.items()))

    colors = {k: v["hex"] for k, v in doc["visual"]["colors"].items()}

    return {
        "renderer": RENDERER_ID,
        "template_version": TEMPLATE_VERSION,
        "motion_variant": MOTION_VARIANT,
        "identity": {
            "display_name": doc["identity"]["display_name"],
            "industry": doc["identity"]["industry"],
        },
        "contact": {
            "phone_e164": doc["contact"]["phone_e164"],
            "email": doc["contact"]["email"],
            "website": doc["contact"]["website"],
        },
        "socials": socials,
        "colors": colors,
        "background_preference": doc["visual"]["colors"]["background"].get("preference", "auto"),
        "typography": {
            "heading_family": doc["typography"]["heading"]["family"],
            "body_family": doc["typography"]["body"]["family"],
        },
        "logo_sha256": logo_sha,
        "output": {"w": WIDTH, "h": HEIGHT, "fps": FPS, "duration": DURATION_SEC},
    }


def cache_key_hash(canon: dict) -> str:
    s = json.dumps(canon, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def cache_paths(slug: str, hash16: str) -> tuple:
    cache_client_dir = CACHE_DIR / slug
    cache_client_dir.mkdir(parents=True, exist_ok=True)
    name = f"{slug}__v{TEMPLATE_VERSION}__subtle__{hash16}"
    return cache_client_dir / f"{name}.mp4", cache_client_dir / f"{name}.json"


def atomic_copy(src: Path, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=dest.parent, delete=False, prefix=".tmp_", suffix=".mp4"
    ) as tf:
        tmp = Path(tf.name)
    shutil.copyfile(src, tmp)
    tmp.replace(dest)


def measure_layout(doc: dict, fonts: dict, logo_size: tuple) -> dict:
    """Pre-compute heights and y-positions so the block is vertically centered."""
    dummy = Image.new("RGBA", (10, 10))
    dd = ImageDraw.Draw(dummy)

    name_present = doc["identity"].get("show_display_name_on_card", True)
    display_name = doc["identity"]["display_name"]
    phone_display = format_phone_national(doc["contact"]["phone_e164"])
    email_display = doc["contact"]["email"]
    website_display = doc["contact"]["website"]

    _, name_h = text_box(dd, display_name, fonts["heading"])
    _, phone_h = text_box(dd, phone_display, fonts["body"])
    _, email_h = text_box(dd, email_display, fonts["body"])
    _, web_h = text_box(dd, website_display, fonts["body"])

    row_h = max(CONTACT_ICON_SIZE, phone_h)
    email_row_h = max(CONTACT_ICON_SIZE, email_h)
    web_row_h = max(CONTACT_ICON_SIZE, web_h)

    logo_h = logo_size[1]
    socials_present = any(v for v in doc["social"].values())
    socials_h = SOCIAL_ICON_SIZE if socials_present else 0

    total_h = logo_h + DIVIDER_GAP + DIVIDER_THICKNESS + DIVIDER_GAP
    if name_present:
        total_h += name_h + GROUP_GAP
    total_h += row_h + LINE_GAP + email_row_h + LINE_GAP + web_row_h
    if socials_present:
        total_h += SOCIALS_TOP_GAP + socials_h

    top_y = max(int(HEIGHT * PAD_PCT), (HEIGHT - total_h) // 2)

    logo_y = top_y
    divider_y = logo_y + logo_h + DIVIDER_GAP
    cursor = divider_y + DIVIDER_THICKNESS + DIVIDER_GAP

    name_y = cursor if name_present else None
    if name_present:
        cursor += name_h + GROUP_GAP

    phone_y = cursor
    cursor += row_h + LINE_GAP
    email_y = cursor
    cursor += email_row_h + LINE_GAP
    web_y = cursor
    cursor += web_row_h

    socials_y = cursor + SOCIALS_TOP_GAP if socials_present else None

    return {
        "name_present": name_present,
        "display_name": display_name,
        "phone_display": phone_display,
        "email_display": email_display,
        "website_display": website_display,
        "name_h": name_h,
        "phone_h": phone_h,
        "email_h": email_h,
        "web_h": web_h,
        "logo_y": logo_y,
        "divider_y": divider_y,
        "name_y": name_y,
        "phone_y": phone_y,
        "email_y": email_y,
        "web_y": web_y,
        "socials_y": socials_y,
        "socials_present": socials_present,
    }


def _draw_contact_row(base: Image.Image, icon_img: Image.Image, text: str, font,
                      y: int, color: tuple, opacity: float, dy: float):
    """Render a row with [icon] [text] centered horizontally as a group."""
    if opacity <= 0.0:
        return
    dummy = Image.new("RGBA", (4, 4))
    dd = ImageDraw.Draw(dummy)
    bbox = dd.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    icon_w, icon_h = icon_img.size
    row_w = icon_w + CONTACT_ICON_GAP + text_w
    row_h = max(icon_h, text_h)
    x0 = (base.size[0] - row_w) // 2

    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)

    icon_y = int(y + dy + (row_h - icon_h) // 2)
    layer.alpha_composite(icon_img, (x0, icon_y))

    text_x = x0 + icon_w + CONTACT_ICON_GAP - bbox[0]
    text_y = int(y + dy + (row_h - text_h) // 2 - bbox[1])
    ld.text((text_x, text_y), text, font=font, fill=color)

    _compose_with_opacity(base, layer, opacity)


def build_text_block(base: Image.Image, layout: dict, fonts: dict, colors: dict,
                     contact_icons: dict, state: dict):
    """Draw the name (optional) + 3 contact rows with icons using pre-computed y-positions."""
    fg = colors["foreground"] + (255,)

    if layout["name_present"] and layout["name_y"] is not None:
        draw_text_centered(base, layout["display_name"], fonts["heading"], layout["name_y"], fg,
                           state["name_opacity"], state["name_dy"])

    _draw_contact_row(base, contact_icons["phone"], layout["phone_display"], fonts["body"],
                      layout["phone_y"], fg, state["contact_opacities"][0], state["contact_dys"][0])
    _draw_contact_row(base, contact_icons["email"], layout["email_display"], fonts["body"],
                      layout["email_y"], fg, state["contact_opacities"][1], state["contact_dys"][1])
    _draw_contact_row(base, contact_icons["website"], layout["website_display"], fonts["body"],
                      layout["web_y"], fg, state["contact_opacities"][2], state["contact_dys"][2])


def build_socials_row(base: Image.Image, socials: dict, social_icons: dict,
                      top_y: int, state: dict):
    """Render brand-colored social icons, centered, evenly spaced."""
    present = [(k, v) for k, v in socials.items() if v and k in ICON_DRAWERS]
    if not present:
        return
    if state["socials_opacity"] <= 0.0:
        return

    total_w = SOCIAL_ICON_SIZE * len(present) + SOCIAL_ICON_GAP * (len(present) - 1)
    x_cursor = (base.size[0] - total_w) // 2

    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    scale = state["socials_scale"]
    for platform, _handle in present:
        icon = social_icons[platform]
        s = max(1, int(SOCIAL_ICON_SIZE * scale))
        icon_scaled = icon.resize((s, s), Image.LANCZOS)
        offset = (SOCIAL_ICON_SIZE - s) // 2
        layer.alpha_composite(icon_scaled, (x_cursor + offset, top_y + offset))
        x_cursor += SOCIAL_ICON_SIZE + SOCIAL_ICON_GAP

    _compose_with_opacity(base, layer, state["socials_opacity"])


def _build_background(colors: dict) -> Image.Image:
    """Subtle vertical gradient from the background color to ~4% darker at the bottom."""
    import numpy as np
    top = colors["background"]
    bottom = tuple(max(0, int(c * 0.96)) for c in top)
    arr = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for i, (t_ch, b_ch) in enumerate(zip(top, bottom)):
        col = np.linspace(t_ch, b_ch, HEIGHT).astype(np.uint8)
        arr[..., i] = col[:, None]
    return Image.fromarray(arr, "RGB").convert("RGBA")


def _draw_divider(base: Image.Image, y: int, color: tuple, scale_x: float, opacity: float):
    if opacity <= 0.0 or scale_x <= 0.0:
        return
    full_w = int(base.size[0] * DIVIDER_WIDTH_PCT)
    w = max(2, int(full_w * scale_x))
    x0 = (base.size[0] - w) // 2
    x1 = x0 + w
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rectangle([x0, y, x1, y + DIVIDER_THICKNESS], fill=color + (255,))
    _compose_with_opacity(base, layer, opacity)


def _compose_with_opacity(base: Image.Image, layer: Image.Image, opacity: float):
    if opacity >= 1.0:
        base.alpha_composite(layer)
        return
    alpha = layer.split()[3].point(lambda a: int(a * opacity))
    layer.putalpha(alpha)
    base.alpha_composite(layer)


def render_frame(t: float, doc: dict, resources: dict) -> Image.Image:
    colors = resources["colors"]
    base = resources["background"].copy()

    layout = resources["layout"]
    state = animation_state(t, layout["socials_present"], layout["name_present"])

    logo = resources["logo"]
    logo_w, logo_h = logo.size
    scale = state["logo_scale"]
    sw = max(1, int(logo_w * scale))
    sh = max(1, int(logo_h * scale))
    logo_scaled = logo.resize((sw, sh), Image.LANCZOS)

    logo_x = (WIDTH - sw) // 2
    logo_y = layout["logo_y"] + (logo_h - sh) // 2
    paste_with_opacity(base, logo_scaled, (logo_x, logo_y), state["logo_opacity"])

    _draw_divider(base, layout["divider_y"], colors["accent"],
                  state["divider_scale_x"], state["divider_opacity"])

    fonts = resources["fonts"]
    contact_icons = resources["contact_icons"]
    build_text_block(base, layout, fonts, colors, contact_icons, state)

    if layout["socials_present"]:
        build_socials_row(base, doc["social"], resources["social_icons"],
                          layout["socials_y"], state)

    return base.convert("RGB")


def preflight_contrast(frame: Image.Image, doc: dict, colors: dict, strict: bool) -> list:
    """Basic WCAG contrast check on the background vs the foreground text color."""
    warnings = []
    bg_hex = doc["visual"]["colors"]["background"]["hex"]
    fg_hex = doc["visual"]["colors"]["foreground"]["hex"]
    ratio = contrast_ratio(fg_hex, bg_hex)
    msg = f"Contrast (foreground vs background): {ratio:.2f}:1"
    if ratio < 4.5:
        warnings.append(f"{msg} — below WCAG AA (4.5:1) for normal text.")
        if strict:
            raise BrandingError(f"Strict contrast check failed. {msg}")
    return warnings


def ffmpeg_encode(frames_iter, output_path: Path, verbose: bool = False):
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS),
        "-i", "pipe:0",
        "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-profile:v", "high", "-level", "4.0", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-shortest",
        "-movflags", "+faststart",
        "-t", f"{DURATION_SEC}",
        str(output_path),
    ]
    stderr = None if verbose else subprocess.DEVNULL
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=stderr)
    try:
        for frame in frames_iter:
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        ret = proc.wait()
        if ret != 0:
            raise RuntimeError(f"ffmpeg exited with code {ret}")
    except Exception:
        proc.kill()
        raise


def load_resources(doc: dict, base_dir: Path) -> dict:
    colors = {
        name: hex_to_rgb(doc["visual"]["colors"][name]["hex"])
        for name in ("primary", "secondary", "accent", "background", "foreground")
    }

    logo_variant = pick_logo_variant(
        doc["visual"]["colors"]["background"]["hex"],
        doc["visual"]["colors"]["background"].get("preference", "auto"),
        base_dir / doc["visual"]["logo"]["light_bg_path"],
        base_dir / doc["visual"]["logo"]["dark_bg_path"],
    )
    logo_bytes = logo_variant.read_bytes()
    max_logo_h = int(HEIGHT * LOGO_MAX_H_PCT)
    max_logo_w = int(WIDTH * 0.86)
    logo = load_logo(logo_variant, max_logo_h, max_logo_w)

    heading_path = base_dir / doc["typography"]["heading"]["file_path"]
    body_path = base_dir / doc["typography"]["body"]["file_path"]
    fonts = {
        "heading": load_font(heading_path, HEADING_FONT_SIZE, variation_name="Bold"),
        "body":    load_font(body_path, BODY_FONT_SIZE, variation_name="Medium"),
        "handle":  load_font(body_path, HANDLE_FONT_SIZE, variation_name="Medium"),
    }

    layout = measure_layout(doc, fonts, logo.size)
    background = _build_background(colors)

    accent_icon_color = colors["accent"] + (255,)
    contact_icons = {
        "phone":   draw_phone_icon(CONTACT_ICON_SIZE, accent_icon_color),
        "email":   draw_email_icon(CONTACT_ICON_SIZE, accent_icon_color),
        "website": draw_globe_icon(CONTACT_ICON_SIZE, accent_icon_color),
    }

    present_socials = {k for k, v in doc["social"].items() if v and k in ICON_DRAWERS}
    social_icons = {k: ICON_DRAWERS[k](SOCIAL_ICON_SIZE) for k in present_socials}

    return {
        "colors": colors,
        "logo": logo,
        "logo_bytes": logo_bytes,
        "fonts": fonts,
        "layout": layout,
        "background": background,
        "contact_icons": contact_icons,
        "social_icons": social_icons,
    }


def render(source: Path, out_path: Path, strict_contrast: bool = False,
           no_cache: bool = False, force_rebuild: bool = False, verbose: bool = False) -> dict:
    t0 = time.time()

    doc = validate(source, strict_slug_match=False)
    base_dir = source.parent

    resources = load_resources(doc, base_dir)

    canon = canonicalize_for_hash(doc, resources["logo_bytes"])
    hash16 = cache_key_hash(canon)
    cache_video_path, cache_meta_path = cache_paths(doc["slug"], hash16)

    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = LOCK_DIR / f"{hash16}.lock"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with portalocker.Lock(str(lock_file), timeout=120):
        if not no_cache and not force_rebuild and cache_video_path.exists():
            atomic_copy(cache_video_path, out_path)
            elapsed = time.time() - t0
            return {
                "status": "cache_hit",
                "hash": hash16,
                "cache_path": cache_video_path,
                "out_path": out_path,
                "elapsed_s": elapsed,
            }

        test_frame = render_frame(0.5, doc, resources)
        warnings = preflight_contrast(test_frame, doc, resources["colors"], strict_contrast)
        for w in warnings:
            print(f"  warn: {w}")

        def frames_iter():
            for i in range(N_FRAMES):
                t = frame_t(i)
                yield render_frame(t, doc, resources)

        with tempfile.NamedTemporaryFile(
            dir=cache_video_path.parent, delete=False, prefix=".tmp_", suffix=".mp4"
        ) as tf:
            tmp_out = Path(tf.name)

        try:
            ffmpeg_encode(frames_iter(), tmp_out, verbose=verbose)
            tmp_out.replace(cache_video_path)

            meta = {
                "hash": hash16,
                "rendered_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "canon": canon,
            }
            cache_meta_path.write_text(json.dumps(meta, indent=2))

            atomic_copy(cache_video_path, out_path)
        except Exception:
            tmp_out.unlink(missing_ok=True)
            raise

    elapsed = time.time() - t0
    return {
        "status": "rendered",
        "hash": hash16,
        "cache_path": cache_video_path,
        "out_path": out_path,
        "elapsed_s": elapsed,
    }


def resolve_source_path(args) -> Path:
    if args.path:
        return Path(args.path)
    if args.client:
        return ASSETS_DIR / args.client / "branding.json"
    raise ValueError("Must provide --client or --path")


def main():
    parser = argparse.ArgumentParser(description="Render a client's 3s branded end card")
    parser.add_argument("--client", help="Client slug (reads assets/{slug}/branding.json)")
    parser.add_argument("--path", help="Direct path to a branding.json")
    parser.add_argument("--out", default=None, help="Output path (default: output/{slug}/end_cards/latest.mp4)")
    parser.add_argument("--layout", default="centered_stack", choices=["centered_stack"],
                        help="Layout template (Phase 1 only supports centered_stack)")
    parser.add_argument("--motion", default="subtle", choices=["subtle"],
                        help="Motion style (Phase 1 only supports subtle)")
    parser.add_argument("--strict-contrast", action="store_true", help="Fail render on WCAG <4.5:1")
    parser.add_argument("--no-cache", action="store_true", help="Render fresh; don't read cache")
    parser.add_argument("--force-rebuild", action="store_true", help="Render fresh and overwrite cache")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    try:
        source = resolve_source_path(args)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    if not source.exists():
        print(f"Error: branding file not found: {source}", file=sys.stderr)
        sys.exit(2)

    slug_hint = source.parent.name
    out_path = Path(args.out) if args.out else OUTPUT_DIR / slug_hint / "end_cards" / "latest.mp4"

    print(f"End card render")
    print(f"  source:   {source}")
    print(f"  output:   {out_path}")

    try:
        result = render(
            source,
            out_path,
            strict_contrast=args.strict_contrast,
            no_cache=args.no_cache,
            force_rebuild=args.force_rebuild,
            verbose=args.verbose,
        )
    except BrandingError as e:
        print(f"Branding error:\n{e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Render error: {e}", file=sys.stderr)
        sys.exit(1)

    status_label = "CACHE HIT" if result["status"] == "cache_hit" else "RENDERED "
    size_mb = result["out_path"].stat().st_size / 1024 / 1024
    print(f"\n{status_label} {result['hash']}")
    print(f"  cache:    {result['cache_path']}")
    print(f"  wrote:    {result['out_path']} ({size_mb:.2f} MB)")
    print(f"  elapsed:  {result['elapsed_s']:.2f}s")


if __name__ == "__main__":
    main()
