#!/usr/bin/env python3
"""Quick verification script for BannerService implementation."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("BannerService Implementation Verification")
print("=" * 70)

# Test 1: Import BannerService
print("\n[Test 1] Import BannerService...")
try:
    from services.banner_service import BannerService, BannerPriority, BannerType

    print("✅ Import successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Check BannerPriority enum
print("\n[Test 2] Check BannerPriority enum...")
try:
    assert hasattr(BannerPriority, "LOW")
    assert hasattr(BannerPriority, "MEDIUM")
    assert hasattr(BannerPriority, "HIGH")
    assert BannerPriority.LOW < BannerPriority.MEDIUM < BannerPriority.HIGH
    print("✅ BannerPriority enum correct")
except Exception as e:
    print(f"❌ BannerPriority enum check failed: {e}")
    sys.exit(1)

# Test 3: Check BannerType class
print("\n[Test 3] Check BannerType class...")
try:
    assert hasattr(BannerType, "SELECTION")
    assert hasattr(BannerType, "STORAGE")
    assert hasattr(BannerType, "API")
    assert hasattr(BannerType, "INFO")
    assert BannerType.SELECTION == "selection"
    assert BannerType.STORAGE == "storage"
    assert BannerType.API == "api"
    assert BannerType.INFO == "info"
    print("✅ BannerType class correct")
except Exception as e:
    print(f"❌ BannerType class check failed: {e}")
    sys.exit(1)

# Test 4: Check BannerService class structure
print("\n[Test 4] Check BannerService class structure...")
try:
    # Check GObject inheritance
    from gi.repository import GObject

    assert issubclass(BannerService, GObject.Object)

    # Check GObject properties
    assert hasattr(BannerService, "current_banner_type")
    assert hasattr(BannerService, "is_visible")

    # Check public methods
    required_methods = [
        "show_selection_banner",
        "show_storage_warning",
        "show_api_warning",
        "show_info_banner",
        "clear_banner",
        "hide_selection_banner",
        "get_banner_widget",
        "cleanup",
    ]

    for method in required_methods:
        assert hasattr(BannerService, method), f"Missing method: {method}"

    print("✅ BannerService class structure correct")
except Exception as e:
    print(f"❌ BannerService class structure check failed: {e}")
    sys.exit(1)

# Test 5: Check method signatures
print("\n[Test 5] Check method signatures...")
try:
    import inspect

    # Check show_selection_banner
    sig = inspect.signature(BannerService.show_selection_banner)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "count" in params
    assert "on_set_all" in params

    # Check show_storage_warning
    sig = inspect.signature(BannerService.show_storage_warning)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "used_mb" in params
    assert "limit_mb" in params
    assert "on_clear_cache" in params

    # Check show_api_warning
    sig = inspect.signature(BannerService.show_api_warning)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "message" in params
    assert "button_text" in params
    assert "on_button_click" in params

    # Check show_info_banner
    sig = inspect.signature(BannerService.show_info_banner)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "message" in params
    assert "button_text" in params
    assert "on_button_click" in params

    print("✅ Method signatures correct")
except Exception as e:
    print(f"❌ Method signature check failed: {e}")
    sys.exit(1)

# Test 6: Check CSS styles
print("\n[Test 6] Check CSS styles...")
try:
    css_path = Path(__file__).parent.parent / "data" / "style.css"
    with open(css_path) as f:
        css_content = f.read()

    required_classes = [
        ".banner",
        ".banner.warning-banner",
        ".banner.info-banner",
        ".banner.selection-banner",
        ".banner-container",
    ]

    for css_class in required_classes:
        assert css_class in css_content, f"Missing CSS class: {css_class}"

    print("✅ CSS styles present")
except Exception as e:
    print(f"❌ CSS styles check failed: {e}")
    sys.exit(1)

# Test 7: Check test file
print("\n[Test 7] Check test file...")
try:
    test_path = Path(__file__).parent.parent / "tests" / "services" / "test_banner_service.py"
    assert test_path.exists(), "Test file not found"
    print("✅ Test file exists")
except Exception as e:
    print(f"❌ Test file check failed: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ All verification checks passed!")
print("=" * 70)
print("\nBannerService is ready for integration.")
print("\nNext steps:")
print("1. Integrate BannerService in main_window.py")
print("2. Add banner widget to ToolbarView layout")
print("3. Connect banner methods to view model events")
print("4. Run full test suite: python -m pytest tests/services/test_banner_service.py")
