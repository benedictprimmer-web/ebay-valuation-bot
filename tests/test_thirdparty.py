import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from valbot.config import load_config  # noqa: E402
from valbot.ebay_client import ThirdPartySource, dig, listing_from_title  # noqa: E402
from valbot.models import Card  # noqa: E402


def test_dig_dotted_path():
    assert dig({"price": {"value": 42}}, "price.value") == 42
    assert dig({"a": 1}, "a.b") is None


def test_listing_from_title_strict_on_grade():
    ok = listing_from_title(
        title="Erling Haaland Topps Chrome PSA 10 Gem Mint",
        price=90.0, listing_id="1", url="u",
        tokens=["haaland", "topps", "chrome"], is_auction=True,
    )
    assert ok is not None and ok.card.grade == 10
    # title missing a required token -> rejected
    assert listing_from_title(
        title="Mbappe Prizm PSA 10", price=50.0, listing_id="2", url="u",
        tokens=["haaland", "topps"], is_auction=True,
    ) is None
    # no grade in title -> rejected
    assert listing_from_title(
        title="Haaland Topps Chrome rookie", price=50.0, listing_id="3", url="u",
        tokens=["haaland"], is_auction=True,
    ) is None


def _sample_sold_response():
    # The Card API GET /sales shape: records under "data", USD `price`, extra fields ignored.
    return {
        "data": [
            {"id": "s1", "platform": "eBay", "listing_type": "auction", "price": 92.00,
             "currency": "USD", "title": "Erling Haaland Topps Chrome PSA 10",
             "listing_url": "u1", "grade": None, "grader": None},
            {"id": "s2", "platform": "eBay", "listing_type": "best_offer", "price": 95.00,
             "currency": "USD", "title": "2023 Topps Chrome Erling Haaland PSA 10 Gem",
             "listing_url": "u2"},
            {"id": "s3", "platform": "eBay", "listing_type": "auction", "price": 55.00,
             "currency": "USD", "title": "Erling Haaland Topps Chrome PSA 9",
             "listing_url": "u3"},
        ],
        "pagination": {"total": 3, "page": 1},
    }


def test_thirdparty_comps_parse_and_filter(monkeypatch):
    cfg = load_config()
    src = ThirdPartySource(api_key="x", cfg=cfg)
    # stand in for the HTTP call
    monkeypatch.setattr(src, "_get", lambda endpoint, query: _sample_sold_response()["data"])
    card = Card("Haaland", "Topps Chrome", "base", "PSA", 10)
    comps = src.fetch_comps(card)
    # the PSA 9 row is filtered out; two PSA 10 comps remain
    assert len(comps) == 2
    assert all(c.is_auction is False for c in comps)
    # prices arrive in USD and are converted to GBP via fx.usd_to_gbp
    fx = cfg["fx"]["usd_to_gbp"]
    assert {round(c.price) for c in comps} == {round(92.0 * fx), round(95.0 * fx)}


def test_sold_endpoint_uses_card_api_header_auth(monkeypatch):
    monkeypatch.setenv("CARDAPI_KEY", "tca_test_key")
    cfg = load_config()
    src = ThirdPartySource(cfg=cfg)  # no RapidAPI key needed for the sold source
    headers = src._headers_for(cfg["thirdparty"]["sold"])
    assert headers == {"x-market-api-key": "tca_test_key"}


def test_live_endpoint_uses_rapidapi_auth():
    cfg = load_config()
    src = ThirdPartySource(api_key="rapid-key", cfg=cfg)
    headers = src._headers_for(cfg["thirdparty"]["live"])
    assert headers["X-RapidAPI-Key"] == "rapid-key"
    assert headers["X-RapidAPI-Host"] == cfg["thirdparty"]["api_host"]
