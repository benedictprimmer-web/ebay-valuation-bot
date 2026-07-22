"""Exact-model identity for cameras and lenses.

The cameras lane lives or dies on identity. Two listings are comparable only if they're
the same body or lens, and eBay titles are messy: missing model suffixes, "mark 3" vs
"mk III" vs "iii", dashes, alpha symbols, brand misspellings. This turns a freeform title
into a normalised identity plus a canonical key for grouping comps.

Design rule from the research: value automatically ONLY when the title resolves to a
specific model. If it doesn't, `resolved` is False and the bot should send it to manual
review, not bid on a guess. That's the bad-listing edge handled safely — a buried model
number we can recover is value; total ambiguity is a pass, not a gamble.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Listing

_BRANDS = {
    "sony": "sony", "canon": "canon", "nikon": "nikon",
    "fujifilm": "fujifilm", "fuji": "fujifilm",
    "panasonic": "panasonic", "lumix": "panasonic",
    "olympus": "olympus", "omd": "olympus",
    "sigma": "sigma", "tamron": "tamron", "leica": "leica",
    "pentax": "pentax", "ricoh": "ricoh",
}
# common misspellings seen in sloppy listings
_BRAND_FIX = {"cannon": "canon", "nikkon": "nikon", "fugifilm": "fujifilm", "sonny": "sony"}

_ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6"}
_MOUNTS = ("rf", "ef-s", "ef", "fe", "z", "x", "l")  # lens mount tokens to keep

_FOCAL = re.compile(r"(\d{1,4})(?:-(\d{1,4}))?\s?mm\b")
_APERTURE = re.compile(r"(?<![a-z])f/?\s?(\d{1,2}(?:\.\d+)?)")  # lookbehind skips rf/ef
_MARK = re.compile(r"\b(?:mark|mk)\s*([ivx]+|\d)\b")
_ROMAN_STANDALONE = re.compile(r"\b(ii|iii|iv|vi)\b")  # multi-char only; Mark V via _MARK

# (brand, pattern). Groups are joined + de-spaced to form the model core.
_BODY_PATTERNS = [
    ("sony", re.compile(r"\b(a)\s?(7r|7s|7c|7|9|1)\b")),
    ("sony", re.compile(r"\b(a)\s?(6\d00)\b")),
    ("sony", re.compile(r"\b(zv)\s?(e10|e1|1)\b")),
    ("canon", re.compile(r"\beos\s?(r)\s?(\d+|p)?\b")),
    ("canon", re.compile(r"\b(r)\s?(\d{1,3})\b")),
    ("canon", re.compile(r"\b(\d{1,3})\s?(d)\b")),
    ("canon", re.compile(r"\b(m)\s?(\d{1,3})\b")),  # EOS M mirrorless (M50, M6, M100...)
    ("nikon", re.compile(r"\b(z)\s?(\d|f|fc)\b")),
    ("nikon", re.compile(r"\b(d)\s?(\d{1,4})\b")),  # 1-4 digits: D6, D90, D610, D3200
    ("fujifilm", re.compile(r"\b(x)\s?(t|s|h|e|pro)\s?(\d+)\b")),
    ("fujifilm", re.compile(r"\b(x100)\s?([a-z]+)?\b")),
    ("panasonic", re.compile(r"\b(gh|gx|gf|gm|g|s|fz)\s?(\d+)\b")),  # gx/gf/gm before bare g
    ("olympus", re.compile(r"\b(?:om\s?d\s?)?(e\s?m)\s?(\d+)\b")),
    ("olympus", re.compile(r"\b(om)\s?(\d+)\b")),
]


@dataclass(frozen=True)
class CameraItem:
    brand: str
    model: str       # normalised, e.g. "a7 3", "rf 50mm f1.8"
    kind: str        # "body" | "lens" | "unknown"
    resolved: bool   # True only if brand + a specific model were found
    raw: str

    def key(self) -> str:
        return f"{self.brand}|{self.kind}|{self.model}".lower()

    def matches(self, other: "CameraItem") -> bool:
        return self.resolved and other.resolved and self.key() == other.key()

    def label(self) -> str:
        # Display only — the key() above stays lowercase-normalised for matching.
        # Upper-case model codes (a7 -> A7, xt4 -> XT4) but leave focal/aperture
        # tokens alone (50mm, f1.8) so they read the way listings write them.
        def tok(t: str) -> str:
            return t if ("mm" in t or re.match(r"^f[\d.]", t)) else t.upper()

        model = " ".join(tok(t) for t in self.model.split())
        return f"{self.brand.title()} {model}".strip()

    def search_query(self) -> str:
        """Search term for comp lookups. Renders a Mark version as a Roman numeral
        (a7 2 -> "Sony A7 II") because that's how sellers title listings — searching
        "Sony A7 2" returns nothing. The key() used for MATCHING stays "...|a7 2", so
        a returned "A7 II" listing still parses back to the same identity and matches."""
        roman = {"2": "II", "3": "III", "4": "IV", "5": "V", "6": "VI"}
        parts = self.model.split()
        if len(parts) >= 2 and parts[-1] in roman:
            core = " ".join(p.upper() for p in parts[:-1])
            return f"{self.brand.title()} {core} {roman[parts[-1]]}".strip()
        return self.label()


def _prep(title: str) -> tuple[str, str]:
    """Return (base, spaced). base keeps dashes/dots (for focal & aperture); spaced
    turns separators into spaces and splits roman numerals stuck onto a digit."""
    base = title.lower().replace("α", "a").replace("alpha", "a")
    base = re.sub(r"\s+", " ", base).strip()
    for bad, good in _BRAND_FIX.items():
        base = base.replace(bad, good)
    spaced = re.sub(r"[\-/(),]", " ", base)
    spaced = re.sub(r"(\d)(iii|ii|iv|vi)\b", r"\1 \2", spaced)  # a7iii -> a7 iii
    spaced = re.sub(r"\s+", " ", spaced).strip()
    return base, spaced


def _brand(spaced: str) -> str | None:
    for tok in spaced.split():
        if tok in _BRANDS:
            return _BRANDS[tok]
    return None


def _version(spaced: str) -> str:
    m = _MARK.search(spaced)
    if m:
        return _ROMAN.get(m.group(1), m.group(1))
    m = _ROMAN_STANDALONE.search(spaced)
    return _ROMAN.get(m.group(1), "") if m else ""


def parse_camera(title: str) -> CameraItem:
    base, spaced = _prep(title)
    brand = _brand(spaced)

    # --- lens: a focal length is the strongest lens signal -------------------
    fm = _FOCAL.search(base)
    if fm:
        focal = f"{fm.group(1)}{'-' + fm.group(2) if fm.group(2) else ''}mm"
        mount = next((t for t in _MOUNTS if re.search(rf"\b{t}\b", spaced)), "")
        ap = _APERTURE.search(base)
        aperture = f"f{ap.group(1)}" if ap else ""
        model = " ".join(p for p in (mount, focal, aperture) if p).strip()
        return CameraItem(
            brand=brand or "unknown", model=model, kind="lens",
            resolved=bool(brand), raw=title,
        )

    # --- body: brand-specific patterns --------------------------------------
    if brand:
        version = _version(spaced)
        for b, pat in _BODY_PATTERNS:
            if b != brand:
                continue
            m = pat.search(spaced)
            if m:
                core = "".join(g for g in m.groups() if g).replace(" ", "")
                model = (core + (f" {version}" if version else "")).strip()
                return CameraItem(brand=brand, model=model, kind="body",
                                  resolved=True, raw=title)
        return CameraItem(brand=brand, model="", kind="body", resolved=False, raw=title)

    return CameraItem(brand="unknown", model="", kind="unknown", resolved=False, raw=title)


# Shutter count — a body-wear signal sellers SOMETIMES put in the title ("shutter count
# 12,345", "SC 12k", "12000 actuations"). Usually it's only in the description or not
# stated at all, so this returns None far more often than not — and None must never be
# treated as "bad", only as "unknown". P2 will read the description for the rest.
_SHUTTER_PATTERNS = [
    re.compile(r"(?:shutter\s*count|shutter\s*actuations?|actuations?|shutter\s*clicks?)\s*[:\-]?\s*(\d[\d,]*)\s*(k)?", re.IGNORECASE),
    re.compile(r"\bsc\s*[:\-]?\s*(\d[\d,]*)\s*(k)?\b", re.IGNORECASE),
    re.compile(r"(\d[\d,]*)\s*(k)?\s*(?:shutter\s*count|actuations?|shutter\s*clicks?|clicks)", re.IGNORECASE),
]


def parse_shutter_count(text: str) -> int | None:
    """Best-effort shutter actuations from a title. None when not stated (the common case).

    A 'k' suffix multiplies by 1000. Implausible values (0, or > 2,000,000) are ignored.
    Requires a shutter-related token so bare model/price numbers aren't misread."""
    if not text:
        return None
    low = text.lower()
    if not ("shutter" in low or "actuation" in low or "click" in low or re.search(r"\bsc\b", low)):
        return None
    for pat in _SHUTTER_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        num = m.group(1).replace(",", "")
        if not num.isdigit():
            continue
        val = int(num) * (1000 if m.group(2) else 1)
        if 0 < val <= 2_000_000:
            return val
    return None


def group_by_model(titles: list[str]) -> dict[str, list[str]]:
    """Cluster messy titles by resolved identity. Unresolved land under '__manual__'."""
    out: dict[str, list[str]] = {}
    for t in titles:
        item = parse_camera(t)
        out.setdefault(item.key() if item.resolved else "__manual__", []).append(t)
    return out


def camera_listing_from_title(
    *,
    title: str,
    price: float,
    listing_id: str,
    url: str,
    is_auction: bool,
    ends_at: str | None = None,
    bin_price: float | None = None,
    postage_in: float | None = None,
    condition: str | None = None,
    condition_id: str | None = None,
    seller_feedback_pct: float | None = None,
    seller_feedback_score: int | None = None,
) -> Listing | None:
    """Build a Listing whose identity is an exact camera/lens model.

    Resolve-or-skip: a title that doesn't pin down a specific body or lens returns
    None and never reaches valuation — the bot won't bid on a guess (the cameras-lane
    equivalent of the cards confidence gate). A `CameraItem` rides in `Listing.card`;
    it exposes the same `key()` / `label()` / `matches()` the pipeline needs, so the
    whole downstream (value -> gate -> fees -> rank) runs unchanged.
    """
    item = parse_camera(title)
    if not item.resolved:
        return None
    return Listing(
        listing_id=str(listing_id),
        card=item,  # CameraItem stands in for Card; same identity interface
        price=price,
        url=url,
        is_auction=is_auction,
        ends_at=ends_at,
        bin_price=bin_price,
        postage_in=postage_in,
        condition=condition,
        condition_id=condition_id,
        seller_feedback_pct=seller_feedback_pct,
        seller_feedback_score=seller_feedback_score,
        shutter_count=parse_shutter_count(title),
        title=title,
    )
