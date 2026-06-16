"""valbot — read-only eBay valuation bot for graded sports cards.

Values active-listing comps with uncertainty baked in, then alerts (WhatsApp via
CallMeBot) when an auction is underpriced after all fees. No bidding. See CONTEXT.md
and docs/adr/ for the locked decisions this implements.
"""

__version__ = "1.0.0"
