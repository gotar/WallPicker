"""Wallpaper domain models and value objects."""

from dataclasses import dataclass, field
from enum import Enum


class WallpaperSource(Enum):
    """Source of wallpaper data."""

    WALLHAVEN = "wallhaven"
    LOCAL = "local"
    FAVORITE = "favorite"


class WallpaperPurity(Enum):
    """Content purity rating."""

    SFW = "sfw"
    SKETCHY = "sketchy"
    NSFW = "nsfw"


@dataclass(frozen=True)
class Resolution:
    """Value object representing image resolution."""

    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width < 0 or self.height < 0:
            raise ValueError(
                f"Resolution dimensions must be non-negative, got {self.width}x{self.height}"
            )

    @property
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio."""
        # Guard against zero/negative height (e.g. unknown resolution 0x0)
        return self.width / self.height if self.height > 0 else 0.0

    def __str__(self) -> str:
        """String representation."""
        return f"{self.width}x{self.height}"

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {"width": self.width, "height": self.height}


@dataclass
class Wallpaper:
    """Domain entity representing a wallpaper."""

    id: str
    url: str
    path: str  # Local file path or download URL
    resolution: Resolution
    source: WallpaperSource
    category: str
    purity: WallpaperPurity
    colors: list[str] = field(default_factory=list)
    file_size: int = 0
    thumbs_large: str = ""
    thumbs_small: str = ""
    tags: list[str] = field(default_factory=list)

    # Domain behavior
    @property
    def is_landscape(self) -> bool:
        """Check if wallpaper is landscape orientation."""
        return self.resolution.aspect_ratio >= 1

    @property
    def is_portrait(self) -> bool:
        """Check if wallpaper is portrait orientation."""
        return self.resolution.aspect_ratio < 1

    @property
    def size_mb(self) -> float:
        """File size in megabytes."""
        return self.file_size / (1024 * 1024)

    def matches_query(self, query: str) -> bool:
        """Check if wallpaper matches search query."""
        query_lower = query.lower()
        return (
            query_lower in self.id.lower()
            or query_lower in self.category.lower()
            or query_lower in self.url.lower()
            or any(query_lower in tag.lower() for tag in self.tags)
        )

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "id": self.id,
            "url": self.url,
            "path": self.path,
            "resolution": self.resolution.to_dict(),
            "source": self.source.value,
            "category": self.category,
            "purity": self.purity.value,
            "colors": self.colors,
            "file_size": self.file_size,
            "thumbs_large": self.thumbs_large,
            "thumbs_small": self.thumbs_small,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Wallpaper":
        """Create from dict for JSON deserialization."""
        resolution_data = data.get("resolution")
        if not isinstance(resolution_data, dict):
            resolution_data = {}

        def _non_negative(key: str) -> int:
            try:
                return max(0, int(resolution_data.get(key, 0)))
            except (TypeError, ValueError):
                return 0

        resolution = Resolution(
            width=_non_negative("width"),
            height=_non_negative("height"),
        )

        def _enum_or_default(value, enum_cls, default):
            """Convert value to enum member, falling back to default on failure."""
            try:
                return enum_cls(value)
            except ValueError:
                return enum_cls(default)

        return cls(
            id=data.get("id", ""),
            url=data.get("url", ""),
            path=data.get("path", ""),
            resolution=resolution,
            source=_enum_or_default(data.get("source", "local"), WallpaperSource, "local"),
            category=data.get("category", ""),
            purity=_enum_or_default(data.get("purity", "sfw"), WallpaperPurity, "sfw"),
            colors=data.get("colors", []),
            file_size=data.get("file_size", 0),
            thumbs_large=data.get("thumbs_large", ""),
            thumbs_small=data.get("thumbs_small", ""),
            tags=data.get("tags", []),
        )
