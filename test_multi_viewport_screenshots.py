"""
Test script for multi-viewport screenshot functionality
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import the models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from screenshot.screenshot_service import ScreenshotService
from models.project import ProjectPage
from models import db
from app import app

async def test_multi_viewport_capture():
    """Test multi-viewport screenshot capture"""
    
    print("Testing Multi-Viewport Screenshot Capture")
    print("=" * 50)
    
    # Initialize screenshot service
    screenshot_service = ScreenshotService()
    
    # Test viewport configurations
    print("Viewport configurations:")
    for viewport, config in screenshot_service.viewports.items():
        print(f"  {viewport}: {config['width']}x{config['height']}")
    
    print("\nTesting screenshot path generation...")
    
    # Test path generation for different viewports
    project_id = 999  # Test project ID
    page_path = "/test-page"
    
    for viewport in ['desktop', 'tablet', 'mobile']:
        staging_path, production_path = screenshot_service.get_screenshot_paths(
            project_id, page_path, viewport
        )
        print(f"  {viewport}:")
        print(f"    Staging: {staging_path}")
        print(f"    Production: {production_path}")
    
    # Test legacy path generation
    legacy_staging, legacy_production = screenshot_service.get_screenshot_paths(
        project_id, page_path
    )
    print(f"  Legacy:")
    print(f"    Staging: {legacy_staging}")
    print(f"    Production: {legacy_production}")
    
    print("\nTesting URL screenshot capture...")
    
    # Test capturing a real URL (using a public test site)
    test_url = "https://httpbin.org/html"
    test_output_dir = Path("test_screenshots")
    test_output_dir.mkdir(exist_ok=True)
    
    for viewport in ['desktop', 'tablet', 'mobile']:
        output_path = test_output_dir / f"test_{viewport}.png"
        print(f"  Capturing {viewport} screenshot...")
        
        try:
            success = await screenshot_service.capture_screenshot(
                test_url, output_path, viewport, timeout=15000
            )
            if success:
                print(f"    [SUCCESS] {output_path}")
                # Check file size
                if output_path.exists():
                    size_kb = output_path.stat().st_size / 1024
                    print(f"    File size: {size_kb:.1f} KB")
            else:
                print(f"    [FAILED] {output_path}")
        except Exception as e:
            print(f"    [ERROR] {str(e)}")
    
    print("\nTesting dynamic content handling...")
    
    # Test with a page that has dynamic content
    dynamic_test_url = "https://httpbin.org/delay/2"  # Simulates slow loading
    dynamic_output = test_output_dir / "test_dynamic.png"
    
    try:
        print("  Capturing with dynamic content handling...")
        success = await screenshot_service.capture_screenshot(
            dynamic_test_url, dynamic_output, 'desktop', 
            timeout=20000, wait_for_dynamic=True
        )
        if success:
            print(f"    [SUCCESS] {dynamic_output}")
        else:
            print(f"    [FAILED] {dynamic_output}")
    except Exception as e:
        print(f"    [ERROR] {str(e)}")
    
    print("\nTest completed!")
    print(f"Test screenshots saved in: {test_output_dir.absolute()}")

def test_database_schema():
    """Test database schema for multi-viewport support"""
    
    print("\nTesting Database Schema")
    print("=" * 30)
    
    with app.app_context():
        # Check if new columns exist
        from sqlalchemy import inspect
        
        inspector = inspect(db.engine)
        columns = inspector.get_columns('project_pages')
        column_names = [col['name'] for col in columns]
        
        # Expected new columns
        expected_columns = [
            'staging_screenshot_path_desktop',
            'staging_screenshot_path_tablet', 
            'staging_screenshot_path_mobile',
            'production_screenshot_path_desktop',
            'production_screenshot_path_tablet',
            'production_screenshot_path_mobile',
            'diff_image_path_desktop',
            'diff_image_path_tablet',
            'diff_image_path_mobile',
            'diff_raw_image_path_desktop',
            'diff_raw_image_path_tablet',
            'diff_raw_image_path_mobile',
            'diff_mismatch_pct_desktop',
            'diff_mismatch_pct_tablet',
            'diff_mismatch_pct_mobile',
            'diff_pixels_changed_desktop',
            'diff_pixels_changed_tablet',
            'diff_pixels_changed_mobile',
            'diff_bounding_boxes_desktop',
            'diff_bounding_boxes_tablet',
            'diff_bounding_boxes_mobile'
        ]
        
        print("Checking for new multi-viewport columns:")
        missing_columns = []
        for col in expected_columns:
            if col in column_names:
                print(f"  [OK] {col}")
            else:
                print(f"  [MISSING] {col}")
                missing_columns.append(col)
        
        if missing_columns:
            print(f"\n[WARNING] {len(missing_columns)} columns are missing!")
            print("Run the migration: python migrations/add_multi_viewport_fields.py")
        else:
            print("\n[SUCCESS] All multi-viewport columns are present!")

async def main():
    """Main test function"""
    
    print("Multi-Viewport Screenshot Testing")
    print("=" * 50)
    
    # Test database schema
    test_database_schema()
    
    # Test screenshot functionality
    await test_multi_viewport_capture()
    
    print("\n" + "=" * 50)
    print("Testing completed!")

if __name__ == "__main__":
    asyncio.run(main())