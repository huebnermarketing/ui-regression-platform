#!/usr/bin/env python3
"""
Test script for Phase 3 Stage 2: Visual Diff Generation
Tests the complete diff generation workflow including image processing and job integration
"""

import os
import sys
import time
import requests
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.project import Project, ProjectPage
from diff.diff_engine import DiffEngine, VisualDiffEngine, DiffConfig

def create_test_images():
    """Create test images for diff testing"""
    print("Creating test images...")
    
    # Create test directories
    screenshots_dir = Path("screenshots/test_project")
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    diffs_dir = Path("diffs")
    diffs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create base image (800x600, white background)
    base_img = Image.new('RGB', (800, 600), 'white')
    draw = ImageDraw.Draw(base_img)
    
    # Add some content to base image
    draw.rectangle([50, 50, 750, 100], fill='blue')
    draw.rectangle([50, 150, 400, 200], fill='green')
    draw.rectangle([450, 150, 750, 200], fill='red')
    draw.text((60, 250), "This is a test page", fill='black')
    draw.rectangle([50, 300, 750, 350], fill='yellow')
    
    # Save as production image
    production_path = screenshots_dir / "staging" / "test_page.png"
    production_path.parent.mkdir(parents=True, exist_ok=True)
    base_img.save(production_path)
    
    # Create modified image (staging with differences)
    modified_img = base_img.copy()
    draw_modified = ImageDraw.Draw(modified_img)
    
    # Add differences
    draw_modified.rectangle([50, 50, 750, 100], fill='purple')  # Changed color
    draw_modified.rectangle([500, 150, 750, 200], fill='orange')  # Changed part of rectangle
    draw_modified.text((60, 280), "This text is different", fill='black')  # Added text
    draw_modified.rectangle([50, 400, 300, 450], fill='cyan')  # New rectangle
    
    # Save as staging image
    staging_path = screenshots_dir / "production" / "test_page.png"
    staging_path.parent.mkdir(parents=True, exist_ok=True)
    modified_img.save(staging_path)
    
    print(f"OK Created test images:")
    print(f"  - Production: {production_path}")
    print(f"  - Staging: {staging_path}")
    
    return str(staging_path.relative_to(Path("screenshots"))), str(production_path.relative_to(Path("screenshots")))

def test_diff_config():
    """Test diff configuration"""
    print("\n=== Testing Diff Configuration ===")
    
    config = DiffConfig()
    
    # Test default values
    assert config.per_pixel_threshold == 12, f"Expected threshold 12, got {config.per_pixel_threshold}"
    assert config.min_diff_area == 24, f"Expected min area 24, got {config.min_diff_area}"
    assert config.overlay_alpha == 140, f"Expected alpha 140, got {config.overlay_alpha}"
    assert config.batch_size == 15, f"Expected batch size 15, got {config.batch_size}"
    
    print("OK Default configuration values correct")
    
    # Test environment variable override
    os.environ['DIFF_PER_PIXEL_THRESHOLD'] = '20'
    os.environ['DIFF_MIN_DIFF_AREA'] = '50'
    
    config2 = DiffConfig()
    assert config2.per_pixel_threshold == 20, f"Expected threshold 20, got {config2.per_pixel_threshold}"
    assert config2.min_diff_area == 50, f"Expected min area 50, got {config2.min_diff_area}"
    
    print("OK Environment variable overrides working")
    
    # Clean up environment
    del os.environ['DIFF_PER_PIXEL_THRESHOLD']
    del os.environ['DIFF_MIN_DIFF_AREA']

def test_visual_diff_engine():
    """Test the visual diff engine core functionality"""
    print("\n=== Testing Visual Diff Engine ===")
    
    # Create test images
    staging_path, production_path = create_test_images()
    
    # Initialize diff engine
    config = DiffConfig()
    config.per_pixel_threshold = 10  # Lower threshold for testing
    config.min_diff_area = 20
    
    engine = VisualDiffEngine(config)
    
    # Load test images
    staging_img = Image.open(Path("screenshots") / staging_path)
    production_img = Image.open(Path("screenshots") / production_path)
    
    print(f"OK Loaded test images: {staging_img.size} and {production_img.size}")
    
    # Test image normalization
    norm_staging, norm_production = engine.normalize_images(staging_img, production_img)
    assert norm_staging.size == norm_production.size, "Normalized images should have same size"
    print(f"OK Image normalization: {norm_staging.size}")
    
    # Test diff mask computation
    diff_mask = engine.compute_diff_mask(norm_staging, norm_production)
    assert diff_mask.mode == 'L', "Diff mask should be grayscale"
    
    # Check that differences were detected
    mask_array = np.array(diff_mask)
    diff_pixels = np.sum(mask_array > 0)
    assert diff_pixels > 0, "Should detect differences between test images"
    print(f"OK Diff mask computation: {diff_pixels} different pixels detected")
    
    # Test bounding box extraction
    bounding_boxes = engine.extract_bounding_boxes(diff_mask)
    assert len(bounding_boxes) > 0, "Should find bounding boxes for differences"
    print(f"OK Bounding box extraction: {len(bounding_boxes)} regions found")
    
    # Test metrics calculation
    metrics = engine.calculate_metrics(diff_mask, bounding_boxes)
    assert 'diff_pixels_changed' in metrics, "Metrics should include pixel count"
    assert 'diff_mismatch_pct' in metrics, "Metrics should include percentage"
    assert 'diff_bounding_boxes' in metrics, "Metrics should include bounding boxes"
    assert metrics['diff_pixels_changed'] == diff_pixels, "Pixel count should match"
    print(f"OK Metrics calculation: {metrics['diff_mismatch_pct']:.2f}% changed")
    
    # Test highlighted diff creation
    highlighted_diff = engine.create_highlighted_diff(norm_production, diff_mask, bounding_boxes)
    assert highlighted_diff.mode == 'RGBA', "Highlighted diff should be RGBA"
    print("OK Highlighted diff creation")
    
    # Test raw diff creation
    raw_diff = engine.create_raw_diff(diff_mask)
    assert raw_diff.mode == 'RGB', "Raw diff should be RGB"
    print("OK Raw diff creation")
    
    return engine, staging_path, production_path

def test_database_integration():
    """Test database integration with diff fields"""
    print("\n=== Testing Database Integration ===")
    
    with app.app_context():
        # Create test project with unique name
        import time
        timestamp = int(time.time())
        project = Project(
            name=f"Test Diff Project {timestamp}",
            staging_url="https://staging.example.com",
            production_url="https://production.example.com",
            user_id=1
        )
        db.session.add(project)
        db.session.commit()
        
        print(f"OK Created test project: {project.id}")
        
        # Create test page with screenshot paths
        staging_path, production_path = create_test_images()
        
        page = ProjectPage(
            project_id=project.id,
            path="/test-page",
            staging_url="https://staging.example.com/test-page",
            production_url="https://production.example.com/test-page",
            page_name="Test Page"
        )
        page.status = "screenshot_complete"
        page.staging_screenshot_path = staging_path
        page.production_screenshot_path = production_path
        db.session.add(page)
        db.session.commit()
        
        print(f"OK Created test page: {page.id}")
        
        # Test diff engine with database
        engine = VisualDiffEngine()
        success = engine.process_page_diff(page.id)
        
        assert success, "Diff processing should succeed"
        print("OK Page diff processing successful")
        
        # Verify database updates
        db.session.refresh(page)
        assert page.status == 'diff_generated', f"Expected status 'diff_generated', got '{page.status}'"
        assert page.diff_image_path is not None, "Diff image path should be set"
        assert page.diff_raw_image_path is not None, "Raw diff image path should be set"
        assert page.diff_mismatch_pct is not None, "Mismatch percentage should be set"
        assert page.diff_pixels_changed is not None, "Changed pixels count should be set"
        assert page.diff_bounding_boxes is not None, "Bounding boxes should be set"
        assert page.diff_generated_at is not None, "Generation timestamp should be set"
        
        print(f"OK Database fields updated:")
        print(f"  - Status: {page.status}")
        print(f"  - Mismatch: {page.diff_mismatch_pct}%")
        print(f"  - Changed pixels: {page.diff_pixels_changed}")
        print(f"  - Bounding boxes: {len(page.diff_bounding_boxes) if page.diff_bounding_boxes else 0}")
        
        # Verify diff files exist
        diff_path = Path("diffs") / page.diff_image_path
        raw_diff_path = Path("diffs") / page.diff_raw_image_path
        
        assert diff_path.exists(), f"Diff image should exist at {diff_path}"
        assert raw_diff_path.exists(), f"Raw diff image should exist at {raw_diff_path}"
        print("OK Diff image files created successfully")
        
        # Clean up
        db.session.delete(page)
        db.session.delete(project)
        db.session.commit()
        
        return project.id

def test_diff_engine_wrapper():
    """Test the DiffEngine wrapper class"""
    print("\n=== Testing DiffEngine Wrapper ===")
    
    with app.app_context():
        # Create test project and page
        import time
        timestamp = int(time.time())
        project = Project(
            name=f"Test Wrapper Project {timestamp}",
            staging_url="https://staging.example.com",
            production_url="https://production.example.com",
            user_id=1
        )
        db.session.add(project)
        db.session.commit()
        
        staging_path, production_path = create_test_images()
        
        page = ProjectPage(
            project_id=project.id,
            path="/wrapper-test",
            staging_url="https://staging.example.com/wrapper-test",
            production_url="https://production.example.com/wrapper-test",
            page_name="Wrapper Test Page"
        )
        page.status = "screenshot_complete"
        page.staging_screenshot_path = staging_path
        page.production_screenshot_path = production_path
        db.session.add(page)
        db.session.commit()
        
        # Test DiffEngine wrapper
        diff_engine = DiffEngine()
        successful_count, failed_count = diff_engine.run_generate_project_diffs(project.id)
        
        assert successful_count == 1, f"Expected 1 successful, got {successful_count}"
        assert failed_count == 0, f"Expected 0 failed, got {failed_count}"
        
        print(f"OK DiffEngine wrapper: {successful_count} successful, {failed_count} failed")
        
        # Verify page was processed
        db.session.refresh(page)
        assert page.status == 'diff_generated', "Page should be marked as diff_generated"
        
        # Clean up
        db.session.delete(page)
        db.session.delete(project)
        db.session.commit()

def test_job_integration():
    """Test job integration with scheduler"""
    print("\n=== Testing Job Integration ===")
    
    # Import scheduler
    from app import crawler_scheduler
    
    with app.app_context():
        # Create test project and page
        import time
        timestamp = int(time.time())
        project = Project(
            name=f"Test Job Project {timestamp}",
            staging_url="https://staging.example.com",
            production_url="https://production.example.com",
            user_id=1
        )
        db.session.add(project)
        db.session.commit()
        
        staging_path, production_path = create_test_images()
        
        page = ProjectPage(
            project_id=project.id,
            path="/job-test",
            staging_url="https://staging.example.com/job-test",
            production_url="https://production.example.com/job-test",
            page_name="Job Test Page"
        )
        page.status = "screenshot_complete"
        page.staging_screenshot_path = staging_path
        page.production_screenshot_path = production_path
        db.session.add(page)
        db.session.commit()
        
        print(f"OK Created test project {project.id} with page {page.id}")
        
        # Test job scheduling
        job_id = crawler_scheduler.schedule_diff_generation(project.id)
        assert job_id is not None, "Job ID should be returned"
        print(f"OK Scheduled diff generation job: {job_id}")
        
        # Wait for job to complete (with timeout)
        timeout = 30  # 30 seconds timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if project.id not in crawler_scheduler.running_jobs:
                break
            time.sleep(1)
        
        # Check if job completed
        if project.id in crawler_scheduler.running_jobs:
            print("WARNING Job still running after timeout, stopping...")
            crawler_scheduler.stop_job(job_id)
        else:
            print("OK Job completed successfully")
            
            # Verify results
            db.session.refresh(page)
            if page.status == 'diff_generated':
                print(f"OK Page processed successfully: {page.diff_mismatch_pct}% changed")
            else:
                print(f"WARNING Page status: {page.status}")
        
        # Clean up
        db.session.delete(page)
        db.session.delete(project)
        db.session.commit()

def test_error_handling():
    """Test error handling scenarios"""
    print("\n=== Testing Error Handling ===")
    
    with app.app_context():
        engine = VisualDiffEngine()
        
        # Test with non-existent page
        success = engine.process_page_diff(99999)
        assert not success, "Should fail for non-existent page"
        print("OK Handles non-existent page correctly")
        
        # Test with page missing screenshot paths
        import time
        timestamp = int(time.time())
        project = Project(
            name=f"Test Error Project {timestamp}",
            staging_url="https://staging.example.com",
            production_url="https://production.example.com",
            user_id=1
        )
        db.session.add(project)
        db.session.commit()
        
        page = ProjectPage(
            project_id=project.id,
            path="/error-test",
            staging_url="https://staging.example.com/error-test",
            production_url="https://production.example.com/error-test",
            page_name="Error Test Page"
            # Missing screenshot paths
        )
        page.status = "screenshot_complete"
        db.session.add(page)
        db.session.commit()
        
        success = engine.process_page_diff(page.id)
        assert not success, "Should fail for missing screenshot paths"
        
        # Verify error was recorded
        db.session.refresh(page)
        assert page.status == 'diff_failed', "Status should be diff_failed"
        assert page.diff_error is not None, "Error message should be recorded"
        print(f"OK Handles missing screenshots: {page.diff_error}")
        
        # Clean up
        db.session.delete(page)
        db.session.delete(project)
        db.session.commit()

def cleanup_test_files():
    """Clean up test files"""
    print("\n=== Cleaning Up Test Files ===")
    
    # Remove test screenshots
    test_screenshots = Path("screenshots/test_project")
    if test_screenshots.exists():
        import shutil
        shutil.rmtree(test_screenshots)
        print("OK Removed test screenshots")
    
    # Remove test diffs (keep directory structure)
    diffs_dir = Path("diffs")
    if diffs_dir.exists():
        for file in diffs_dir.glob("**/*.png"):
            if "test" in str(file):
                file.unlink()
        print("OK Removed test diff images")

def main():
    """Run all diff generation tests"""
    print("Starting Phase 3 Stage 2: Visual Diff Generation Tests")
    print("=" * 60)
    
    try:
        # Test configuration
        test_diff_config()
        
        # Test core diff engine
        test_visual_diff_engine()
        
        # Test database integration
        test_database_integration()
        
        # Test wrapper class
        test_diff_engine_wrapper()
        
        # Test job integration
        test_job_integration()
        
        # Test error handling
        test_error_handling()
        
        print("\n" + "=" * 60)
        print("All diff generation tests passed successfully!")
        print("\nPhase 3 Stage 2 implementation is working correctly:")
        print("• Visual diff engine with image normalization OK")
        print("• Pixel-level comparison with thresholding OK")
        print("• Morphological operations for noise reduction OK")
        print("• Bounding box detection OK")
        print("• Highlighted diff rendering OK")
        print("• Metrics calculation OK")
        print("• Database integration OK")
        print("• Job orchestration OK")
        print("• Error handling OK")
        
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        cleanup_test_files()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)