"""Ephemeral DLP masking context for AI agent proxy.

Masks internal asset values before sending to the LLM,
unmasks tokens in the response stream. Map is never persisted.
"""

from typing import Any


class DLPMaskingContext:
    """Session-scoped, ephemeral mask map. Never persisted."""

    def __init__(self, assets: list[Any]) -> None:
        self._map: dict[str, str] = {}       # token -> real value
        self._reverse: dict[str, str] = {}   # real value -> token
        counters: dict[str, int] = {}

        for asset in assets:
            if asset.status != "INTERNAL":
                continue
            # Extract type prefix: IP from IP_ADDRESS, DOMAIN from DOMAIN,
            # FILE from FILE_HASH_*
            asset_type = asset.type.split("_")[0]
            counters[asset_type] = counters.get(asset_type, 0) + 1
            token = f"[INTERNAL_{asset_type}_{counters[asset_type]:03d}]"
            self._map[token] = asset.value
            self._reverse[asset.value] = token

    def mask(self, text: str) -> str:
        """Replace real internal values with tokens."""
        for real_value, token in self._reverse.items():
            text = text.replace(real_value, token)
        return text

    def unmask(self, text: str) -> str:
        """Replace tokens with real internal values."""
        for token, real_value in self._map.items():
            text = text.replace(token, real_value)
        return text
