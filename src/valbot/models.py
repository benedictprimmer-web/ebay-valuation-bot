"""Core data types. One Listing shape for both target auctions and comps."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass(frozen=True)
class Card:
    """The identity a comp must match strictly. A PSA 9 is not a PSA 10."""

    player: str
    set_name: str
    variant: str  # parallel / variant, e.g. "base", "silver prizm", "refractor"
    grader: str  # PSA, BGS, SGC
    grade: float  # 10, 9.5, 9 ...

    def key(self) -> str:
        return " | ".join(
            [
                self.player.strip().lower(),
                self.set_name.strip().lower(),
                self.variant.strip().lower(),
                self.grader.strip().upper(),
                f"{self.grade:g}",
            ]
        )

    def label(self) -> str:
        return (
            f"{self.player} — {self.set_name} {self.variant} "
            f"{self.grader} {self.grade:g}"
        )


@dataclass(frozen=True)
class Listing:
    """An eBay listing. `price` is asking (fixed-price comp) or current bid (auction)."""

    listing_id: str
    card: Card
    price: float  # GBP — asking (fixed-price comp) or current bid (auction)
    url: str
    is_auction: bool = False
    ends_at: Optional[str] = None  # ISO8601, auctions only
    postage_in: Optional[float] = None  # seller's stated inbound postage, if known
    bin_price: Optional[float] = None  # Buy-It-Now price, if the auction also offers one

    def matches(self, card: Card) -> bool:
        return self.card.key() == card.key()


@dataclass
class Valuation:
    """The distribution, not a point. conservative_value drives every money decision."""

    card: Card
    n: int
    point_value: float
    dispersion: float  # on the value scale (asking spread x ratio)
    rel_dispersion: float  # dispersion / point_value
    conservative_value: float
    confidence: float  # 0..1
    confidence_label: str  # high / medium / low
    ratio: float  # sold-to-asking ratio used

    def as_dict(self) -> dict:
        d = asdict(self)
        d["card"] = self.card.label()
        return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in d.items()}


@dataclass
class Assessment:
    """A target auction run through value -> gate -> fees -> floors."""

    listing: Listing
    valuation: Optional[Valuation]
    max_bid: Optional[float]
    expected_profit: Optional[float]  # if won at current price
    margin: Optional[float]  # expected_profit / conservative_value
    headroom: Optional[float]  # max_bid - current price
    fee_breakdown: dict = field(default_factory=dict)
    passed_gate: bool = False
    passed_floors: bool = False
    reasons: list[str] = field(default_factory=list)

    @property
    def is_alert(self) -> bool:
        return self.passed_gate and self.passed_floors
