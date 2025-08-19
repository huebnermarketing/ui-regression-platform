#!/usr/bin/env python3
"""
Test script to verify the slugify_path fix for long filenames
"""

import sys
import os
import hashlib

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from screenshot.screenshot_service import ScreenshotService

def test_slugify_fix():
    """Test the slugify_path fix with various path lengths"""
    
    screenshot_service = ScreenshotService()
    
    print("Testing slugify_path fix for long filenames")
    print("=" * 60)
    
    # Test cases with various path lengths
    test_cases = [
        # Short path
        "/",
        "/about",
        "/products/item-123",
        
        # Medium path
        "/product-category/search-by-device/elo/mm-1000-elo/mm-1000-series-modular-mounts-mm-1000-elo",
        
        # Long path (the problematic one from the error)
        "/product-category/search-by-device/elo/mm-1000-elo/mm-1000-series-modular-mounts-mm-1000-elo/mm-1000-sp-line-mm-1000-series-modular-mounts-mm-1000-elo/mm-1000-sp-accessories-mm-1000-sp-line-mm-1000-series-modular-mounts-mm-1000-elo",
        
        # Very long path
        "/product-category/search-by-device/elo/mm-1000-elo/mm-1000-series-modular-mounts-mm-1000-elo/mm-1000-sp-line-mm-1000-series-modular-mounts-mm-1000-elo/mm-1000-sp-accessories-mm-1000-sp-line-mm-1000-series-modular-mounts-mm-1000-elo/mm-1000-sp-accessories-mm-1000-sp-line-mm-1000-series-modular-mounts-mm-1000-elo/mm-1000-sp-accessories-mm-1000-sp-line-mm-1000-series-modular-mounts-mm-1000-elo"
    ]
    
    print("Testing path slugification:")
    for i, path in enumerate(test_cases, 1):
        slug = screenshot_service.slugify_path(path)
        print(f"  {i}. '{path}'")
        print(f"     -> '{slug}' (length: {len(slug)})")
        
        # Verify that the slug is not too long
        if len(slug) > 250:
            print(f"     ERROR: Slug is too long ({len(slug)} > 250)")
        else:
            print(f"     OK: Slug length is within limit")
        
        # For long paths, verify uniqueness mechanism
        if len(path) > 250:
            expected_hash = hashlib.md5(path.encode()).hexdigest()[:8]
            if expected_hash in slug:
                print(f"     OK: Hash-based uniqueness maintained")
            else:
                print(f"     ERROR: Hash-based uniqueness not maintained")
        
        print()
    
    print("Slugify path fix verification completed!")

if __name__ == "__main__":
    test_slugify_fix()