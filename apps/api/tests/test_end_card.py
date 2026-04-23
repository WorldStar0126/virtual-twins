"""Pytest suite for the end card pipeline (schema validation, rendering, caching).

Run with:
    python -m pytest tests/ -v

Notes:
    - Integration tests invoke ffmpeg/ffprobe and write real MP4 files into .tmp/test_outputs/.
    - Unit tests for pure functions don't require ffmpeg.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import generate_end_card as ec  # noqa: E402
import validate_branding as vb  # noqa: E402


FIXTURES = {
    "test-client": ROOT / "assets" / "_fixtures" / "test-client" / "branding.json",
    "minimal-client": ROOT / "assets" / "_fixtures" / "minimal-client" / "branding.json",
}

TEST_OUT = ROOT / ".tmp" / "test_outputs"


@pytest.fixture(scope="session", autouse=True)
def _ensure_test_out():
    TEST_OUT.mkdir(parents=True, exist_ok=True)


class TestEaseAndLuminance:
    def test_ease_out_cubic_endpoints(self):
        assert ec.ease_out_cubic(0.0) == 0.0
        assert ec.ease_out_cubic(1.0) == 1.0

    def test_ease_out_cubic_monotonic(self):
        prev = -1.0
        for i in range(0, 101):
            v = ec.ease_out_cubic(i / 100.0)
            assert v >= prev
            prev = v

    def test_ease_out_cubic_clamped(self):
        assert ec.ease_out_cubic(-1.0) == 0.0
        assert ec.ease_out_cubic(2.0) == 1.0

    def test_luminance_black(self):
        assert ec.relative_luminance("#000000") == pytest.approx(0.0, abs=1e-6)

    def test_luminance_white(self):
        assert ec.relative_luminance("#ffffff") == pytest.approx(1.0, abs=1e-6)

    def test_luminance_ordering(self):
        dark = ec.relative_luminance("#222222")
        light = ec.relative_luminance("#DDDDDD")
        assert dark < light

    def test_contrast_ratio_black_on_white(self):
        assert ec.contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0, abs=1e-3)


class TestLogoVariantPick:
    def test_light_preference_wins(self, tmp_path):
        light = tmp_path / "light.png"
        dark = tmp_path / "dark.png"
        light.touch()
        dark.touch()
        assert ec.pick_logo_variant("#000000", "light", light, dark) == light
        assert ec.pick_logo_variant("#ffffff", "light", light, dark) == light

    def test_dark_preference_wins(self, tmp_path):
        light = tmp_path / "l.png"
        dark = tmp_path / "d.png"
        light.touch()
        dark.touch()
        assert ec.pick_logo_variant("#ffffff", "dark", light, dark) == dark

    def test_auto_picks_light_for_light_bg(self, tmp_path):
        light = tmp_path / "l.png"
        dark = tmp_path / "d.png"
        light.touch()
        dark.touch()
        assert ec.pick_logo_variant("#f5f5f5", "auto", light, dark) == light

    def test_auto_picks_dark_for_dark_bg(self, tmp_path):
        light = tmp_path / "l.png"
        dark = tmp_path / "d.png"
        light.touch()
        dark.touch()
        assert ec.pick_logo_variant("#101010", "auto", light, dark) == dark


class TestPhoneNormalization:
    def test_parses_us_number(self):
        assert vb.normalize_phone("401-369-9100") == "+14013699100"

    def test_parses_e164(self):
        assert vb.normalize_phone("+14013699100") == "+14013699100"

    def test_parses_with_parens(self):
        assert vb.normalize_phone("(401) 369-9100") == "+14013699100"

    def test_rejects_invalid_area_code(self):
        with pytest.raises(vb.BrandingError):
            vb.normalize_phone("+15555550123")

    def test_rejects_garbage(self):
        with pytest.raises(vb.BrandingError):
            vb.normalize_phone("not a phone")


class TestWebsiteNormalization:
    @pytest.mark.parametrize("inp,out", [
        ("balkuntc.com", "balkuntc.com"),
        ("https://balkuntc.com", "balkuntc.com"),
        ("HTTP://Balkuntc.com/", "balkuntc.com"),
        ("https://BalkunTC.com/path", "balkuntc.com/path"),
    ])
    def test_website_normalized(self, inp, out):
        assert vb.normalize_website(inp) == out


class TestSocialNormalization:
    @pytest.mark.parametrize("inp,out", [
        (None, None),
        ("", None),
        ("  ", None),
        ("handle", "handle"),
        ("@handle", "handle"),
        ("  @handle  ", "handle"),
    ])
    def test_social_handle(self, inp, out):
        assert vb.normalize_social_handle(inp) == out


class TestSchemaValidation:
    @pytest.mark.parametrize("slug", ["test-client", "minimal-client"])
    def test_fixtures_validate(self, slug):
        src = FIXTURES[slug]
        doc = vb.validate(src, strict_slug_match=False)
        assert doc["slug"] == slug

    def test_dan_balkun_validates(self):
        src = ROOT / "assets" / "dan-balkun" / "branding.json"
        if not src.exists():
            pytest.skip("dan-balkun branding not set up")
        doc = vb.validate(src)
        assert doc["contact"]["phone_e164"].startswith("+1")
        assert doc["contact"]["email"] == doc["contact"]["email"].lower()

    def test_rejects_missing_required(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text('{"slug": "bad"}')
        with pytest.raises(vb.BrandingError):
            vb.validate(bad, strict_slug_match=False)


class TestCacheKeyStability:
    def test_same_input_same_hash(self):
        doc = {
            "identity": {"display_name": "Test", "industry": "other"},
            "contact": {"phone_e164": "+14013699100", "email": "x@y.com", "website": "y.com"},
            "social": {"instagram": "a", "facebook": None, "linkedin": None,
                       "tiktok": None, "youtube": None, "x": None},
            "visual": {"colors": {
                "primary":    {"hex": "#111111"},
                "secondary":  {"hex": "#222222"},
                "accent":     {"hex": "#333333"},
                "background": {"hex": "#ffffff", "preference": "light"},
                "foreground": {"hex": "#000000"},
            }},
            "typography": {"heading": {"family": "Manrope", "file_path": "a.ttf"},
                           "body": {"family": "Inter", "file_path": "b.ttf"}},
        }
        logo_bytes = b"\x89PNG\r\n\x1a\nfake"

        h1 = ec.cache_key_hash(ec.canonicalize_for_hash(doc, logo_bytes))
        h2 = ec.cache_key_hash(ec.canonicalize_for_hash(doc, logo_bytes))
        assert h1 == h2

    def test_different_socials_different_hash(self):
        def make(handle):
            return {
                "identity": {"display_name": "Test", "industry": "other"},
                "contact": {"phone_e164": "+14013699100", "email": "x@y.com", "website": "y.com"},
                "social": {"instagram": handle, "facebook": None, "linkedin": None,
                           "tiktok": None, "youtube": None, "x": None},
                "visual": {"colors": {
                    "primary":    {"hex": "#111111"},
                    "secondary":  {"hex": "#222222"},
                    "accent":     {"hex": "#333333"},
                    "background": {"hex": "#ffffff", "preference": "light"},
                    "foreground": {"hex": "#000000"},
                }},
                "typography": {"heading": {"family": "Manrope", "file_path": "a.ttf"},
                               "body": {"family": "Inter", "file_path": "b.ttf"}},
            }

        logo = b"fake"
        h1 = ec.cache_key_hash(ec.canonicalize_for_hash(make("a"), logo))
        h2 = ec.cache_key_hash(ec.canonicalize_for_hash(make("b"), logo))
        assert h1 != h2

    def test_different_logo_different_hash(self):
        doc = {
            "identity": {"display_name": "Test", "industry": "other"},
            "contact": {"phone_e164": "+14013699100", "email": "x@y.com", "website": "y.com"},
            "social": {"instagram": None, "facebook": None, "linkedin": None,
                       "tiktok": None, "youtube": None, "x": None},
            "visual": {"colors": {
                "primary":    {"hex": "#111111"},
                "secondary":  {"hex": "#222222"},
                "accent":     {"hex": "#333333"},
                "background": {"hex": "#ffffff", "preference": "light"},
                "foreground": {"hex": "#000000"},
            }},
            "typography": {"heading": {"family": "Manrope", "file_path": "a.ttf"},
                           "body": {"family": "Inter", "file_path": "b.ttf"}},
        }
        h1 = ec.cache_key_hash(ec.canonicalize_for_hash(doc, b"logo-v1"))
        h2 = ec.cache_key_hash(ec.canonicalize_for_hash(doc, b"logo-v2"))
        assert h1 != h2


def ffprobe_json(path: Path) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(r.stdout)


class TestIntegrationRender:
    @pytest.mark.parametrize("slug", ["test-client", "minimal-client"])
    def test_render_produces_expected_mp4(self, slug):
        src = FIXTURES[slug]
        out = TEST_OUT / f"{slug}.mp4"
        if out.exists():
            out.unlink()

        result = ec.render(src, out, force_rebuild=True)
        assert result["status"] == "rendered"
        assert out.exists()
        assert out.stat().st_size > 10_000

        probe = ffprobe_json(out)
        vstream = next(s for s in probe["streams"] if s["codec_type"] == "video")
        astream = next(s for s in probe["streams"] if s["codec_type"] == "audio")

        assert vstream["codec_name"] == "h264"
        assert vstream["width"] == 720
        assert vstream["height"] == 1280
        num, den = (int(x) for x in vstream["r_frame_rate"].split("/"))
        assert num / den == pytest.approx(30.0)
        assert vstream["pix_fmt"] == "yuv420p"

        assert astream["codec_name"] == "aac"
        assert int(astream["sample_rate"]) == 48000

        duration = float(probe["format"]["duration"])
        assert duration == pytest.approx(3.0, abs=0.05)

    def test_cache_hit_is_fast(self):
        src = FIXTURES["test-client"]
        out = TEST_OUT / "cache_hit.mp4"
        if out.exists():
            out.unlink()

        ec.render(src, out, force_rebuild=True)
        import time
        t0 = time.time()
        result = ec.render(src, out)
        elapsed = time.time() - t0
        assert result["status"] == "cache_hit"
        assert elapsed < 0.5


class TestSocialsRow:
    @pytest.mark.parametrize("socials,expected_presence", [
        ({"instagram": None, "facebook": None, "linkedin": None, "tiktok": None, "youtube": None, "x": None}, False),
        ({"instagram": "a", "facebook": None, "linkedin": None, "tiktok": None, "youtube": None, "x": None}, True),
        ({"instagram": "a", "facebook": "b", "linkedin": "c", "tiktok": "d", "youtube": "e", "x": "f"}, True),
    ])
    def test_state_flags_row_presence(self, socials, expected_presence):
        row_present = any(v for v in socials.values())
        assert row_present == expected_presence
        state = ec.animation_state(1.5, row_present)
        if expected_presence:
            assert state["socials_opacity"] > 0
        else:
            assert state["socials_opacity"] == 0


class TestSocialIconDrawing:
    @pytest.mark.parametrize("platform", ["instagram", "tiktok", "facebook", "youtube", "linkedin", "x"])
    def test_each_drawer_produces_nonblank(self, platform):
        drawer = ec.ICON_DRAWERS[platform]
        img = drawer(76)
        assert img.size == (76, 76)
        assert img.mode == "RGBA"
        alpha = img.split()[3]
        assert alpha.getextrema()[1] > 0, f"{platform} icon appears blank"

    def test_each_icon_has_brand_color(self):
        """Non-monochrome icons should have visible color in RGB (not grayscale)."""
        import numpy as np
        for platform in ["instagram", "facebook", "linkedin", "youtube"]:
            img = ec.ICON_DRAWERS[platform](76)
            arr = np.array(img)
            rgb = arr[:, :, :3]
            alpha = arr[:, :, 3]
            opaque = alpha > 128
            if not opaque.any():
                continue
            r = rgb[:, :, 0][opaque]
            g = rgb[:, :, 1][opaque]
            b = rgb[:, :, 2][opaque]
            max_channel_spread = max(
                int(r.max()) - int(r.min()),
                int(g.max()) - int(g.min()),
                int(b.max()) - int(b.min()),
            )
            assert max_channel_spread > 30, f"{platform} looks monochrome"


class TestContactIcons:
    @pytest.mark.parametrize("kind", ["phone", "email", "website"])
    def test_each_contact_icon_renders(self, kind):
        drawer = ec.CONTACT_ICON_DRAWERS[kind]
        img = drawer(32, (149, 106, 45, 255))
        assert img.size == (32, 32)
        assert img.mode == "RGBA"
        assert img.split()[3].getextrema()[1] > 0


class TestDisplayNameToggle:
    def test_name_hidden_when_flag_false(self):
        state = ec.animation_state(1.5, row_present=True, name_present=False)
        assert state["name_opacity"] == 0.0

    def test_name_shown_when_flag_true(self):
        state = ec.animation_state(1.5, row_present=True, name_present=True)
        assert state["name_opacity"] > 0.0
