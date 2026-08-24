"""Favorite domain model."""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .wallpaper import Wallpaper as _WallpaperImport
else:
    from .wallpaper import Wallpaper


@dataclass
class Favorite:
    """Favorite wallpaper domain entity."""

    wallpaper: _WallpaperImport if TYPE_CHECKING else Wallpaper
    added_at: datetime

    @property
    def days_since_added(self) -> int:
        """Calculate days since wallpaper was added to favorites."""
        return (datetime.now() - self.added_at).days

    @property
    def wallpaper_id(self) -> str:
        """Get wallpaper ID for serialization."""
        return self.wallpaper.id

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "wallpaper": self.wallpaper.to_dict(),
            "added_at": self.added_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict, wallpaper_class: type | None = None) -> "Favorite":
        """Create from dict for JSON deserialization.

        Tolerant of malformed entries: missing/invalid fields fall back to defaults
        instead of raising, so a single bad entry cannot kill loading of all favorites.
        """
        from .wallpaper import Wallpaper

        wallpaper_data = data.get("wallpaper")
        if not isinstance(wallpaper_data, dict):
            raise ValueError("favorite entry is missing 'wallpaper' object")
        try:
            wallpaper = Wallpaper.from_dict(wallpaper_data)
        except Exception:
            # Fall back to an empty placeholder; callers may skip such entries.
            from .wallpaper import Resolution, WallpaperPurity, WallpaperSource

            wallpaper = Wallpaper(
                id=str(data.get("id", "")),
                url="",
                path="",
                resolution=Resolution(0, 0),
                source=WallpaperSource.LOCAL,
                category="",
                purity=WallpaperPurity.SFW,
            )

        added_at_raw = data.get("added_at")
        added_at = datetime.now()
        if added_at_raw:
            try:
                parsed = datetime.fromisoformat(str(added_at_raw))
            except (TypeError, ValueError):
                pass
            else:
                added_at = parsed

        return cls(wallpaper=wallpaper, added_at=added_at)
