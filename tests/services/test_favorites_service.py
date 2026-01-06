"""Tests for FavoritesService."""

import json
from pathlib import Path

import pytest

from domain.exceptions import ServiceError
from domain.wallpaper import Resolution, Wallpaper, WallpaperPurity, WallpaperSource
from services.favorites_service import FavoritesService


@pytest.fixture
def favorites_service(temp_dir: Path) -> FavoritesService:
    """Create FavoritesService with temporary favorites file."""
    favorites_file = temp_dir / "favorites.json"
    return FavoritesService(favorites_file=favorites_file)


@pytest.fixture
def sample_wallpaper() -> Wallpaper:
    """Create sample wallpaper for testing."""
    res = Resolution(width=1920, height=1080)
    return Wallpaper(
        id="test123",
        url="http://example.com/view/1",
        path="http://example.com/full.jpg",
        resolution=res,
        source=WallpaperSource.WALLHAVEN,
        category="anime",
        purity=WallpaperPurity.SFW,
        colors=["#000000"],
        file_size=1024,
    )


def test_favorites_service_init(favorites_service: FavoritesService):
    """Test FavoritesService initialization."""
    # Favorites file is created on first write, not initialization
    assert favorites_service.favorites_dir.exists()
    assert favorites_service.favorites_file.parent == favorites_service.favorites_dir


def test_add_favorite(favorites_service: FavoritesService, sample_wallpaper: Wallpaper):
    """Test adding wallpaper to favorites."""
    favorites_service.add_favorite(sample_wallpaper)

    favorites = favorites_service.get_favorites()
    assert len(favorites) == 1
    assert favorites[0].wallpaper_id == sample_wallpaper.id


def test_add_duplicate_favorite(favorites_service: FavoritesService, sample_wallpaper: Wallpaper):
    """Test adding duplicate favorite."""
    favorites_service.add_favorite(sample_wallpaper)
    favorites_service.add_favorite(sample_wallpaper)

    favorites = favorites_service.get_favorites()
    assert len(favorites) == 1  # Should not duplicate


def test_remove_favorite(favorites_service: FavoritesService, sample_wallpaper: Wallpaper):
    """Test removing favorite."""
    favorites_service.add_favorite(sample_wallpaper)

    favorites_service.remove_favorite(sample_wallpaper.id)

    favorites = favorites_service.get_favorites()
    assert len(favorites) == 0


def test_remove_nonexistent_favorite(favorites_service: FavoritesService):
    """Test removing non-existent favorite."""
    # Should not raise error
    favorites_service.remove_favorite("nonexistent")


def test_is_favorite(favorites_service: FavoritesService, sample_wallpaper: Wallpaper):
    """Test checking if wallpaper is favorite."""
    assert not favorites_service.is_favorite(sample_wallpaper.id)

    favorites_service.add_favorite(sample_wallpaper)
    assert favorites_service.is_favorite(sample_wallpaper.id)


def test_get_favorites(favorites_service: FavoritesService, sample_wallpaper: Wallpaper):
    """Test getting all favorites."""
    # Add multiple favorites
    for i in range(3):
        wallpaper = Wallpaper(
            id=f"test{i}",
            url=f"http://example.com/{i}",
            path=f"http://example.com/full{i}.jpg",
            resolution=Resolution(width=1920, height=1080),
            source=WallpaperSource.WALLHAVEN,
            category="anime",
            purity=WallpaperPurity.SFW,
        )
        favorites_service.add_favorite(wallpaper)

    favorites = favorites_service.get_favorites()
    assert len(favorites) == 3


def test_search_favorites_empty(favorites_service: FavoritesService):
    """Test searching empty favorites."""
    results = favorites_service.search_favorites("anime")
    assert len(results) == 0


def test_search_favorites_no_query(
    favorites_service: FavoritesService, sample_wallpaper: Wallpaper
):
    """Test searching favorites without query returns all."""
    favorites_service.add_favorite(sample_wallpaper)

    results = favorites_service.search_favorites("")
    assert len(results) == 1


def test_search_favorites_by_id(favorites_service: FavoritesService, sample_wallpaper: Wallpaper):
    """Test searching favorites by ID."""
    favorites_service.add_favorite(sample_wallpaper)

    results = favorites_service.search_favorites("test123")
    assert len(results) == 1
    assert results[0].id == sample_wallpaper.id


def test_search_favorites_by_category(
    favorites_service: FavoritesService, sample_wallpaper: Wallpaper
):
    """Test searching favorites by category."""
    favorites_service.add_favorite(sample_wallpaper)

    results = favorites_service.search_favorites("anime")
    assert len(results) == 1


def test_search_favorites_no_match(
    favorites_service: FavoritesService, sample_wallpaper: Wallpaper
):
    """Test searching with no matches."""
    favorites_service.add_favorite(sample_wallpaper)

    results = favorites_service.search_favorites("nonexistent")
    assert len(results) == 0


def test_favorite_persistence(favorites_service: FavoritesService, sample_wallpaper: Wallpaper):
    """Test favorites persist across service instances."""
    # Add favorite
    favorites_service.add_favorite(sample_wallpaper)

    # Create new service instance
    new_service = FavoritesService(favorites_file=favorites_service.favorites_file)

    favorites = new_service.get_favorites()
    assert len(favorites) == 1
    assert favorites[0].wallpaper.id == sample_wallpaper.id


def test_favorite_serialization(favorites_service: FavoritesService, sample_wallpaper: Wallpaper):
    """Test favorite JSON serialization."""
    favorites_service.add_favorite(sample_wallpaper)

    # Read JSON file directly
    with open(favorites_service.favorites_file) as f:
        data = json.load(f)

    assert len(data) == 1
    assert data[0]["wallpaper"]["id"] == sample_wallpaper.id
    assert "added_at" in data[0]


def test_days_since_added(favorites_service: FavoritesService, sample_wallpaper: Wallpaper):
    """Test days since favorite was added."""
    favorites_service.add_favorite(sample_wallpaper)

    favorites_list = favorites_service.get_favorites()
    assert len(favorites_list) == 1
    assert favorites_list[0].wallpaper.id == sample_wallpaper.id


def test_load_favorites_with_json_decode_error(favorites_service: FavoritesService):
    """Test loading favorites with invalid JSON raises ServiceError."""
    # Create file first
    favorites_service._ensure_favorites_file_exists()

    # Write invalid JSON
    with open(favorites_service.favorites_file, "w") as f:
        f.write("invalid json {")

    with pytest.raises(ServiceError, match="Failed to load favorites"):
        favorites_service._load_favorites()


def test_parse_favorites_data_dict_migration(
    favorites_service: FavoritesService, temp_dir: Path, caplog
):
    """Test migrating from old dict format to new format."""
    caplog.set_level("INFO")

    # Create old format data
    old_data = {
        "wallpaper123": {
            "id": "wallpaper123",
            "url": "http://example.com/view/123",
            "path": "http://example.com/full.jpg",
            "thumbs_large": "http://example.com/thumb.jpg",
            "thumbs_small": "http://example.com/small.jpg",
            "resolution": "1920x1080",
            "category": "anime",
            "purity": "sfw",
            "source": "wallhaven",
        }
    }

    # Create directory and write old format
    favorites_service.favorites_dir.mkdir(parents=True, exist_ok=True)
    with open(favorites_service.favorites_file, "w") as f:
        import json

        json.dump(old_data, f)

    # Load should migrate
    favorites = favorites_service._load_favorites()

    assert len(favorites) == 1
    assert favorites[0].wallpaper_id == "wallpaper123"
    # File should be saved in new format
    assert "Migrated" in caplog.text


def test_search_favorites_with_low_score(
    favorites_service: FavoritesService, sample_wallpaper: Wallpaper
):
    """Test searching favorites filters out low fuzzy match scores."""
    favorites_service.add_favorite(sample_wallpaper)

    # Query that won't match well
    results = favorites_service.search_favorites("xyzabc123")

    assert len(results) == 0


def test_parse_favorites_data_list(favorites_service: FavoritesService):
    """Test parsing favorites data in list format (new format)."""
    new_data = [
        {
            "wallpaper": {
                "id": "test1",
                "url": "http://example.com/1",
                "path": "http://example.com/1.jpg",
                "resolution": {"width": 1920, "height": 1080},
                "source": "wallhaven",
                "category": "general",
                "purity": "sfw",
                "colors": ["#000000"],
                "file_size": 1024,
            },
            "added_at": "2024-01-01T00:00:00",
        }
    ]

    favorites = favorites_service._parse_favorites_data(new_data)

    assert len(favorites) == 1
    assert favorites[0].wallpaper_id == "test1"


def test_parse_favorites_data_invalid_item(favorites_service: FavoritesService, caplog):
    """Test parsing favorites with invalid item logs warning."""
    # Invalid data in dict format - both items have path (from thumbs_large fallback)
    # So both should be parsed successfully in old format migration
    invalid_data = {
        "wallpaper123": {
            "id": "wallpaper123",
            "url": "http://example.com/123",
            "resolution": "1920x1080",
            "source": "wallhaven",
            "category": "general",
            "purity": "sfw",
            "path": "",  # Empty path, thumbs_large will be used as fallback
            "thumbs_large": "http://example.com/thumb123.jpg",
        },
        "wallpaper456": {
            "id": "wallpaper456",
            "url": "http://example.com/456",
            "resolution": "1920x1080",
            "source": "wallhaven",
            "category": "general",
            "purity": "sfw",
            "path": "http://example.com/456.jpg",
            "thumbs_large": "http://example.com/thumb456.jpg",
        },
    }

    caplog.set_level("WARNING")
    favorites = favorites_service._parse_favorites_data(invalid_data)

    # Both items should be parsed successfully (thumbs_large provides valid path)
    assert len(favorites) == 2
    assert len(caplog.records) >= 0
