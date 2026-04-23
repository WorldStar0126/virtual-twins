"""Scrape a single vehicle detail page (VDP) and emit a structured JSON record.

Prefers Schema.org `Vehicle` JSON-LD (most dealer CMSes emit this for SEO), falling
back to Open Graph and HTML meta tags. Tested against guaranteedautoloansri.com;
should generalize to any dealer site that publishes Vehicle JSON-LD.

Pass `--all-photos` to run headless Chromium (Playwright) so the full photo array
is captured after the VDP's JS hydrates. Without that flag, only the hero photo
(from og:image / JSON-LD) is returned — fast and cheap, but incomplete.

Usage:
    python tools/scrape_vehicle_listing.py --url URL
    python tools/scrape_vehicle_listing.py --url URL --out listing.json --all-photos
"""

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def fetch_html(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    return r.text


def parse_year_make_model(name: str) -> dict:
    """Parse a Schema.org Vehicle name like '2016 Honda CR-V SE Sport Utility 4D'."""
    out = {"year": None, "make": None, "model": None, "trim": None}
    if not name:
        return out
    parts = name.strip().split(maxsplit=3)
    if parts and re.fullmatch(r"\d{4}", parts[0]):
        out["year"] = int(parts[0])
        parts = parts[1:]
    if parts:
        out["make"] = parts[0]
        parts = parts[1:]
    if parts:
        out["model"] = parts[0]
        parts = parts[1:]
    if parts:
        out["trim"] = " ".join(parts)
    return out


def extract_json_ld(html: str) -> list[dict]:
    """Return all JSON-LD blocks present on the page, parsed."""
    out = []
    for m in re.finditer(
        r"<script[^>]*type=['\"]application/ld\+json['\"][^>]*>(.*?)</script>",
        html, flags=re.DOTALL | re.IGNORECASE,
    ):
        raw = m.group(1).strip()
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return out


def pick_vehicle_block(blocks: list[dict]) -> dict | None:
    """Return the first block whose @type is 'Vehicle' (case-insensitive)."""
    for b in blocks:
        t = b.get("@type")
        if isinstance(t, str) and t.lower() == "vehicle":
            return b
        if isinstance(t, list) and any(x.lower() == "vehicle" for x in t if isinstance(x, str)):
            return b
    return None


def extract_meta(html: str, attr: str, key: str) -> str | None:
    """Return the 'content' of the first <meta {attr}='{key}' content='...'>."""
    pat = re.compile(
        rf"<meta[^>]*{attr}=['\"]{re.escape(key)}['\"][^>]*content=['\"]([^'\"]+)['\"]",
        flags=re.IGNORECASE,
    )
    m = pat.search(html)
    if m:
        return m.group(1)
    pat2 = re.compile(
        rf"<meta[^>]*content=['\"]([^'\"]+)['\"][^>]*{attr}=['\"]{re.escape(key)}['\"]",
        flags=re.IGNORECASE,
    )
    m2 = pat2.search(html)
    return m2.group(1) if m2 else None


def extract_exposed_vars(html: str) -> dict:
    """Pull the `exposed_vars = {...};` JS object if present."""
    m = re.search(r"exposed_vars\s*=\s*(\{.*?\});", html, flags=re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}


def condition_from_schema(s: str) -> str | None:
    """Map Schema.org itemCondition to 'new' / 'used'."""
    if not s:
        return None
    s = s.lower()
    if "used" in s:
        return "used"
    if "new" in s:
        return "new"
    return None


def clean_description(desc: str) -> str:
    """Strip HTML tags, collapse whitespace, keep markdown-style bold ** markers."""
    if not desc:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", desc, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def fetch_photos_headless(url: str, vin: str, timeout_s: int = 20) -> list[str]:
    """Launch Chromium via Playwright, let the VDP hydrate, and return all image
    URLs on the page whose path contains `vehicle_images/{VIN}/`.

    Returns de-duplicated URLs, preferring the largest known size tier when the
    same photo appears at multiple sizes (sm/md/lg/bg).
    """
    from playwright.sync_api import sync_playwright

    size_rank = {"bg": 5, "lg": 4, "full": 4, "md": 3, "og": 3, "thumb": 2, "sm": 1, "xs": 0}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_s * 1000)

        try:
            page.wait_for_selector(f"img[src*='vehicle_images/{vin}/']", timeout=timeout_s * 1000)
        except Exception:
            pass
        try:
            page.wait_for_load_state("networkidle", timeout=5_000)
        except Exception:
            pass

        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(800)

        srcs = page.evaluate("""() => {
            const urls = new Set();
            document.querySelectorAll('img').forEach(img => {
                const cands = [img.src, img.getAttribute('data-src'),
                               img.getAttribute('data-lazy'), img.currentSrc];
                cands.forEach(u => { if (u) urls.add(u); });
                const srcset = img.getAttribute('srcset');
                if (srcset) {
                    srcset.split(',').forEach(part => {
                        const u = part.trim().split(/\\s+/)[0];
                        if (u) urls.add(u);
                    });
                }
            });
            document.querySelectorAll('source').forEach(s => {
                const srcset = s.getAttribute('srcset');
                if (srcset) {
                    srcset.split(',').forEach(part => {
                        const u = part.trim().split(/\\s+/)[0];
                        if (u) urls.add(u);
                    });
                }
            });
            return Array.from(urls);
        }""")

        browser.close()

    vin_urls = [u for u in srcs if f"vehicle_images/{vin}/" in u]

    def photo_key(u: str) -> str:
        """Same visual photo across size tiers shares this key (strip size + ext)."""
        m = re.search(r"vehicle_images/[^/]+/([a-z]+)/([^/]+)$", u)
        if not m:
            return u
        _tier, fname = m.groups()
        fname = re.sub(r"\.[a-z0-9]+$", "", fname)
        fname = re.sub(r"-(?:bg|sm|md|lg|og|thumb|xs|full)$", "", fname)
        return fname

    def tier_of(u: str) -> int:
        m = re.search(r"vehicle_images/[^/]+/([a-z]+)/", u)
        return size_rank.get(m.group(1), 0) if m else 0

    best: dict[str, str] = {}
    for u in vin_urls:
        k = photo_key(u)
        if k not in best or tier_of(u) > tier_of(best[k]):
            best[k] = u

    def sort_key(u: str):
        m = re.search(r"vehicle_images/[^/]+/[a-z]+/.*?([a-f0-9]{6,})", u)
        return m.group(1) if m else u

    return sorted(best.values(), key=sort_key)


def scrape(url: str, all_photos: bool = False) -> dict:
    html = fetch_html(url)
    blocks = extract_json_ld(html)
    veh = pick_vehicle_block(blocks) or {}

    ymm = parse_year_make_model(veh.get("name", ""))
    offer = veh.get("offers") or {}
    mileage = veh.get("mileageFromOdometer") or {}
    engine = veh.get("vehicleEngine") or {}

    hero_photo = extract_meta(html, "property", "og:image")
    og_description = extract_meta(html, "property", "og:description")

    additional = []
    if isinstance(veh.get("image"), list):
        additional = [u for u in veh["image"] if isinstance(u, str) and u]

    photos = []
    if hero_photo:
        photos.append(hero_photo)
    for p in additional:
        if p not in photos:
            photos.append(p)

    ev = extract_exposed_vars(html)

    vin = veh.get("vehicleIdentificationNumber") or ev.get("vin")

    if all_photos and vin:
        hydrated = fetch_photos_headless(url, vin)
        if hydrated:
            photos = list(dict.fromkeys(hydrated + photos))
    price_raw = offer.get("price")
    try:
        price = float(price_raw) if price_raw not in (None, "") else None
    except (TypeError, ValueError):
        price = None

    mileage_val = mileage.get("value")
    try:
        mileage_num = int(mileage_val) if mileage_val not in (None, "") else None
    except (TypeError, ValueError):
        mileage_num = None

    return {
        "source_url": url,
        "scraped_at_utc": None,
        "vin": vin,
        "year": ymm["year"] or (int(veh["modelDate"]) if veh.get("modelDate", "").isdigit() else None),
        "make": ymm["make"] or (veh.get("brand") or {}).get("name"),
        "model": ymm["model"],
        "trim": ymm["trim"] or veh.get("vehicleConfiguration"),
        "name_full": veh.get("name"),
        "price_usd": price,
        "price_currency": offer.get("priceCurrency"),
        "price_valid_until": offer.get("priceValidUntil"),
        "availability": (offer.get("availability") or "").split("/")[-1] or None,
        "condition": condition_from_schema(offer.get("itemCondition", "")),
        "mileage": mileage_num,
        "mileage_unit": mileage.get("unitCode"),
        "engine": engine.get("name"),
        "fuel_type": veh.get("fuelType"),
        "transmission": veh.get("vehicleTransmission"),
        "drivetrain": veh.get("driveWheelConfiguration"),
        "body_type": veh.get("bodyType"),
        "num_doors": veh.get("numberOfDoors"),
        "seating_capacity": veh.get("seatingCapacity"),
        "description_raw": veh.get("description") or og_description,
        "description_text": clean_description(veh.get("description") or og_description or ""),
        "hero_photo_url": hero_photo,
        "photo_urls": photos,
        "photo_count_known_incomplete": (not all_photos) and len(photos) <= 1,
        "headless_used": all_photos,
        "dealer_account": ev.get("account"),
    }


def main():
    p = argparse.ArgumentParser(description="Scrape a vehicle detail page → structured JSON")
    p.add_argument("--url", required=True, help="Vehicle detail page URL")
    p.add_argument("--out", help="Output JSON path (default: stdout)")
    p.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    p.add_argument("--all-photos", action="store_true",
                   help="Run headless Chromium to capture all photos (slower, requires Playwright).")
    args = p.parse_args()

    try:
        data = scrape(args.url, all_photos=args.all_photos)
    except requests.HTTPError as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Scrape error: {e}", file=sys.stderr)
        sys.exit(1)

    from datetime import datetime, timezone
    data["scraped_at_utc"] = datetime.now(timezone.utc).isoformat()

    payload = json.dumps(data, indent=2 if args.pretty else None, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(payload)


if __name__ == "__main__":
    main()
