"""Raised when a submitted URL is not a public web address."""


class UnsafeUrlError(ValueError):
    """The URL must not be fetched."""
