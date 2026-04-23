"""Validate a client's branding.json against the canonical schema.

Usage:
    python tools/validate_branding.py --client dan-balkun
    python tools/validate_branding.py --path assets/_fixtures/test-client/branding.json

Exit codes:
    0 — valid
    1 — schema or business-rule failure
    2 — file not found / unreadable
"""

import argparse
import json
import re
import sys
from pathlib import Path

import phonenumbers
from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "branding.schema.json"
ASSETS_DIR = ROOT / "assets"

SUPPORTED_SOCIAL_PLATFORMS = {"instagram", "tiktok", "facebook", "youtube", "linkedin", "x"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class BrandingError(Exception):
    """Raised when validation fails for reasons beyond jsonschema structure."""


def load_schema() -> dict:
    if not SCHEMA_PATH.exists():
        raise BrandingError(f"Schema not found at {SCHEMA_PATH}")
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def normalize_phone(raw: str) -> str:
    """Parse and validate, returning E.164 format. Raises BrandingError on failure."""
    try:
        parsed = phonenumbers.parse(raw, "US")
    except phonenumbers.NumberParseException as e:
        raise BrandingError(f"Could not parse phone number '{raw}': {e}")
    if not phonenumbers.is_valid_number(parsed):
        raise BrandingError(f"Phone number '{raw}' parses but is not a valid number")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def normalize_website(raw: str) -> str:
    """Strip scheme, strip trailing slash, lowercase."""
    s = raw.strip().lower()
    for prefix in ("https://", "http://"):
        if s.startswith(prefix):
            s = s[len(prefix):]
    return s.rstrip("/")


def normalize_social_handle(raw):
    """None or empty → None. Otherwise strip leading @ and whitespace."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    return s.lstrip("@")


def normalize_branding(doc: dict) -> dict:
    """Return a normalized copy with phone in E.164, email/website lowercased,
    social handles stripped of @, and unknown social platforms removed."""
    out = json.loads(json.dumps(doc))

    out["contact"]["phone_e164"] = normalize_phone(out["contact"]["phone_e164"])
    email = out["contact"].get("email")
    out["contact"]["email"] = email.strip().lower() if email else None
    out["contact"]["website"] = normalize_website(out["contact"]["website"])
    address = out["contact"].get("address")
    out["contact"]["address"] = address.strip() if address else None

    social_in = out.get("social", {}) or {}
    social_out = {}
    for platform in SUPPORTED_SOCIAL_PLATFORMS:
        social_out[platform] = normalize_social_handle(social_in.get(platform))
    out["social"] = social_out

    for variant in ("light_bg_path", "dark_bg_path"):
        p = out["visual"]["logo"][variant]
        out["visual"]["logo"][variant] = p.replace("\\", "/")

    for kind in ("heading", "body"):
        p = out["typography"][kind]["file_path"]
        out["typography"][kind]["file_path"] = p.replace("\\", "/")

    for color_key, color_val in out["visual"]["colors"].items():
        color_val["hex"] = color_val["hex"].lower()

    return out


def check_files_exist(doc: dict, base_dir: Path) -> list[str]:
    """Return a list of error strings for missing files referenced in the doc."""
    errors = []
    logo = doc["visual"]["logo"]
    for key in ("light_bg_path", "dark_bg_path"):
        rel = logo[key]
        abs_path = (base_dir / rel) if not Path(rel).is_absolute() else Path(rel)
        if not abs_path.exists():
            errors.append(f"visual.logo.{key} does not exist: {abs_path}")

    for kind in ("heading", "body"):
        rel = doc["typography"][kind]["file_path"]
        abs_path = (base_dir / rel) if not Path(rel).is_absolute() else Path(rel)
        if not abs_path.exists():
            errors.append(f"typography.{kind}.file_path does not exist: {abs_path}")
    return errors


def check_email(doc: dict) -> list[str]:
    email = doc["contact"].get("email")
    if email is None:
        return []
    if not EMAIL_RE.match(email):
        return [f"contact.email failed regex check: '{email}'"]
    return []


def check_slug_matches_folder(doc: dict, source_path: Path) -> list[str]:
    """If the doc is at assets/{slug}/branding.json, the slug must match the folder."""
    try:
        folder_name = source_path.parent.name
    except Exception:
        return []
    if folder_name != doc["slug"]:
        return [
            f"slug '{doc['slug']}' does not match containing folder '{folder_name}' "
            f"({source_path})"
        ]
    return []


def validate(source_path: Path, strict_slug_match: bool = True) -> dict:
    """Run all checks. Return the normalized document. Raises BrandingError on any failure."""
    schema = load_schema()
    if not source_path.exists():
        raise BrandingError(f"Branding file not found: {source_path}")

    try:
        doc = json.loads(source_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise BrandingError(f"Invalid JSON in {source_path}: {e}")

    validator = Draft7Validator(schema)
    schema_errors = sorted(validator.iter_errors(doc), key=lambda e: e.path)
    if schema_errors:
        lines = [f"Schema validation failed for {source_path}:"]
        for err in schema_errors:
            path = ".".join(str(p) for p in err.path) or "<root>"
            lines.append(f"  [{path}] {err.message}")
        raise BrandingError("\n".join(lines))

    normalized = normalize_branding(doc)

    business_errors: list[str] = []
    business_errors.extend(check_email(normalized))
    base_dir = source_path.parent
    business_errors.extend(check_files_exist(normalized, base_dir))
    if strict_slug_match:
        business_errors.extend(check_slug_matches_folder(normalized, source_path))

    if business_errors:
        raise BrandingError(
            f"Branding at {source_path} failed business checks:\n  " +
            "\n  ".join(business_errors)
        )

    return normalized


def resolve_source_path(args) -> Path:
    if args.path:
        return Path(args.path)
    if args.client:
        return ASSETS_DIR / args.client / "branding.json"
    raise BrandingError("Must provide either --client or --path")


def main():
    parser = argparse.ArgumentParser(description="Validate a client branding.json")
    parser.add_argument("--client", help="Client slug under assets/")
    parser.add_argument("--path", help="Direct path to a branding.json")
    parser.add_argument("--no-slug-check", action="store_true",
                        help="Skip the 'slug must match folder name' check (useful for fixtures)")
    parser.add_argument("--print-normalized", action="store_true",
                        help="Print the normalized document on success")
    args = parser.parse_args()

    try:
        source = resolve_source_path(args)
    except BrandingError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    if not source.exists():
        print(f"Error: file not found: {source}", file=sys.stderr)
        sys.exit(2)

    try:
        normalized = validate(source, strict_slug_match=not args.no_slug_check)
    except BrandingError as e:
        print(f"{e}", file=sys.stderr)
        sys.exit(1)

    print(f"OK  {source}")
    print(f"    slug:         {normalized['slug']}")
    print(f"    display_name: {normalized['identity']['display_name']}")
    print(f"    industry:     {normalized['identity']['industry']}")
    print(f"    phone (E.164):{normalized['contact']['phone_e164']}")
    socials_present = [k for k, v in normalized["social"].items() if v]
    print(f"    socials:      {', '.join(socials_present) if socials_present else '(none)'}")

    if args.print_normalized:
        print("\nNormalized document:")
        print(json.dumps(normalized, indent=2))


if __name__ == "__main__":
    main()
