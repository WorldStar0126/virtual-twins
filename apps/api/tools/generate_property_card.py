"""Render a RISE-style Open House property card (1080x1920 @ 30fps, 3s MP4).

Design port of `RISE Open House End Card.html` from Claude Design. The layout is
photo-hero: property photo fills the top ~40%, an "Open House" pill badge straddles
the photo/content seam, followed by logo, address, SAT/SUN date columns, agent
attribution with phone, and brand-colored social icons along the bottom.

Usage:
    python tools/generate_property_card.py --client james-duffer \\
        --property-photo "assets/james-duffer/photos/17 kieth drive exterior.jpg" \\
        --address "17 Keith Drive" --city "Hopkinton, RI" \\
        --agent-name "James Duffer" \\
        --date1-day SAT --date1-date "April 18" --date1-time "10:30 AM - 12 PM" \\
        --date2-day SUN --date2-date "April 19" --date2-time "10:30 AM - 12 PM"
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_end_card import (  # noqa: E402
    ICON_DRAWERS,
    format_phone_national,
    hex_to_rgb,
)

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONTS_DIR = ASSETS / "fonts"

WIDTH = 1080
HEIGHT = 1920
FPS = 30
DURATION_SEC = 3.0
N_FRAMES = int(FPS * DURATION_SEC)

PHOTO_HEIGHT = 760
PHOTO_FADE_H = 120
BADGE_TOP = 680
CONTENT_TOP = 800
CONTENT_PAD_X = 60

LOGO_HEIGHT = 90
LOGO_MARGIN_BOTTOM = 36

ADDRESS_SIZE = 96
ADDRESS_MARGIN_BOTTOM = 18
CITY_SIZE = 36
CITY_LETTER_SPACING_EM = 0.20
ADDRESS_BLOCK_MARGIN_BOTTOM = 84

DATE_COL_GAP = 64
DAY_SIZE = 26
DAY_LETTER_SPACING_EM = 0.38
DATE_SIZE = 64
TIME_SIZE = 30
DATE_ITEM_GAP = 14
TIME_MARGIN_TOP = 6
DATES_MARGIN_BOTTOM = 64

LISTED_BY_SIZE = 22
LISTED_BY_LETTER_SPACING_EM = 0.32
AGENT_NAME_SIZE = 64
PHONE_SIZE = 44
AGENT_ITEM_GAP = 14
PHONE_MARGIN_TOP = 10

BADGE_TEXT = "OPEN HOUSE"
BADGE_FONT_SIZE = 26
BADGE_LETTER_SPACING_EM = 0.34
BADGE_PAD_X = 32
BADGE_PAD_Y = 18
BADGE_DOT_SIZE = 10
BADGE_DOT_GAP = 14
BADGE_SHADOW_BLUR = 30
BADGE_SHADOW_OFFSET = 10

SOCIAL_ICON_SIZE = 64
SOCIAL_GAP = 32
SOCIAL_BOTTOM = 70

BG_COLOR = (255, 255, 255)

ACCENTS = {
    "navy":     {"primary": "#2d3f52", "ink": "#121821", "soft": "#6b86a8"},
    "charcoal": {"primary": "#1a1a1a", "ink": "#0a0a0a", "soft": "#6f6f6f"},
}

FONT_CORMORANT = FONTS_DIR / "CormorantGaramond-VF.ttf"
FONT_CORMORANT_ITALIC = FONTS_DIR / "CormorantGaramond-Italic-VF.ttf"
FONT_INTER = FONTS_DIR / "Inter-Medium.ttf"
FONT_JBM = FONTS_DIR / "JetBrainsMono-VF.ttf"


# ── Math ────────────────────────────────────────────────────────────────────
def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def ease_out_expo(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    if t >= 1.0:
        return 1.0
    return 1 - pow(2, -10 * t)


# ── Fonts ───────────────────────────────────────────────────────────────────
def load_variable_font(path: Path, size: int, variation: str | None = None):
    font = ImageFont.truetype(str(path), size)
    if variation:
        try:
            font.set_variation_by_name(variation)
        except Exception:
            pass
    return font


# ── Letter-spaced text ──────────────────────────────────────────────────────
def measure_letter_spaced(text: str, font: ImageFont.FreeTypeFont, tracking_px: int) -> tuple[int, int, int]:
    """Return (width, height, baseline_offset_y) for tracked text.

    baseline_offset_y is the negative top of the bbox (distance from the drawing
    origin down to the glyph top).
    """
    dummy = Image.new("L", (4, 4))
    dd = ImageDraw.Draw(dummy)
    if not text:
        return 0, 0, 0

    total_w = 0
    max_top = 0
    max_bottom = 0
    chars = list(text)
    for i, ch in enumerate(chars):
        bbox = dd.textbbox((0, 0), ch, font=font)
        ch_w = bbox[2] - bbox[0]
        total_w += ch_w
        max_top = min(max_top, bbox[1])
        max_bottom = max(max_bottom, bbox[3])
        if i < len(chars) - 1:
            total_w += tracking_px
    return total_w, max_bottom - max_top, -max_top


def draw_letter_spaced(layer: Image.Image, x: int, y: int, text: str,
                       font: ImageFont.FreeTypeFont, tracking_px: int,
                       color: tuple) -> int:
    """Draw `text` at (x, y-top) with extra spacing between chars. Returns total width drawn."""
    d = ImageDraw.Draw(layer)
    cursor = x
    total = 0
    for i, ch in enumerate(text):
        bbox = d.textbbox((0, 0), ch, font=font)
        ch_w = bbox[2] - bbox[0]
        # draw.text uses the glyph bbox's left; subtract bbox[0] so we land at `cursor`.
        d.text((cursor - bbox[0], y), ch, font=font, fill=color)
        cursor += ch_w
        total += ch_w
        if i < len(text) - 1:
            cursor += tracking_px
            total += tracking_px
    return total


def text_bbox(text: str, font: ImageFont.FreeTypeFont) -> tuple:
    dummy = Image.new("L", (4, 4))
    bbox = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)
    return bbox


# ── Image helpers ───────────────────────────────────────────────────────────
def cover_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Scale `img` with object-fit: cover to (target_w, target_h)."""
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(round(src_w * scale))
    new_h = int(round(src_h * scale))
    img_scaled = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img_scaled.crop((left, top, left + target_w, top + target_h))


def build_photo_frame(base_photo: Image.Image, kb_scale: float) -> Image.Image:
    """Return an RGBA image sized (WIDTH, PHOTO_HEIGHT) with the photo zoomed by kb_scale
    (cover fit, center crop) and a bottom gradient fade to white."""
    zw = int(round(WIDTH * kb_scale))
    zh = int(round(PHOTO_HEIGHT * kb_scale))
    zoomed = cover_crop(base_photo, zw, zh)
    left = (zw - WIDTH) // 2
    top = (zh - PHOTO_HEIGHT) // 2
    cropped = zoomed.crop((left, top, left + WIDTH, top + PHOTO_HEIGHT)).convert("RGBA")

    # Bottom gradient fade: transparent→white across PHOTO_FADE_H pixels at bottom.
    grad = Image.new("RGBA", (WIDTH, PHOTO_FADE_H), (255, 255, 255, 0))
    gp = grad.load()
    for yy in range(PHOTO_FADE_H):
        a = int(round(255 * (yy / (PHOTO_FADE_H - 1))))
        for xx in range(WIDTH):
            gp[xx, yy] = (255, 255, 255, a)
    cropped.alpha_composite(grad, (0, PHOTO_HEIGHT - PHOTO_FADE_H))
    return cropped


def build_logo(path: Path, max_h: int, max_w: int) -> Image.Image:
    """Load logo, key out near-white, crop to content, scale to fit max_h within max_w."""
    img = Image.open(path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    alpha = img.split()[3]
    alpha_min, alpha_max = alpha.getextrema()
    if alpha_min == 255 and alpha_max == 255:
        import numpy as np
        arr = np.array(img)
        rgb = arr[:, :, :3]
        near_white = (rgb[:, :, 0] >= 240) & (rgb[:, :, 1] >= 240) & (rgb[:, :, 2] >= 240)
        arr[:, :, 3] = np.where(near_white, 0, 255).astype(arr.dtype)
        img = Image.fromarray(arr, "RGBA")

    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    w, h = img.size
    scale = min(max_h / h, max_w / w)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    return img.resize((new_w, new_h), Image.LANCZOS)


# ── Static layer builders (built once, composited per-frame) ────────────────
def build_badge_layer(accent_primary_rgb: tuple) -> Image.Image:
    """Render the 'OPEN HOUSE' pill on a transparent layer sized to include soft shadow."""
    font = load_variable_font(FONT_JBM, BADGE_FONT_SIZE, "Medium")
    tracking = int(round(BADGE_FONT_SIZE * BADGE_LETTER_SPACING_EM))
    text_w, text_h, text_top = measure_letter_spaced(BADGE_TEXT, font, tracking)

    content_w = BADGE_DOT_SIZE + BADGE_DOT_GAP + text_w
    content_h = max(BADGE_DOT_SIZE, text_h)
    pill_w = content_w + BADGE_PAD_X * 2
    pill_h = content_h + BADGE_PAD_Y * 2
    radius = pill_h // 2

    pad = BADGE_SHADOW_BLUR + BADGE_SHADOW_OFFSET
    layer_w = pill_w + pad * 2
    layer_h = pill_h + pad * 2
    layer = Image.new("RGBA", (layer_w, layer_h), (0, 0, 0, 0))

    from PIL import ImageFilter
    shadow = Image.new("RGBA", (layer_w, layer_h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        [pad, pad + BADGE_SHADOW_OFFSET, pad + pill_w, pad + pill_h + BADGE_SHADOW_OFFSET],
        radius=radius,
        fill=(*accent_primary_rgb, int(0.22 * 255)),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(BADGE_SHADOW_BLUR / 2))
    layer.alpha_composite(shadow)

    pill = Image.new("RGBA", (layer_w, layer_h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pill)
    pd.rounded_rectangle(
        [pad, pad, pad + pill_w, pad + pill_h],
        radius=radius,
        fill=(*accent_primary_rgb, 255),
    )
    layer.alpha_composite(pill)

    content_x = pad + BADGE_PAD_X
    content_y_center = pad + pill_h // 2

    dot_x = content_x
    dot_y = content_y_center - BADGE_DOT_SIZE // 2
    dd = ImageDraw.Draw(layer)
    dd.ellipse(
        [dot_x, dot_y, dot_x + BADGE_DOT_SIZE, dot_y + BADGE_DOT_SIZE],
        fill=(255, 255, 255, int(0.9 * 255)),
    )

    text_x = content_x + BADGE_DOT_SIZE + BADGE_DOT_GAP
    text_y = content_y_center - text_h // 2 + text_top
    draw_letter_spaced(layer, text_x, text_y, BADGE_TEXT, font, tracking, (255, 255, 255, 255))

    return layer


def build_content_layers(branding_logo_path: Path, address: str, city: str,
                         dates: list[dict], agent_name: str, phone_display: str,
                         accent: dict) -> dict:
    """Build individual RGBA layers (width=WIDTH) for each content row, so the render
    loop can composite them with per-row opacity + translateY."""
    ink_rgb = hex_to_rgb(accent["ink"])
    soft_rgb = hex_to_rgb(accent["soft"])
    primary_rgb = hex_to_rgb(accent["primary"])

    content_w = WIDTH - CONTENT_PAD_X * 2

    # Logo row
    logo_img = build_logo(branding_logo_path, LOGO_HEIGHT, content_w)
    logo_layer = Image.new("RGBA", (WIDTH, LOGO_HEIGHT), (0, 0, 0, 0))
    lx = (WIDTH - logo_img.size[0]) // 2
    ly = (LOGO_HEIGHT - logo_img.size[1]) // 2
    logo_layer.alpha_composite(logo_img, (lx, ly))

    # Address block (address + city), wrapped together because they share one FadeUp in the design.
    addr_font = load_variable_font(FONT_CORMORANT, ADDRESS_SIZE, "Medium")
    city_font = load_variable_font(FONT_INTER, CITY_SIZE)

    addr_bbox = text_bbox(address, addr_font)
    addr_w = addr_bbox[2] - addr_bbox[0]
    addr_h = addr_bbox[3] - addr_bbox[1]
    addr_baseline_top = -addr_bbox[1]

    city_upper = city.upper()
    city_tracking = int(round(CITY_SIZE * CITY_LETTER_SPACING_EM))
    city_w, city_h, city_top = measure_letter_spaced(city_upper, city_font, city_tracking)

    addr_block_h = addr_h + ADDRESS_MARGIN_BOTTOM + city_h
    addr_layer = Image.new("RGBA", (WIDTH, addr_block_h), (0, 0, 0, 0))
    ad = ImageDraw.Draw(addr_layer)
    addr_x = (WIDTH - addr_w) // 2 - addr_bbox[0]
    ad.text((addr_x, addr_baseline_top), address, font=addr_font, fill=(*ink_rgb, 255))
    city_x = (WIDTH - city_w) // 2
    city_y = addr_h + ADDRESS_MARGIN_BOTTOM + city_top
    draw_letter_spaced(addr_layer, city_x, city_y, city_upper, city_font, city_tracking,
                       (*soft_rgb, 255))

    # Dates row: two columns centered with gap
    day_font = load_variable_font(FONT_JBM, DAY_SIZE, "Medium")
    date_font = load_variable_font(FONT_CORMORANT, DATE_SIZE, "Medium")
    time_font = load_variable_font(FONT_INTER, TIME_SIZE)

    day_tracking = int(round(DAY_SIZE * DAY_LETTER_SPACING_EM))

    def build_date_col(entry: dict) -> Image.Image:
        day_upper = entry["day"].upper()
        day_w, day_h, day_top = measure_letter_spaced(day_upper, day_font, day_tracking)
        date_bbox = text_bbox(entry["date"], date_font)
        date_w = date_bbox[2] - date_bbox[0]
        date_h = date_bbox[3] - date_bbox[1]
        date_baseline_top = -date_bbox[1]
        time_bbox = text_bbox(entry["time"], time_font)
        time_w = time_bbox[2] - time_bbox[0]
        time_h = time_bbox[3] - time_bbox[1]
        time_baseline_top = -time_bbox[1]

        col_w = max(day_w, date_w, time_w)
        col_h = day_h + DATE_ITEM_GAP + date_h + TIME_MARGIN_TOP + time_h
        col = Image.new("RGBA", (col_w, col_h), (0, 0, 0, 0))
        cy = 0
        draw_letter_spaced(col, (col_w - day_w) // 2, cy + day_top, day_upper, day_font,
                           day_tracking, (*soft_rgb, 255))
        cy += day_h + DATE_ITEM_GAP
        cd = ImageDraw.Draw(col)
        cd.text(((col_w - date_w) // 2 - date_bbox[0], cy + date_baseline_top),
                entry["date"], font=date_font, fill=(*ink_rgb, 255))
        cy += date_h + TIME_MARGIN_TOP
        cd.text(((col_w - time_w) // 2 - time_bbox[0], cy + time_baseline_top),
                entry["time"], font=time_font, fill=(*ink_rgb, 255))
        return col

    date_cols = [build_date_col(e) for e in dates]
    dates_total_w = sum(c.size[0] for c in date_cols) + DATE_COL_GAP * (len(date_cols) - 1)
    dates_max_h = max(c.size[1] for c in date_cols)
    dates_layer = Image.new("RGBA", (WIDTH, dates_max_h), (0, 0, 0, 0))
    dx = (WIDTH - dates_total_w) // 2
    for col in date_cols:
        dy = (dates_max_h - col.size[1]) // 2
        dates_layer.alpha_composite(col, (dx, dy))
        dx += col.size[0] + DATE_COL_GAP

    # Agent block: "Listed by" / agent name (italic serif) / phone
    listed_font = load_variable_font(FONT_JBM, LISTED_BY_SIZE, "Medium")
    agent_font = load_variable_font(FONT_CORMORANT_ITALIC, AGENT_NAME_SIZE, "Medium Italic")
    phone_font = load_variable_font(FONT_INTER, PHONE_SIZE)

    listed_upper = "LISTED BY"
    listed_tracking = int(round(LISTED_BY_SIZE * LISTED_BY_LETTER_SPACING_EM))
    listed_w, listed_h, listed_top = measure_letter_spaced(listed_upper, listed_font,
                                                            listed_tracking)

    agent_bbox = text_bbox(agent_name, agent_font)
    agent_w = agent_bbox[2] - agent_bbox[0]
    agent_h = agent_bbox[3] - agent_bbox[1]
    agent_baseline_top = -agent_bbox[1]

    phone_bbox = text_bbox(phone_display, phone_font)
    phone_w = phone_bbox[2] - phone_bbox[0]
    phone_h = phone_bbox[3] - phone_bbox[1]
    phone_baseline_top = -phone_bbox[1]

    agent_block_h = (listed_h + AGENT_ITEM_GAP + agent_h + PHONE_MARGIN_TOP + phone_h)
    agent_layer = Image.new("RGBA", (WIDTH, agent_block_h), (0, 0, 0, 0))
    y = 0
    draw_letter_spaced(agent_layer, (WIDTH - listed_w) // 2, y + listed_top, listed_upper,
                       listed_font, listed_tracking, (*soft_rgb, 255))
    y += listed_h + AGENT_ITEM_GAP
    agd = ImageDraw.Draw(agent_layer)
    agd.text(((WIDTH - agent_w) // 2 - agent_bbox[0], y + agent_baseline_top),
             agent_name, font=agent_font, fill=(*ink_rgb, 255))
    y += agent_h + PHONE_MARGIN_TOP
    agd.text(((WIDTH - phone_w) // 2 - phone_bbox[0], y + phone_baseline_top),
             phone_display, font=phone_font, fill=(*primary_rgb, 255))

    # Compute absolute y-offsets for each row.
    y_logo = CONTENT_TOP
    y_addr = y_logo + LOGO_HEIGHT + LOGO_MARGIN_BOTTOM
    y_dates = y_addr + addr_block_h + ADDRESS_BLOCK_MARGIN_BOTTOM
    y_agent = y_dates + dates_max_h + DATES_MARGIN_BOTTOM

    return {
        "logo": {"img": logo_layer, "y": y_logo},
        "address": {"img": addr_layer, "y": y_addr},
        "dates": {"img": dates_layer, "y": y_dates},
        "agent": {"img": agent_layer, "y": y_agent},
    }


def build_social_layer(social_dict: dict) -> Image.Image | None:
    """Render brand-colored icons in a single row, sized to (row_w, SOCIAL_ICON_SIZE)."""
    present = [k for k, v in social_dict.items() if v and k in ICON_DRAWERS]
    if not present:
        return None
    icons = [ICON_DRAWERS[k](SOCIAL_ICON_SIZE) for k in present]
    total_w = SOCIAL_ICON_SIZE * len(icons) + SOCIAL_GAP * (len(icons) - 1)
    layer = Image.new("RGBA", (total_w, SOCIAL_ICON_SIZE), (0, 0, 0, 0))
    x = 0
    for icon in icons:
        layer.alpha_composite(icon, (x, 0))
        x += SOCIAL_ICON_SIZE + SOCIAL_GAP
    return layer


# ── Per-frame compositing ───────────────────────────────────────────────────
def paste_opacity(base: Image.Image, layer: Image.Image, pos: tuple, opacity: float):
    if opacity <= 0.001:
        return
    if opacity >= 0.999:
        base.alpha_composite(layer, dest=pos)
        return
    alpha = layer.split()[3].point(lambda a: int(a * opacity))
    tmp = layer.copy()
    tmp.putalpha(alpha)
    base.alpha_composite(tmp, dest=pos)


def frame_state(t: float) -> dict:
    """Compute animation state for time t seconds into the 3s card."""
    def fade(delay, dur, y):
        p = ease_out_expo(clamp((t - delay) / dur, 0.0, 1.0))
        return p, (1 - p) * y

    kb_scale = 1.06 - min(t / 3.0, 1.0) * 0.06
    photo_p, _ = fade(0.0, 0.8, 0)
    badge_p, badge_dy = fade(0.3, 0.7, 10)
    badge_scale = 0.96 + 0.04 * badge_p
    logo_p, logo_dy = fade(0.4, 0.7, 10)
    addr_p, addr_dy = fade(0.6, 0.8, 12)
    dates_p, dates_dy = fade(0.8, 0.8, 12)
    agent_p, agent_dy = fade(1.0, 0.8, 12)
    social_p, social_dy = fade(1.2, 0.7, 8)

    return {
        "kb_scale": kb_scale,
        "photo_opacity": photo_p,
        "badge_opacity": badge_p,
        "badge_dy": badge_dy,
        "badge_scale": badge_scale,
        "logo_opacity": logo_p,
        "logo_dy": logo_dy,
        "addr_opacity": addr_p,
        "addr_dy": addr_dy,
        "dates_opacity": dates_p,
        "dates_dy": dates_dy,
        "agent_opacity": agent_p,
        "agent_dy": agent_dy,
        "social_opacity": social_p,
        "social_dy": social_dy,
    }


def render_frame(t: float, base_photo: Image.Image, badge_layer: Image.Image,
                 content: dict, social_layer: Image.Image | None) -> Image.Image:
    state = frame_state(t)
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (*BG_COLOR, 255))

    photo = build_photo_frame(base_photo, state["kb_scale"])
    paste_opacity(canvas, photo, (0, 0), state["photo_opacity"])

    for key, accent_key in (
        ("logo", "logo"),
        ("address", "addr"),
        ("dates", "dates"),
        ("agent", "agent"),
    ):
        item = content[key]
        dy = int(round(state[f"{accent_key}_dy"]))
        paste_opacity(canvas, item["img"], (0, item["y"] + dy),
                      state[f"{accent_key}_opacity"])

    bw, bh = badge_layer.size
    scale = state["badge_scale"]
    sw = max(1, int(round(bw * scale)))
    sh = max(1, int(round(bh * scale)))
    badge_scaled = badge_layer.resize((sw, sh), Image.LANCZOS) if (sw, sh) != (bw, bh) else badge_layer
    bx = (WIDTH - sw) // 2
    by = BADGE_TOP - (sh - (bh - 2 * (BADGE_SHADOW_BLUR + BADGE_SHADOW_OFFSET))) // 2
    # Anchor: badge visual top should land on BADGE_TOP regardless of shadow padding.
    # The pill starts at offset `pad` inside the layer; we want that pill-top at BADGE_TOP+badge_dy.
    pad_offset = int(round((BADGE_SHADOW_BLUR + BADGE_SHADOW_OFFSET) * scale))
    by = BADGE_TOP - pad_offset + int(round(state["badge_dy"]))
    paste_opacity(canvas, badge_scaled, (bx, by), state["badge_opacity"])

    if social_layer is not None:
        sw2, sh2 = social_layer.size
        sx = (WIDTH - sw2) // 2
        sy = HEIGHT - SOCIAL_BOTTOM - sh2 + int(round(state["social_dy"]))
        paste_opacity(canvas, social_layer, (sx, sy), state["social_opacity"])

    return canvas.convert("RGB")


# ── Encoding ────────────────────────────────────────────────────────────────
def ffmpeg_encode(frames_iter, output_path: Path, verbose: bool = False):
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS),
        "-i", "pipe:0",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
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


# ── CLI ─────────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="Render a RISE-style Open House property card")
    p.add_argument("--client", required=True, help="Client slug (reads assets/{slug}/branding.json)")
    p.add_argument("--property-photo", required=True, help="Path to the hero property photo")
    p.add_argument("--address", required=True, help="Street address (e.g. '17 Keith Drive')")
    p.add_argument("--city", required=True, help="City/state line (e.g. 'Hopkinton, RI')")
    p.add_argument("--agent-name", required=True, help="Listing agent name")
    p.add_argument("--date1-day", required=True, help="First date day label (e.g. 'SAT')")
    p.add_argument("--date1-date", required=True, help="First date (e.g. 'April 18')")
    p.add_argument("--date1-time", required=True, help="First time range (e.g. '10:30 AM - 12 PM')")
    p.add_argument("--date2-day", help="Second date day label (optional)")
    p.add_argument("--date2-date", help="Second date (optional)")
    p.add_argument("--date2-time", help="Second time range (optional)")
    p.add_argument("--accent", choices=list(ACCENTS.keys()), default="navy",
                   help="Accent palette (default: navy)")
    p.add_argument("--out", default=None, help="Output MP4 path")
    p.add_argument("--preview-png", help="Also save a final-frame PNG preview to this path")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    client_dir = ASSETS / args.client
    branding_path = client_dir / "branding.json"
    if not branding_path.exists():
        print(f"Error: branding.json not found: {branding_path}", file=sys.stderr)
        sys.exit(2)
    branding = json.loads(branding_path.read_text())

    photo_path = Path(args.property_photo)
    if not photo_path.is_absolute():
        photo_path = (ROOT / photo_path).resolve()
    if not photo_path.exists():
        print(f"Error: property photo not found: {photo_path}", file=sys.stderr)
        sys.exit(2)

    logo_rel = branding["visual"]["logo"]["light_bg_path"]
    logo_path = client_dir / logo_rel
    phone_display = format_phone_national(branding["contact"]["phone_e164"])

    dates = [{
        "day": args.date1_day,
        "date": args.date1_date,
        "time": args.date1_time,
    }]
    if args.date2_day and args.date2_date and args.date2_time:
        dates.append({
            "day": args.date2_day,
            "date": args.date2_date,
            "time": args.date2_time,
        })

    accent = ACCENTS[args.accent]

    out_path = Path(args.out) if args.out else ROOT / "output" / args.client / "property_card.mp4"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("Property card render")
    print(f"  client:   {args.client}")
    print(f"  photo:    {photo_path}")
    print(f"  address:  {args.address}, {args.city}")
    print(f"  agent:    {args.agent_name}  ({phone_display})")
    print(f"  dates:    {len(dates)} entr{'y' if len(dates) == 1 else 'ies'}")
    print(f"  output:   {out_path}")

    base_photo = Image.open(photo_path).convert("RGB")
    badge_layer = build_badge_layer(hex_to_rgb(accent["primary"]))
    content = build_content_layers(logo_path, args.address, args.city, dates,
                                   args.agent_name, phone_display, accent)
    social_layer = build_social_layer(branding["social"])

    def frames_iter():
        for i in range(N_FRAMES):
            t = (i + 0.5) / FPS
            yield render_frame(t, base_photo, badge_layer, content, social_layer)

    if args.preview_png:
        preview_frame = render_frame(DURATION_SEC - 0.05, base_photo, badge_layer,
                                     content, social_layer)
        preview_frame.save(args.preview_png)
        print(f"  preview:  {args.preview_png}")

    with tempfile.NamedTemporaryFile(dir=out_path.parent, delete=False,
                                     prefix=".tmp_", suffix=".mp4") as tf:
        tmp_out = Path(tf.name)
    try:
        ffmpeg_encode(frames_iter(), tmp_out, verbose=args.verbose)
        tmp_out.replace(out_path)
    except Exception:
        tmp_out.unlink(missing_ok=True)
        raise

    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"  wrote:    {out_path} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
