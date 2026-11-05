class Conflict(Exception):
    """Unique or state conflict. Mapped to HTTP 409."""


class PayloadTooLarge(Exception):
    """Mapped to HTTP 413."""
