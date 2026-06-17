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
_APERTURE = re.compile(r"f/?\s?(\d{1,2}(?:\.\d+)?)")
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
    ("nikon", re.compile(r"\b(z)\s?(\d|f|fc)\b")),
    ("nikon", re.compile(r"\b(d)\s?(\d{3,4})\b")),
    ("fujifilm", re.compile(r"\b(x)\s?(t|s|h|e|pro)\s?(\d+)\b")),
    ("fujifilm", re.compile(r"\b(x100)\s?([a-z]+)?\b")),
    ("panasonic", re.compile(r"\b(gh|g|s|fz)\s?(\d+)\b")),
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
        return f"{self.brand.title()} {self.model}".strip()


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


def group_by_model(titles: list[str]) -> dict[str, list[str]]:
    """Cluster messy titles by resolved identity. Unresolved land under '__manual__'."""
    out: dict[str, list[str]] = {}
    for t in titles:
        item = parse_camera(t)
        out.setdefault(item.key() if item.resolved else "__manual__", []).append(t)
    return out
