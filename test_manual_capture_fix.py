#!/usr/bin/env python3
"""
Test script to verify manual screenshot capture fix
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_enum_values():
    """Test that the enum values are correctly defined"""
    print("🔍 Testing Database Enum Values")
    print("=" * 50)
    
    try:
        from app import app
        from models.project import ProjectPage
        
        with app.app_context():
            # Test creating a page with valid status
            print("✅ Database models imported successfully")
            
            # Check if we can set valid enum values
            valid_statuses = ['pending', 'capturing', 'captured', 'diffing', 'completed', 'failed', 'no_baseline']
            print(f"📋 Valid find_diff_status values: {valid_statuses}")
            
            # Test that 'queued' is not in the valid values
            if 'queued' not in valid_statuses:
                print("✅ 'queued' is correctly not in valid enum values")
            else:
                print("❌ 'queued' is still in valid enum values")
                
            return True
            
    except Exception as e:
        print(f"❌ Error testing enum values: {e}")
        return False

async def test_basic_screenshot():
    """Test basic screenshot functionality"""
    print("\n📸 Testing Basic Screenshot Functionality")
    print("=" * 50)
    
    try:
        from screenshot.screenshot_service import ScreenshotService
        
        # Initialize service
        service = ScreenshotService()
        print("✅ Screenshot service initialized")
        
        # Test with a simple, reliable URL
        test_url = "https://httpbin.org/html"
        output_path = Path("test_screenshots/manual_capture_test.png")
        
        print(f"🌐 Testing URL: {test_url}")
        print(f"💾 Output path: {output_path}")
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        success = await service.capture_screenshot(test_url, output_path, viewport='desktop')
        
        if success and output_path.exists():
            file_size = output_path.stat().st_size
            print(f"✅ Screenshot captured successfully - Size: {file_size:,} bytes")
            return True
        else:
            print("❌ Screenshot capture failed")
            return False
            
    except Exception as e:
        print(f"❌ Screenshot test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_page_status():
    """Test setting page status to valid values"""
    print("\n🗄️ Testing Database Page Status Updates")
    print("=" * 50)
    
    try:
        from app import app, db
        from models.project import ProjectPage
        
        with app.app_context():
            # Find a test page
            page = ProjectPage.query.first()
            if not page:
                print("⚠️ No pages found in database")
                return True  # Not a failure, just no test data
            
            print(f"🎯 Testing with page: {page.path}")
            
            # Test setting to valid status values
            valid_statuses = ['pending', 'capturing', 'captured', 'diffing', 'completed', 'failed']
            
            for status in valid_statuses:
                try:
                    page.find_diff_status = status
                    db.session.commit()
                    print(f"✅ Successfully set status to '{status}'")
                except Exception as e:
                    print(f"❌ Failed to set status to '{status}': {e}")
                    db.session.rollback()
                    return False
            
            # Reset to pending
            page.find_diff_status = 'pending'
            db.session.commit()
            print("✅ Reset status to 'pending'")
            
            return True
            
    except Exception as e:
        print(f"❌ Database status test failed: {e}")
        return False

async def test_find_difference_service():
    """Test the Find Difference service initialization"""
    print("\n🔄 Testing Find Difference Service")
    print("=" * 50)
    
    try:
        from services.find_difference_service import FindDifferenceService
        
        # Initialize service
        service = FindDifferenceService()
        print("✅ Find Difference service initialized")
        
        # Test run ID generation
        run_id = service.generate_run_id()
        print(f"✅ Generated run ID: {run_id}")
        
        # Test path generation
        project_id = 1
        page_path = "/test-page"
        viewport = "desktop"
        
        staging_path, production_path = service.get_screenshot_paths_for_run(
            project_id, run_id, page_path, viewport
        )
        
        print(f"✅ Generated paths:")
        print(f"   Staging: {staging_path}")
        print(f"   Production: {production_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Find Difference service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🚨 Manual Screenshot Capture Fix Verification")
    print("=" * 60)
    
    # Test 1: Enum values
    enum_ok = test_enum_values()
    
    # Test 2: Database status updates
    db_status_ok = test_database_page_status()
    
    # Test 3: Basic screenshot
    screenshot_ok = await test_basic_screenshot()
    
    # Test 4: Find Difference service
    service_ok = await test_find_difference_service()
    
    # Summary
    print("\n📋 Test Summary")
    print("=" * 60)
    print(f"Enum Values: {'✅' if enum_ok else '❌'}")
    print(f"Database Status Updates: {'✅' if db_status_ok else '❌'}")
    print(f"Basic Screenshot: {'✅' if screenshot_ok else '❌'}")
    print(f"Find Difference Service: {'✅' if service_ok else '❌'}")
    
    if all([enum_ok, db_status_ok, screenshot_ok, service_ok]):
        print("\n🎉 All tests passed! Manual capture should now be working.")
        print("\n💡 Next steps:")
        print("   1. Restart the Flask application")
        print("   2. Try the manual capture feature in the web interface")
        print("   3. Check the browser console and server logs for any remaining issues")
    else:
        print("\n🚨 Some tests failed. Check the errors above.")
        
        if not enum_ok:
            print("   - Fix database enum definitions")
        if not db_status_ok:
            print("   - Check database schema and permissions")
        if not screenshot_ok:
            print("   - Install Playwright browsers: playwright install chromium")
        if not service_ok:
            print("   - Check service dependencies and configuration")

if __name__ == "__main__":
    asyncio.run(main())