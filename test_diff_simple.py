#!/usr/bin/env python3
"""
Simplified Visual Diff Generation Test
Tests the core diff engine functionality without database dependencies
"""

import os
import sys
import shutil
from PIL import Image, ImageDraw
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from diff.diff_engine import VisualDiffEngine
from diff import DiffConfig

def create_test_images():
    """Create test images for diff testing"""
    # Create screenshots directory
    os.makedirs('screenshots/test_simple', exist_ok=True)
    
    # Create production image (800x600, white background with blue rectangle)
    prod_img = Image.new('RGB', (800, 600), 'white')
    draw = ImageDraw.Draw(prod_img)
    draw.rectangle([100, 100, 300, 200], fill='blue')
    draw.text((400, 300), "Production Version", fill='black')
    prod_path = 'screenshots/test_simple/production.png'
    prod_img.save(prod_path)
    
    # Create staging image (800x600, white background with red rectangle and extra text)
    staging_img = Image.new('RGB', (800, 600), 'white')
    draw = ImageDraw.Draw(staging_img)
    draw.rectangle([120, 120, 320, 220], fill='red')  # Slightly different position
    draw.text((400, 300), "Staging Version", fill='black')
    draw.text((400, 350), "New Feature!", fill='green')  # Extra text
    staging_path = 'screenshots/test_simple/staging.png'
    staging_img.save(staging_path)
    
    return prod_path, staging_path

def test_diff_engine():
    """Test the visual diff engine"""
    print("=== Testing Visual Diff Engine ===")
    
    # Create test images
    print("Creating test images...")
    prod_path, staging_path = create_test_images()
    print(f"OK Created: {prod_path}")
    print(f"OK Created: {staging_path}")
    
    # Initialize diff engine
    config = DiffConfig()
    engine = VisualDiffEngine(config)
    
    # Load images
    print("\nLoading images...")
    prod_img = Image.open(prod_path)
    staging_img = Image.open(staging_path)
    print(f"OK Production image: {prod_img.size}")
    print(f"OK Staging image: {staging_img.size}")
    
    # Generate diff step by step
    print("\nGenerating visual diff...")
    
    # Normalize images
    norm_staging, norm_production = engine.normalize_images(staging_img, prod_img)
    print(f"OK Image normalization: {norm_staging.size}")
    
    # Compute difference mask
    diff_mask = engine.compute_diff_mask(norm_staging, norm_production)
    print(f"OK Diff mask computation completed")
    
    # Extract bounding boxes
    bounding_boxes = engine.extract_bounding_boxes(diff_mask)
    print(f"OK Bounding box extraction: {len(bounding_boxes)} regions found")
    
    # Calculate metrics
    metrics = engine.calculate_metrics(diff_mask, bounding_boxes)
    print(f"OK Metrics calculation: {metrics['diff_mismatch_pct']:.2f}% changed")
    
    # Create diff images
    highlighted_diff = engine.create_highlighted_diff(norm_production, diff_mask, bounding_boxes)
    raw_diff = engine.create_raw_diff(diff_mask)
    print(f"OK Highlighted diff creation")
    print(f"OK Raw diff creation")
    
    # Save diff images
    diff_dir = 'screenshots/test_simple/diffs'
    os.makedirs(diff_dir, exist_ok=True)
    
    highlighted_path = os.path.join(diff_dir, 'highlighted_diff.png')
    raw_path = os.path.join(diff_dir, 'raw_diff.png')
    
    highlighted_diff.save(highlighted_path)
    raw_diff.save(raw_path)
    
    print(f"OK Saved highlighted diff: {highlighted_path}")
    print(f"OK Saved raw diff: {raw_path}")
    
    # Validate results
    assert metrics['diff_mismatch_pct'] > 0, "Should detect differences"
    assert metrics['diff_pixels_changed'] > 0, "Should have changed pixels"
    assert len(bounding_boxes) > 0, "Should find bounding boxes"
    
    print("OK All validations passed!")
    
    # Return metrics for main function
    result = {
        'mismatch_pct': metrics['diff_mismatch_pct'],
        'pixels_changed': metrics['diff_pixels_changed'],
        'bounding_boxes': bounding_boxes
    }
    
    return result

def test_configuration():
    """Test configuration system"""
    print("\n=== Testing Configuration ===")
    
    # Test default config
    config = DiffConfig()
    print(f"OK Default per_pixel_threshold: {config.per_pixel_threshold}")
    print(f"OK Default min_diff_area: {config.min_diff_area}")
    print(f"OK Default overlay_alpha: {config.overlay_alpha}")
    print(f"OK Default output_dir: {config.output_dir}")
    print(f"OK Default enable_blur: {config.enable_blur}")
    print(f"OK Default dilate_iterations: {config.dilate_iterations}")

def cleanup():
    """Clean up test files"""
    print("\n=== Cleaning Up ===")
    if os.path.exists('screenshots/test_simple'):
        shutil.rmtree('screenshots/test_simple')
        print("OK Removed test files")

def main():
    """Run all tests"""
    print("Starting Visual Diff Engine Tests")
    print("=" * 50)
    
    try:
        # Test configuration
        test_configuration()
        
        # Test diff engine
        result = test_diff_engine()
        
        print("\n" + "=" * 50)
        print("SUCCESS: ALL TESTS PASSED!")
        print(f"Final Results:")
        print(f"   - Detected {result['mismatch_pct']:.2f}% difference")
        print(f"   - Found {result['pixels_changed']:,} changed pixels")
        print(f"   - Identified {len(result['bounding_boxes'])} difference regions")
        
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        cleanup()
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)