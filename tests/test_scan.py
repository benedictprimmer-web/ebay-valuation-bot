import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from valbot.cache import BudgetExceeded  # noqa: E402
from valbot.camera import camera_listing_from_title, parse_camera  # noqa: E402
from valbot.config import apply_sector, load_config  # noqa: E402
from valbot.models import Card  # noqa: E402
from valbot.scan import resolve_query, scan, scatter_stats  # noqa: E402


def test_resolve_query_camera_and_card():
    cam = resolve_query("Sony A6000 body", "camera")
    assert cam is not None and cam.key() == "sony|body|a6000"
    assert resolve_query("some random junk", "camera") is None
    card = resolve_query("PSA 10 panini prizm", "card")
    assert isinstance(card, Card) and card.grader == "PSA" and card.grade == 10


def test_scatter_stats_math():
    s = scatter_stats([100.0, 100.0, 100.0], "mad")
    assert s["rel_dispersion"] == 0.0 and s["edge_gbp"] == 0.0
    s2 = scatter_stats([90.0, 150.0, 200.0], "mad")
    assert s2["n"] == 3 and s2["median"] == 150.0
    assert s2["min"] == 90.0 and s2["max"] == 200.0
    assert s2["edge_gbp"] == 60.0  # median - min
    assert s2["score"] > 0
    assert scatter_stats([], "mad") == {}


class _StubSource:
    """Returns preset comps per model key; no network, no cache."""

    def __init__(self, comps_by_key, cache=None):
        self._by_key = comps_by_key
        self.cache = cache

    def fetch_comps(self, ident):
        return self._by_key.get(ident.key(), [])


def _cam_comps(titles_prices):
    out = []
    for i, (title, price) in enumerate(titles_prices):
        lst = camera_listing_from_title(
            title=title, price=price, listing_id=str(i), url="u", is_auction=False
        )
        assert lst is not None
        out.append(lst)
    return out


def test_scan_ranks_scattered_niche_first():
    cfg = apply_sector(load_config(), "cameras-lenses")
    cfg["search"]["queries"] = ["Sony A6000 body", "Nikon D610 body"]
    # A6000: wide scatter. D610: tight cluster.
    scattered = _cam_comps([("Sony A6000 body", 90.0), ("Sony A6000 body", 140.0),
                            ("Sony A6000 body", 200.0)])
    tight = _cam_comps([("Nikon D610 body", 230.0), ("Nikon D610 body", 235.0),
                        ("Nikon D610 body", 240.0)])
    src = _StubSource({
        parse_camera("Sony A6000 body").key(): scattered,
        parse_camera("Nikon D610 body").key(): tight,
    })
    rows = scan(cfg, src)
    assert [r["query"] for r in rows][0] == "Sony A6000 body"  # scatter ranks first
    assert rows[0]["stats"]["rel_dispersion"] > rows[1]["stats"]["rel_dispersion"]
    assert all(r["source"] == "live" for r in rows)  # no cache attached


class _SpentCache:
    def pulls_this_month(self):
        return 50


class _BudgetSpentSource:
    cache = _SpentCache()

    def fetch_comps(self, ident):
        raise BudgetExceeded("spent")


def test_scan_marks_skipped_when_budget_spent():
    cfg = apply_sector(load_config(), "cameras-lenses")
    cfg["search"]["queries"] = ["Sony A6000 body"]
    rows = scan(cfg, _BudgetSpentSource())
    assert rows[0]["source"] == "skipped (budget)"
    assert rows[0]["stats"] == {}
