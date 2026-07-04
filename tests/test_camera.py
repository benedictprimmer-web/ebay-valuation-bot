import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from valbot.camera import (  # noqa: E402
    CameraItem,
    group_by_model,
    parse_camera,
    parse_shutter_count,
)
from valbot.config import ROOT  # noqa: E402


def test_parse_shutter_count_variants_and_unknown():
    assert parse_shutter_count("Sony A6000 body shutter count 12,345") == 12345
    assert parse_shutter_count("Canon 6D SC 12k") == 12000
    assert parse_shutter_count("Nikon D610 45000 actuations") == 45000
    assert parse_shutter_count("Sony A7 II 180,000 shutter count") == 180000
    # unknown is the common case and must never look like a bad (low/zero) value
    assert parse_shutter_count("Sony A6000 body only boxed") is None
    assert parse_shutter_count("Nikon D3200 body 18-55mm") is None  # focal, not a count
    assert parse_shutter_count("") is None


def test_body_variants_resolve_to_same_key():
    titles = [
        "Sony A7 III Body",
        "sony a7iii mirrorless",
        "Sony Alpha 7 Mark III camera",
        "SONY A7 MK3 body only",
    ]
    keys = {parse_camera(t).key() for t in titles}
    assert len(keys) == 1  # all the same identity
    assert parse_camera(titles[0]).model == "a7 3"


def test_grade_suffix_distinguishes_models():
    assert parse_camera("Sony A7 III").key() != parse_camera("Sony A7R IV").key()
    assert parse_camera("Canon EOS R6").key() != parse_camera("Canon EOS R6 Mark II").key()


def test_lens_focal_and_aperture():
    c = parse_camera("Canon RF 50mm F1.8 STM lens")
    assert c.kind == "lens"
    assert c.model == "rf 50mm f1.8"  # mount kept, aperture not the mount's 'f'
    z = parse_camera("Canon EF 24-70mm f/2.8L USM")
    assert z.model == "ef 24-70mm f2.8"  # zoom range preserved


def test_brand_misspelling_fixed():
    assert parse_camera("Cannon eos rp body").brand == "canon"


def test_unresolved_goes_to_manual():
    c = parse_camera("job lot of old cameras untested")
    assert not c.resolved
    assert c.kind == "unknown"


def test_brand_without_model_is_unresolved():
    c = parse_camera("Sony camera bargain look")
    assert c.brand == "sony"
    assert not c.resolved  # no specific model -> don't value it


def test_matches_requires_resolved():
    a = parse_camera("job lot cameras")
    b = parse_camera("another junk lot")
    assert not a.matches(b)  # two unresolved items never match


def test_grouping_clusters_comps():
    g = group_by_model([
        "Sony A7 III", "Sony a7iii body", "Sony A7 Mark 3",
        "Canon RF 50mm f1.8", "Canon RF 50mm F1.8 STM", "random junk",
    ])
    assert len(g["sony|body|a7 3"]) == 3
    assert len(g["canon|lens|rf 50mm f1.8"]) == 2
    assert g["__manual__"] == ["random junk"]


def test_previously_unresolved_bodies_now_parse():
    """Regression: Canon EOS M-series, 2-digit Nikons, and Panasonic GX/GF/GM bodies
    used to fall through to unresolved (silently skipped). They must resolve now."""
    assert parse_camera("Canon EOS M50 body").key() == "canon|body|m50"
    assert parse_camera("Canon EOS M50 Mark II body").key() == "canon|body|m50 2"
    assert parse_camera("Nikon D90 body").key() == "nikon|body|d90"
    assert parse_camera("Nikon D6 body").key() == "nikon|body|d6"
    assert parse_camera("Panasonic Lumix GX80 body").key() == "panasonic|body|gx80"
    assert parse_camera("Panasonic Lumix GF7").key() == "panasonic|body|gf7"
    # and the broadened patterns must not swallow existing identities
    assert parse_camera("Canon EOS 6D body").key() == "canon|body|6d"
    assert parse_camera("Panasonic Lumix G7 body").key() == "panasonic|body|g7"
    assert parse_camera("Nikon D610 body").key() == "nikon|body|d610"


def test_fixture_mostly_resolves():
    data = json.loads((ROOT / "data" / "mock_cameras.json").read_text())
    titles = [e["title"] for e in data["targets"] + data["comps"]]
    items = [parse_camera(t) for t in titles]
    resolved = [i for i in items if i.resolved]
    # real models resolve; the three junk lots (1 target + 2 comps) must not
    assert len(resolved) == len(items) - 3
