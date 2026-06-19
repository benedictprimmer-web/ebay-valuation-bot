"""Tests for ends_within() — the ending-window filter used by BrowseAPISource.fetch_targets."""

from datetime import datetime, timedelta, timezone

import pytest

from valbot.ebay_client import ends_within

# Fixed "now" used across all tests so results don't depend on wall-clock time.
_NOW = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)


def _ts(offset_hours: float) -> str:
    """ISO8601 UTC timestamp offset_hours from _NOW."""
    dt = _NOW + timedelta(hours=offset_hours)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


# -- core window behaviour ---------------------------------------------------

def test_inside_window_kept():
    assert ends_within(_ts(12), hours=24, now=_NOW) is True


def test_seven_days_out_dropped():
    assert ends_within(_ts(7 * 24), hours=24, now=_NOW) is False


def test_boundary_inclusive():
    # Exactly at the boundary (now + 24h) should be kept.
    assert ends_within(_ts(24), hours=24, now=_NOW) is True


def test_already_ended_dropped():
    assert ends_within(_ts(-1), hours=24, now=_NOW) is False


def test_ending_now_kept():
    # dt == now is inside the window.
    assert ends_within(_ts(0), hours=24, now=_NOW) is True


# -- edge cases: bad / missing data ------------------------------------------

def test_missing_ends_at_dropped():
    assert ends_within(None, hours=24, now=_NOW) is False


def test_empty_string_dropped():
    assert ends_within("", hours=24, now=_NOW) is False


def test_bad_timestamp_dropped():
    assert ends_within("not-a-date", hours=24, now=_NOW) is False


# -- timezone handling -------------------------------------------------------

def test_z_suffix_parsed():
    # Browse API returns "Z" suffix; must be treated as UTC.
    ts = "2026-06-19T18:00:00.000Z"
    now = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)
    assert ends_within(ts, hours=24, now=now) is True


def test_plus00_offset_parsed():
    # Some providers return +00:00 instead of Z.
    ts = "2026-06-19T18:00:00+00:00"
    now = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)
    assert ends_within(ts, hours=24, now=now) is True


def test_naive_timestamp_treated_as_utc():
    # A timestamp with no timezone info should be accepted and treated as UTC.
    ts = "2026-06-19T18:00:00"
    now = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)
    assert ends_within(ts, hours=24, now=now) is True
