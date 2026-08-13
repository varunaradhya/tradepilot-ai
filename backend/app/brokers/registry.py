from __future__ import annotations

from typing import Type

from app.brokers.base import BrokerAdapter


class BrokerRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, Type[BrokerAdapter]] = {}

    def register(self, name: str, adapter: Type[BrokerAdapter]) -> None:
        self._adapters[name.lower()] = adapter

    def get(self, name: str) -> Type[BrokerAdapter]:
        key = name.lower()
        if key not in self._adapters:
            raise KeyError(f"Unsupported broker: {name}")
        return self._adapters[key]

    def names(self) -> list[str]:
        return sorted(self._adapters)


registry = BrokerRegistry()


def _register_builtin_adapters() -> None:
    from app.brokers.adapters import DhanBrokerAdapter

    registry.register("dhan", DhanBrokerAdapter)


_register_builtin_adapters()
