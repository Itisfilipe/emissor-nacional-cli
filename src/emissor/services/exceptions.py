from __future__ import annotations


class SefinRejectError(Exception):
    """SEFIN returned 200 OK but the response indicates rejection or missing chNFSe."""

    def __init__(self, message: str, response: dict | None = None) -> None:
        super().__init__(message)
        self.response = response or {}
