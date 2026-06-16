"""WhatsApp alerts via CallMeBot (ADR-007). One HTTPS GET. Free, no registration.

After the one-time activation (README step), CallMeBot gives Ben a personal API key.
Set CALLMEBOT_PHONE and CALLMEBOT_APIKEY as repo secrets. Dry-run prints instead of
sending, so the whole pipeline is testable with no key.
"""

from __future__ import annotations

from urllib.parse import quote


class CallMeBotAlerter:
    ENDPOINT = "https://api.callmebot.com/whatsapp.php"

    def __init__(self, phone: str, apikey: str, dry_run: bool = False):
        self.phone = phone
        self.apikey = apikey
        self.dry_run = dry_run

    def send(self, text: str) -> bool:
        if self.dry_run:
            print("---- [dry-run] WhatsApp message ----")
            print(text)
            print("------------------------------------")
            return True
        import requests

        url = (
            f"{self.ENDPOINT}?phone={quote(self.phone)}"
            f"&text={quote(text)}&apikey={quote(self.apikey)}"
        )
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return True


def get_alerter(dry_run: bool = False) -> CallMeBotAlerter:
    if dry_run:
        return CallMeBotAlerter(phone="", apikey="", dry_run=True)
    from .config import secret

    return CallMeBotAlerter(
        phone=secret("CALLMEBOT_PHONE"),
        apikey=secret("CALLMEBOT_APIKEY"),
        dry_run=False,
    )
