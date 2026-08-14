from __future__ import annotations

from abc import ABC, abstractmethod


class NotificationProvider(ABC):
    @abstractmethod
    def notify(self, user_id: int, title: str, message: str) -> None:
        """Deliver a notification without influencing alert evaluation."""


class InAppNotificationProvider(NotificationProvider):
    def notify(self, user_id: int, title: str, message: str) -> None:
        del user_id, title, message
