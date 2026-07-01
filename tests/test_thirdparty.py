import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from valbot.config import apply_sector, load_config  # noqa: E402
from valbot.ebay_client import ThirdPartySource, dig, listing_from_title  # noqa: E402
from valbot.models import Card  # noqa: E402


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


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


def _sample_sold_price_response():
    # ebay-average-selling-price /findCompletedItems shape: aggregate stats at the top,
    # rows under "products". Sold prices are already GBP for site_id 3.
    return {
        "success": True,
        "average_price": 152.0, "median_price": 150.0,
        "min_price": 95.0, "max_price": 205.0, "results": 3,
        "products": [
            {"title": "Sony A6000 body black", "sale_price": 150.0, "currency": "GBP",
             "condition": "Used", "buying_format": "Auction", "date_sold": "2026-06-28",
             "item_id": "p1", "link": "u1"},
            {"title": "Sony Alpha A6000 mirrorless camera body only", "sale_price": 95.0,
             "currency": "GBP", "date_sold": "2026-06-27", "item_id": "p2", "link": "u2"},
            # a lens listing that shouldn't match an A6000 body query
            {"title": "Sony FE 50mm f1.8 lens", "sale_price": 120.0, "currency": "GBP",
             "date_sold": "2026-06-26", "item_id": "p3", "link": "u3"},
        ],
    }


def test_sold_endpoint_issues_post_with_json_body(monkeypatch):
    # cameras sold feed is method: POST -> _get must POST the keywords in a JSON body.
    cfg = apply_sector(load_config(), "cameras-lenses")
    src = ThirdPartySource(api_key="rapid-key", cfg=cfg)
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"], captured["json"] = url, json
        return _FakeResp(_sample_sold_price_response())

    def fake_get(*a, **k):  # guard: the POST endpoint must not fall through to GET
        raise AssertionError("sold POST endpoint should not use GET")

    import requests
    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "get", fake_get)
    rows = src._get(cfg["thirdparty"]["sold"], "Sony A6000 body")
    assert captured["url"].endswith("/findCompletedItems")
    assert captured["json"]["keywords"] == "Sony A6000 body"
    assert captured["json"]["site_id"] == "3"  # UK
    assert len(rows) == 3


def test_browse_camera_targets_filter_to_model_window_and_capture_bin(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from valbot.ebay_client import BrowseAPISource

    cfg = apply_sector(load_config(), "cameras-lenses")
    src = BrowseAPISource(app_id="x", cert_id="y", cfg=cfg)
    soon = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    late = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
    items = [
        {"title": "Sony A6000 body black", "currentBidPrice": {"value": "120"},
         "price": {"value": "300"}, "buyingOptions": ["AUCTION", "FIXED_PRICE"],
         "itemId": "1", "itemWebUrl": "u1", "itemEndDate": soon},        # keep, has BIN
        {"title": "Sony 1000mm telephoto lens", "currentBidPrice": {"value": "90"},
         "buyingOptions": ["AUCTION"], "itemId": "2", "itemWebUrl": "u2",
         "itemEndDate": soon},                                           # accessory -> drop
        {"title": "Sony A6000 body", "currentBidPrice": {"value": "150"},
         "buyingOptions": ["AUCTION"], "itemId": "3", "itemWebUrl": "u3",
         "itemEndDate": late},                                           # ends >24h -> drop
    ]
    monkeypatch.setattr(src, "_search",
                        lambda q, extra_filter="", category_id="": items if "A6000" in q else [])
    targets = src.fetch_targets()
    assert len(targets) == 1
    t = targets[0]
    assert t.card.key() == "sony|body|a6000"  # only the in-window body
    assert t.price == 120.0                     # current bid
    assert t.bin_price == 300.0                 # Buy-It-Now captured


def test_browse_camera_targets_require_buy_it_now(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from valbot.ebay_client import BrowseAPISource

    cfg = apply_sector(load_config(), "cameras-lenses")
    assert cfg["search"]["require_buy_it_now"] is True  # cameras default
    src = BrowseAPISource(app_id="x", cert_id="y", cfg=cfg)
    soon = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    items = [
        {"title": "Sony A6000 body", "currentBidPrice": {"value": "120"},
         "price": {"value": "300"}, "buyingOptions": ["AUCTION", "FIXED_PRICE"],
         "itemId": "1", "itemWebUrl": "u1", "itemEndDate": soon},   # has BIN -> keep
        {"title": "Sony A6000 body", "currentBidPrice": {"value": "110"},
         "buyingOptions": ["AUCTION"], "itemId": "2", "itemWebUrl": "u2",
         "itemEndDate": soon},                                       # no BIN -> drop
    ]
    monkeypatch.setattr(src, "_search",
                        lambda q, extra_filter="", category_id="": items if "A6000" in q else [])
    targets = src.fetch_targets()
    assert len(targets) == 1 and targets[0].bin_price == 300.0


def test_get_alerter_degrades_to_print_without_callmebot(monkeypatch):
    from valbot.alert import get_alerter
    monkeypatch.delenv("CALLMEBOT_PHONE", raising=False)
    monkeypatch.delenv("CALLMEBOT_APIKEY", raising=False)
    alerter = get_alerter(dry_run=False)  # asked to send, but no secrets
    assert alerter.dry_run is True         # degrades to print-only, no crash


def test_hybrid_source_splits_targets_and_comps():
    from valbot.ebay_client import HybridSource

    class _Live:
        def fetch_targets(self):
            return ["auction1", "auction2"]
        def fetch_comps(self, card):
            raise AssertionError("comps must not come from the live source")

    class _Sold:
        cache = "CACHE"
        def fetch_targets(self):
            raise AssertionError("targets must not come from the sold source")
        def fetch_comps(self, card):
            return ["comp1"]

    src = HybridSource(live=_Live(), sold=_Sold())
    assert src.fetch_targets() == ["auction1", "auction2"]  # from Browse (live)
    assert src.fetch_comps(object()) == ["comp1"]            # from cached sold feed
    assert src.cache == "CACHE"                              # ledger surfaced for reporting


def test_camera_search_query_renders_roman_version():
    from valbot.camera import parse_camera
    # the bug that made "Sony A7 II" return 0 comps: model key is a7 2, but the search
    # term must read "A7 II" to match how sellers title listings.
    assert parse_camera("Sony A7 II body").search_query() == "Sony A7 II"
    assert parse_camera("Sony A6000 body").search_query() == "Sony A6000"
    assert parse_camera("Canon EOS 6D body").search_query() == "Canon 6D"


def test_sold_comps_drop_new_parts_and_bundles(monkeypatch):
    from valbot.camera import parse_camera
    cfg = apply_sector(load_config(), "cameras-lenses")
    src = ThirdPartySource(api_key="x", cfg=cfg)
    resp = {"products": [
        {"title": "Sony A6000 body only", "sale_price": 250.0, "condition": "Pre-owned",
         "item_id": "1", "link": "u1"},                                      # keep
        {"title": "Sony A6000 body", "sale_price": 400.0, "condition": "New",
         "item_id": "2", "link": "u2"},                                      # new -> drop
        {"title": "Sony A6000 with lens bundle", "sale_price": 390.0, "condition": "Used",
         "item_id": "3", "link": "u3"},                                      # bundle -> drop
        {"title": "Sony A6000 for parts not working", "sale_price": 80.0,
         "condition": "For parts or not working", "item_id": "4", "link": "u4"},  # parts -> drop
    ]}
    import requests
    monkeypatch.setattr(requests, "post", lambda *a, **k: _FakeResp(resp))
    comps = src.fetch_comps(parse_camera("Sony A6000 body"))
    assert [round(c.price) for c in comps] == [250]  # only the clean used body survives


def test_cameras_sold_comps_parse_and_filter_by_model(monkeypatch):
    cfg = apply_sector(load_config(), "cameras-lenses")
    src = ThirdPartySource(api_key="rapid-key", cfg=cfg)

    def fake_post(url, headers=None, json=None, timeout=None):
        return _FakeResp(_sample_sold_price_response())

    import requests
    monkeypatch.setattr(requests, "post", fake_post)
    from valbot.camera import parse_camera

    card = parse_camera("Sony A6000 body")  # CameraItem identity, resolves to sony|body|a6000
    comps = src.fetch_comps(card)
    # the two A6000 bodies match; the 50mm lens is filtered out. GBP -> no conversion.
    assert {round(c.price) for c in comps} == {150, 95}
    assert all(c.is_auction is False for c in comps)
