"""Notification Service for system notifications."""

import asyncio
import subprocess

from services.base import BaseService


class NotificationService(BaseService):
    """Service for sending system notifications."""

    def __init__(self, enabled: bool = True) -> None:
        super().__init__()
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def notify(
        self, title: str, message: str, icon: str = "dialog-information"
    ) -> bool:
        if not self._enabled:
            return False

        try:
            subprocess.run(
                ["notify-send", "-i", icon, title, message],
                check=False,
                capture_output=True,
            )
            self.log_debug(f"Notification sent: {title} - {message}")
            return True
        except FileNotFoundError:
            self.log_warning("notify-send not found, notifications disabled")
            return False
        except Exception as e:
            self.log_error(f"Failed to send notification: {e}")
            return False

    async def notify_async(
        self, title: str, message: str, icon: str = "dialog-information"
    ) -> bool:
        return await asyncio.to_thread(self.notify, title, message, icon)

    async def notify_success_async(self, message: str) -> bool:
        return await self.notify_async("Wallpicker", message, "emblem-ok-symbolic")

    async def notify_error_async(self, message: str) -> bool:
        return await self.notify_async("Wallpicker", message, "dialog-error-symbolic")

    async def notify_info_async(self, message: str) -> bool:
        return await self.notify_async(
            "Wallpicker", message, "dialog-information-symbolic"
        )

    def notify_success(self, message: str) -> bool:
        return self.notify("Wallpicker", message, "emblem-ok-symbolic")

    def notify_error(self, message: str) -> bool:
        return self.notify("Wallpicker", message, "dialog-error-symbolic")

    def notify_info(self, message: str) -> bool:
        return self.notify("Wallpicker", message, "dialog-information-symbolic")
