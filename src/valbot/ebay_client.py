"""Listing sources: mock (testable now) and live eBay Browse API (swap in when keys land).

Both expose the same shape:
    fetch_targets() -> list[Listing]        # auctions ending in the search window
    fetch_comps(card) -> list[Listing]      # active listings to value that card against

Browse API is read-only and free (ADR-001). Keys are the one thing that can block
shipping today, so the mock source mirrors the interface exactly — the pipeline can't
tell them apart, and live is a one-line swap once eBay approves production access.
"""

from __future__ import annotations

import json
import re
import time
from base64 import b64encode
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from .camera import camera_listing_from_title, parse_camera
from .models import Card, Listing

GRADE_RE = re.compile(
    r"\b(PSA|BGS|SGC|CGC)\s*[- ]?\s*(10|9\.5|9|8\.5|8|7|6|5)\b", re.IGNORECASE
)


class ListingSource(Protocol):
    def fetch_targets(self) -> list[Listing]: ...
    def fetch_comps(self, card: Card) -> list[Listing]: ...


# --------------------------------------------------------------------------- mock


def _card_from_dict(d: dict) -> Card:
    return Card(
        player=d["player"],
        set_name=d["set_name"],
        variant=d.get("variant", "base"),
        grader=d["grader"],
        grade=float(d["grade"]),
    )


def _listing_from_dict(d: dict) -> Listing | None:
    """Build a Listing from a fixture entry.

    Two fixture shapes share one source: a structured `card` (slabs), or a freeform
    `title` parsed to an exact camera/lens model. A camera title that doesn't resolve
    returns None and is dropped — the mock mirrors the live resolve-or-skip rule.
    """
    if "card" not in d and "title" in d:
        return camera_listing_from_title(
            title=str(d["title"]),
            price=float(d["price"]),
            listing_id=str(d["listing_id"]),
            url=d.get("url", f"https://www.ebay.co.uk/itm/{d['listing_id']}"),
            is_auction=bool(d.get("is_auction", False)),
            ends_at=d.get("ends_at"),
        )
    return Listing(
        listing_id=str(d["listing_id"]),
        card=_card_from_dict(d["card"]),
        price=float(d["price"]),
        url=d.get("url", f"https://www.ebay.co.uk/itm/{d['listing_id']}"),
        is_auction=bool(d.get("is_auction", False)),
        ends_at=d.get("ends_at"),
        postage_in=d.get("postage_in"),
    )


class MockSource:
    """Reads targets + a comp pool from a JSON fixture. Proves the logic without keys."""

    def __init__(self, path: str | Path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._targets = [x for x in map(_listing_from_dict, data.get("targets", [])) if x]
        self._comps = [x for x in map(_listing_from_dict, data.get("comps", [])) if x]

    def fetch_targets(self) -> list[Listing]:
        return list(self._targets)

    def fetch_comps(self, card: Card) -> list[Listing]:
        return [c for c in self._comps if c.matches(card)]


# ----------------------------------------------------------------------- live API


def parse_grade(title: str) -> tuple[str, float] | None:
    """Pull grader + grade out of a listing title. None if absent."""
    m = GRADE_RE.search(title)
    if not m:
        return None
    return m.group(1).upper(), float(m.group(2))


def query_tokens(query: str) -> list[str]:
    """Player/set/variant tokens from a query, with grader+grade stripped out."""
    return [t for t in query.lower().split() if not parse_grade(t)]


def listing_from_title(
    *,
    title: str,
    price: float,
    listing_id: str,
    url: str,
    tokens: list[str],
    is_auction: bool,
    ends_at: str | None = None,
    identity: str = "card",
) -> Listing | None:
    """Build a Listing from a freeform title, by identity mode.

    identity="camera" routes to exact body/lens model parsing (resolve-or-skip);
    `tokens` are ignored there. identity="card" (default) keeps v1 behaviour: grader
    and grade parsed strictly; player/set/variant come from the query that found the
    card and must be present in the title.
    """
    if identity == "camera":
        return camera_listing_from_title(
            title=title,
            price=price,
            listing_id=listing_id,
            url=url,
            is_auction=is_auction,
            ends_at=ends_at,
        )
    parsed = parse_grade(title)
    if not parsed:
        return None
    grader, grade = parsed
    low = title.lower()
    if not all(tok in low for tok in tokens):
        return None
    card = Card(
        player=tokens[0] if tokens else "unknown",
        set_name=" ".join(tokens[1:]) if len(tokens) > 1 else "unknown",
        variant="base",
        grader=grader,
        grade=grade,
    )
    return Listing(
        listing_id=str(listing_id),
        card=card,
        price=price,
        url=url,
        is_auction=is_auction,
        ends_at=ends_at,
    )


def dig(obj: dict, path: str):
    """Fetch a value by dotted path, e.g. 'price.value'. None if any hop is missing."""
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def ends_within(ends_at: str | None, hours, *, now=None) -> bool:
    """True if ends_at is an ISO8601 timestamp that falls within the next `hours` hours."""
    if not ends_at:
        return False
    try:
        dt = datetime.fromisoformat(ends_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    return now <= dt <= now + timedelta(hours=float(hours))


class BrowseAPISource:
    """Live eBay Browse API. Read-only. Needs production App ID + Cert ID.

    Comp identity from freeform titles is approximate in v1: grader + grade are parsed
    strictly; player/set/variant are required to appear as tokens in the title (they
    come from the query that found the card). Documented limitation, swappable later.
    """

    OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
    SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    SCOPE = "https://api.ebay.com/oauth/api_scope"

    def __init__(self, app_id: str, cert_id: str, cfg: dict):
        self.app_id = app_id
        self.cert_id = cert_id
        self.cfg = cfg
        self.search_cfg = cfg["search"]
        self.identity = cfg.get("identity", "card")
        self._token: str | None = None
        self._token_expiry = 0.0

    # -- auth ----------------------------------------------------------------
    def _get_token(self) -> str:
        import requests

        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        creds = b64encode(f"{self.app_id}:{self.cert_id}".encode()).decode()
        resp = requests.post(
            self.OAUTH_URL,
            headers={
                "Authorization": f"Basic {creds}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials", "scope": self.SCOPE},
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._token_expiry = time.time() + int(body.get("expires_in", 7200))
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "X-EBAY-C-MARKETPLACE-ID": self.search_cfg["marketplace"],
            "Content-Type": "application/json",
        }

    # -- search --------------------------------------------------------------
    def _search(
        self,
        query: str,
        *,
        buying_options: str = "AUCTION",
        extra_filter: str = "",
        category_id: str = "",
    ) -> list[dict]:
        import requests

        filt = f"buyingOptions:{{{buying_options}}}"
        if extra_filter:
            filt += f",{extra_filter}"
        params = {
            "q": query,
            "filter": filt,
            "limit": str(self.search_cfg["max_results_per_query"]),
            "sort": "endingSoonest",
        }
        if category_id:
            params["category_ids"] = category_id
        resp = requests.get(
            self.SEARCH_URL, headers=self._headers(), params=params, timeout=30
        )
        resp.raise_for_status()
        return resp.json().get("itemSummaries", []) or []

    def _to_listing(self, item: dict, query_tokens: list[str]) -> Listing | None:
        title = item.get("title", "")
        price = item.get("currentBidPrice") or item.get("price") or {}
        try:
            value = float(price.get("value"))
        except (TypeError, ValueError):
            return None
        if self.identity == "camera":
            # Browse returns ACTIVE listings only -> active-listing proxy for cameras
            # (ADR-011 fallback). Identity is exact-model, resolve-or-skip.
            # An auction may ALSO offer Buy-It-Now: buyingOptions lists FIXED_PRICE and
            # `price` carries that BIN figure (currentBidPrice is the live bid).
            opts = item.get("buyingOptions") or []
            bin_price = None
            if "FIXED_PRICE" in opts:
                try:
                    bin_price = float((item.get("price") or {}).get("value"))
                except (TypeError, ValueError):
                    bin_price = None
            seller = item.get("seller") or {}
            try:
                fb_pct = float(seller.get("feedbackPercentage"))
            except (TypeError, ValueError):
                fb_pct = None
            try:
                fb_score = int(seller.get("feedbackScore"))
            except (TypeError, ValueError):
                fb_score = None
            # Real inbound postage for THIS listing (free = 0.0). None -> fall back to the
            # flat fees.postage_in estimate. shippingOptions[0] is the primary option.
            ship_in = None
            ship_opts = item.get("shippingOptions") or []
            if ship_opts:
                try:
                    ship_in = float((ship_opts[0].get("shippingCost") or {}).get("value"))
                except (TypeError, ValueError):
                    ship_in = None
            return camera_listing_from_title(
                title=title,
                price=value,
                listing_id=str(item.get("itemId")),
                url=item.get("itemWebUrl", ""),
                is_auction=bool(item.get("currentBidPrice")),
                ends_at=item.get("itemEndDate"),
                bin_price=bin_price,
                postage_in=ship_in,
                condition=item.get("condition"),
                condition_id=str(item.get("conditionId")) if item.get("conditionId") else None,
                seller_feedback_pct=fb_pct,
                seller_feedback_score=fb_score,
            )
        parsed = parse_grade(title)
        if not parsed:
            return None
        grader, grade = parsed
        low = title.lower()
        if not all(tok in low for tok in query_tokens):
            return None
        # player/set/variant come from the query that found it; identity is approximate.
        card = Card(
            player=query_tokens[0] if query_tokens else "unknown",
            set_name=" ".join(query_tokens[1:]) if len(query_tokens) > 1 else "unknown",
            variant="base",
            grader=grader,
            grade=grade,
        )
        return Listing(
            listing_id=str(item.get("itemId")),
            card=card,
            price=value,
            url=item.get("itemWebUrl", ""),
            is_auction=True,
            ends_at=item.get("itemEndDate"),
        )

    def fetch_targets(self) -> list[Listing]:
        window = self.search_cfg.get("ending_within_hours")
        if self.identity == "camera":
            return self._fetch_camera_targets(window)
        out: list[Listing] = []
        for query in self.search_cfg["queries"]:
            tokens = [t for t in query.lower().split() if not parse_grade(t)]
            for item in self._search(query):
                lst = self._to_listing(item, tokens)
                if not lst:
                    continue
                if window and not ends_within(lst.ends_at, window):
                    continue
                out.append(lst)
        return out

    def _fetch_camera_targets(self, window) -> list[Listing]:
        """Buyable candidates restricted to the EXACT niche model each query is for.

        Searches BOTH auctions and fixed-price/Buy-It-Now listings. A raw "Sony A6000
        body" search also returns lenses/straps; keeping only listings that match the
        intended body (plus the body category filter and price floor) means we never
        value accessories — and comps stay cache hits, so a live run spends 0 sold pulls.

        The ending `window` gates ONLY pure auctions (they vanish when they close). A
        listing with a Buy-It-Now price — a fixed-price listing, or an auction that also
        offers BIN — is snap-buyable any time, so it's kept regardless of end time.
        `require_buy_it_now` (default off) can restrict to snap-buyable listings only."""
        cat_map = self.search_cfg.get("category_ids") or {}
        floors = (self.cfg.get("valuation") or {}).get("comp_min_price") or {}
        require_bin = bool(self.search_cfg.get("require_buy_it_now"))
        # Quality / risk gates: don't tell Ben to buy a broken body (it looks like a
        # bargain only because it's compared to WORKING comps), or bid via a dodgy seller.
        excl_cond = [c.lower() for c in self.search_cfg.get("exclude_target_conditions", [])]
        excl_kw = [k.lower() for k in self.search_cfg.get("exclude_target_title_keywords", [])]
        # Body-only guard: a body target whose title says "with lens"/"kit"/"twin" is a
        # bundle, not a bare body — valuing it against body-only comps mis-prices it. These
        # apply ONLY to body niches (a "kit lens" IS the item for a lens niche).
        excl_kw_body = [k.lower() for k in self.search_cfg.get("exclude_target_title_keywords_body", [])]
        min_fb = self.search_cfg.get("min_seller_feedback_pct")
        out: list[Listing] = []
        for query in self.search_cfg["queries"]:
            intended = parse_camera(query)
            if not intended.resolved:
                continue
            kw = excl_kw + (excl_kw_body if intended.kind == "body" else [])
            category_id = cat_map.get(intended.kind, "") if isinstance(cat_map, dict) else ""
            for item in self._search(
                query, buying_options="FIXED_PRICE|AUCTION", category_id=category_id
            ):
                lst = self._to_listing(item, [])
                if not lst or not lst.card.matches(intended):
                    continue  # drop accessories / other models the keyword dragged in
                if not self._quality_ok(lst, excl_cond, kw, min_fb):
                    continue  # broken / bundle / low-feedback -> never auto-alert
                snap_buyable = lst.bin_price is not None or not lst.is_auction
                if require_bin and not snap_buyable:
                    continue  # optional: keep only listings you can Buy-It-Now
                # Window applies only to pure auctions; a BIN is buyable any time.
                if not snap_buyable and window and not ends_within(lst.ends_at, window):
                    continue
                floor = floors.get(getattr(lst.card, "kind", ""))
                if floor and lst.price < floor:
                    continue
                out.append(lst)
        return out

    @staticmethod
    def _quality_ok(lst, excl_cond: list[str], excl_kw: list[str], min_fb) -> bool:
        """False for a target we should never auto-alert on: a broken/for-parts item
        (its cheap price is condition, not mispricing) or a low-feedback seller (risk).
        Signals come from the Browse condition/conditionId/seller fields + the title."""
        cond = (lst.condition or "").lower()
        if excl_cond and any(c in cond for c in excl_cond):
            return False
        if lst.condition_id and str(lst.condition_id) == "7000":  # For parts or not working
            return False
        if excl_kw:
            title = (getattr(lst.card, "raw", "") or "").lower()
            if any(k in title for k in excl_kw):
                return False
        if min_fb is not None and lst.seller_feedback_pct is not None:
            if lst.seller_feedback_pct < float(min_fb):
                return False
        return True

    def fetch_comps(self, card) -> list[Listing]:
        if self.identity == "camera":
            floors = (self.cfg.get("valuation") or {}).get("comp_min_price") or {}
            cat_map = (self.search_cfg.get("category_ids") or {})
            category_id = cat_map.get(getattr(card, "kind", ""), "") if isinstance(cat_map, dict) else ""
            out: list[Listing] = []
            for item in self._search(
                card.search_query(),
                buying_options="FIXED_PRICE|AUCTION",
                category_id=category_id,
            ):
                lst = self._to_listing(item, [])
                if not lst or not lst.card.matches(card):
                    continue
                floor = floors.get(getattr(lst.card, "kind", ""))
                if floor and lst.price < floor:
                    continue
                out.append(lst)
            return out
        query = f"{card.player} {card.set_name} {card.grader} {card.grade:g}"
        tokens = [t for t in query.lower().split() if not parse_grade(t)]
        out = []
        # Comps are active listings of any buying option, not just auctions.
        for item in self._search(query, buying_options="FIXED_PRICE|AUCTION"):
            lst = self._to_listing(item, tokens)
            if lst and lst.card.grader == card.grader and lst.card.grade == card.grade:
                out.append(lst)
        return out


# ------------------------------------------------------- third-party (RapidAPI)


class ThirdPartySource:
    """Live listings + real sold comps via a third-party RapidAPI provider.

    No eBay developer account. One key. Two endpoints, both configured in
    config.yaml under `thirdparty` so you can point it at whichever provider you
    subscribe to without touching code:
      - live: active auctions ending soon -> targets to act on.
      - sold: real sold prices -> comps to value against (better than asking).

    The field mapping (where the title/price/id live in their JSON) is config, because
    providers shape responses differently. Confirm the four field paths against your
    provider's sample response once, then it just runs.
    """

    def __init__(self, api_key: str | None = None, cfg: dict = None, cache=None):
        self.api_key = api_key  # RapidAPI key, when injected (tests / single-provider)
        self.cfg = cfg
        self.tp = cfg["thirdparty"]
        self.search_cfg = cfg["search"]
        self.identity = cfg.get("identity", "card")
        # Optional SoldFeedCache: caches metered endpoints (cache_days) and enforces
        # their monthly_pull_budget. None in tests/mock -> every call hits the network.
        self.cache = cache
        # Defense-in-depth: cap live pulls PER RUN (on top of the monthly ledger) so one
        # cold-cache run can't burn the whole month's budget in a burst. Bounded here;
        # skipped models simply fetch on the next run as the cache warms.
        self._run_pulls = 0
        # Circuit breaker: once the metered feed errors (e.g. 429 rate limit), stop hitting
        # it for the rest of this run — every later query would just error too.
        self._feed_down = False

    def _auth_for(self, endpoint: dict) -> dict:
        """Auth config for an endpoint, falling back to the provider default (RapidAPI)."""
        return endpoint.get("auth") or self.tp.get("auth") or {
            "scheme": "rapidapi",
            "secret": "RAPIDAPI_KEY",
        }

    def _key_for(self, auth: dict) -> str:
        name = auth.get("secret", "RAPIDAPI_KEY")
        # an injected api_key stands in for the RapidAPI default (keeps tests keyless)
        if self.api_key is not None and name == "RAPIDAPI_KEY":
            return self.api_key
        from .config import secret

        return secret(name)

    def _headers_for(self, endpoint: dict) -> dict:
        auth = self._auth_for(endpoint)
        key = self._key_for(auth)
        if auth.get("scheme") == "header":
            return {auth["header"]: key}
        return {
            "X-RapidAPI-Key": key,
            "X-RapidAPI-Host": endpoint.get("host", self.tp["api_host"]),
        }

    def _fx_factor(self, endpoint: dict) -> float:
        """Convert the endpoint's price currency to GBP. 1.0 if already GBP."""
        cur = (endpoint.get("currency") or "GBP").upper()
        if cur == "GBP":
            return 1.0
        if cur == "USD":
            return float(self.cfg.get("fx", {}).get("usd_to_gbp", 1.0))
        return 1.0

    def _get(self, endpoint: dict, query: str) -> list[dict]:
        import requests

        # Metered endpoints opt into caching + budget via `cache_days`. A fresh cache
        # hit returns with zero network + zero pulls; a miss checks the monthly budget
        # BEFORE spending a pull (raises BudgetExceeded once it's gone), then records it.
        cache_days = endpoint.get("cache_days")
        cached = self.cache.get(
            endpoint["url"], query, cache_days, endpoint.get("empty_cache_days")
        ) if (self.cache and cache_days) else None
        if cached is not None:
            return cached
        metered = bool(self.cache and cache_days)
        if metered:
            from .cache import BudgetExceeded, FeedUnavailable

            if self._feed_down:  # breaker tripped earlier this run — don't hammer the feed
                raise FeedUnavailable("sold feed already errored this run; skipping.")
            run_cap = endpoint.get("max_pulls_per_run")
            if run_cap is not None and self._run_pulls >= int(run_cap):
                raise BudgetExceeded(
                    f"per-run sold-feed pull cap reached ({run_cap}); skipping live "
                    "pull (cached data still served)."
                )
            self.cache.check_budget(endpoint.get("monthly_pull_budget"))

        # Some sold-price providers take the search term + filters as a JSON POST body
        # (e.g. ebay-average-selling-price /findCompletedItems) rather than GET params.
        # `method: POST` in the endpoint config routes here; the field mapping is unchanged.
        payload = {endpoint["query_param"]: query, **endpoint.get("extra_params", {})}
        headers = self._headers_for(endpoint)
        try:
            if (endpoint.get("method") or "GET").upper() == "POST":
                resp = requests.post(endpoint["url"], headers=headers, json=payload, timeout=30)
            else:
                resp = requests.get(endpoint["url"], headers=headers, params=payload, timeout=30)
            resp.raise_for_status()
            body = resp.json()
        except requests.exceptions.RequestException as e:
            # 429 rate limit / 5xx / timeout / network: a read-only run must never crash on
            # the feed. Trip the breaker and degrade to "no fresh comps" for this query. Do
            # NOT record a pull or cache anything — the miss retries on a later run.
            if metered:
                self._feed_down = True
                from .cache import FeedUnavailable

                raise FeedUnavailable(f"sold feed unavailable ({e}); skipping.") from e
            raise
        items = dig(body, endpoint["items_path"]) if endpoint.get("items_path") else body
        items = items or []
        if metered:
            self.cache.record_pull()
            self._run_pulls += 1
            self.cache.put(endpoint["url"], query, items)
        return items

    def _parse(
        self, items: list[dict], endpoint: dict, tokens, is_auction, kind=None
    ) -> list[Listing]:
        f = endpoint["fields"]
        fx = self._fx_factor(endpoint)
        # Optional client-side cleaning (applied to cached raw items too -> 0 extra pulls):
        # drop new/parts conditions and multi-item bundles so the comp distribution
        # reflects genuine used single items, not boxed kits or spares/repair units.
        excl_cond = [c.lower() for c in endpoint.get("exclude_conditions", [])]
        excl_kw = [k.lower() for k in endpoint.get("exclude_title_keywords", [])]
        # Body-only excludes (kit/zoom/"with lens"...) would wrongly gut a LENS comp set
        # — a zoom IS a lens, a kit lens IS the item. Apply them only when valuing a body.
        if kind == "body":
            excl_kw += [k.lower() for k in endpoint.get("exclude_title_keywords_body", [])]
        out: list[Listing] = []
        for item in items:
            title = str(dig(item, f["title"]) or "")
            low = title.lower()
            if excl_kw and any(k in low for k in excl_kw):
                continue
            if excl_cond and "condition" in f:
                cond = str(dig(item, f["condition"]) or "").lower()
                if any(c in cond for c in excl_cond):
                    continue
            price_raw = dig(item, f["price"])
            try:
                price = float(price_raw) * fx
            except (TypeError, ValueError):
                continue
            lst = listing_from_title(
                title=title,
                price=price,
                listing_id=str(dig(item, f["id"]) or ""),
                url=str(dig(item, f["url"]) or ""),
                tokens=tokens,
                is_auction=is_auction,
                ends_at=dig(item, f["ends_at"]) if "ends_at" in f else None,
                identity=self.identity,
            )
            if lst:
                out.append(lst)
        return out

    def fetch_targets(self) -> list[Listing]:
        out: list[Listing] = []
        for query in self.search_cfg["queries"]:
            items = self._get(self.tp["live"], query)
            out.extend(self._parse(items, self.tp["live"], query_tokens(query), True))
        return out

    def fetch_comps(self, card) -> list[Listing]:
        if self.identity == "camera":
            query = card.search_query()  # Roman-numeral versions so "A7 II" matches listings
            items = self._get(self.tp["sold"], query)
            comps = self._parse(
                items, self.tp["sold"], [], False, kind=getattr(card, "kind", None)
            )
            return [c for c in comps if c.card.matches(card)]
        query = f"{card.player} {card.set_name} {card.grader} {card.grade:g}"
        items = self._get(self.tp["sold"], query)
        comps = self._parse(items, self.tp["sold"], query_tokens(query), False)
        return [
            c for c in comps if c.card.grader == card.grader and c.card.grade == card.grade
        ]


class HybridSource:
    """Current auctions from one source, sold comps from another.

    Built for the cameras lane: live auctions come FREE from eBay's Browse API, while
    comps come from the cached RapidAPI sold feed (real completed sales, 30-day cache,
    50/month budget). That keeps live running effectively free — auctions are free and
    comps are almost always cache hits — instead of valuing against Browse's ACTIVE
    listings (asking-price proxy). Exposes the same fetch_targets/fetch_comps interface.
    """

    def __init__(self, live: ListingSource, sold: ListingSource):
        self._live = live
        self._sold = sold
        # surface the sold cache so the scanner / budget reporting can read the ledger
        self.cache = getattr(sold, "cache", None)

    def fetch_targets(self) -> list[Listing]:
        return self._live.fetch_targets()

    def fetch_comps(self, card) -> list[Listing]:
        return self._sold.fetch_comps(card)


def get_source(cfg: dict, mode: str, mock_path: str | Path | None = None) -> ListingSource:
    """Factory.

    mode 'mock'       — built-in fixture, no keys (testing).
    mode 'thirdparty' — RapidAPI live + sold (default live route, no eBay dev account).
    mode 'hybrid'     — live auctions from eBay Browse (free) + comps from the cached
                        RapidAPI sold feed. Needs EBAY_APP_ID/EBAY_CERT_ID + RAPIDAPI_KEY.
    mode 'browse'     — official eBay Browse API (free fallback, needs dev keys).
    """
    if mode == "mock":
        from .config import ROOT

        path = mock_path or (ROOT / "data" / "mock_listings.json")
        return MockSource(path)
    if mode == "thirdparty":
        from .cache import SoldFeedCache
        from .config import ROOT, secret

        # RapidAPI key (live source) is optional here; the sold source uses its own key.
        # Each endpoint resolves the key it needs when first called. The cache backs the
        # metered sold feed (cache_days / monthly_pull_budget in config) — see cache.py.
        return ThirdPartySource(
            api_key=secret("RAPIDAPI_KEY", required=False),
            cfg=cfg,
            cache=SoldFeedCache(ROOT / "data" / "cache"),
        )
    if mode == "browse":
        from .config import secret

        return BrowseAPISource(
            app_id=secret("EBAY_APP_ID"),
            cert_id=secret("EBAY_CERT_ID"),
            cfg=cfg,
        )
    if mode == "hybrid":
        from .cache import SoldFeedCache
        from .config import ROOT, secret

        live = BrowseAPISource(
            app_id=secret("EBAY_APP_ID"),
            cert_id=secret("EBAY_CERT_ID"),
            cfg=cfg,
        )
        sold = ThirdPartySource(
            api_key=secret("RAPIDAPI_KEY", required=False),
            cfg=cfg,
            cache=SoldFeedCache(ROOT / "data" / "cache"),
        )
        return HybridSource(live=live, sold=sold)
    raise ValueError(f"unknown source mode: {mode!r}")
