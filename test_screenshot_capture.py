#!/usr/bin/env python3
"""
Test script for screenshot capture functionality
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db
from models.project import Project, ProjectPage
from screenshot.screenshot_service import ScreenshotService

def test_screenshot_service():
    """Test the screenshot service functionality"""
    
    with app.app_context():
        print("🧪 Testing Screenshot Capture Service")
        print("=" * 50)
        
        # Initialize screenshot service
        screenshot_service = ScreenshotService()
        print(f"✅ Screenshot service initialized")
        print(f"📁 Base directory: {screenshot_service.base_screenshot_dir}")
        
        # Test slugify function
        test_paths = [
            "/",
            "/about",
            "/about/team",
            "/products/category-1/item-2",
            "/special-chars?query=test&page=1",
            "/with spaces and/special@chars"
        ]
        
        print("\n🔤 Testing path slugification:")
        for path in test_paths:
            slug = screenshot_service.slugify_path(path)
            print(f"  '{path}' → '{slug}'")
        
        # Test screenshot path generation
        print("\n📂 Testing screenshot path generation:")
        project_id = 1
        test_path = "/about/team"
        staging_path, production_path = screenshot_service.get_screenshot_paths(project_id, test_path)
        print(f"  Project ID: {project_id}")
        print(f"  Page path: {test_path}")
        print(f"  Staging path: {staging_path}")
        print(f"  Production path: {production_path}")
        
        # Check if directories would be created
        print(f"  Staging dir exists: {staging_path.parent.exists()}")
        print(f"  Production dir exists: {production_path.parent.exists()}")
        
        # Test with actual project data if available
        projects = Project.query.limit(1).all()
        if projects:
            project = projects[0]
            print(f"\n🎯 Testing with actual project: {project.name}")
            
            pages = ProjectPage.query.filter_by(project_id=project.id).limit(3).all()
            if pages:
                print(f"📄 Found {len(pages)} pages to test with:")
                for page in pages:
                    print(f"  - {page.path} ({page.status})")
                    staging_path, production_path = screenshot_service.get_screenshot_paths(
                        project.id, page.path
                    )
                    print(f"    Staging: {staging_path}")
                    print(f"    Production: {production_path}")
            else:
                print("⚠️  No pages found for this project")
        else:
            print("⚠️  No projects found in database")
        
        print("\n✅ Screenshot service test completed!")

async def test_single_screenshot():
    """Test capturing a single screenshot"""
    
    print("\n📸 Testing single screenshot capture")
    print("=" * 50)
    
    # Test with a reliable website
    test_url = "https://httpbin.org/html"
    output_path = Path("screenshots/test/test_screenshot.png")
    
    screenshot_service = ScreenshotService()
    
    print(f"🌐 Testing URL: {test_url}")
    print(f"💾 Output path: {output_path}")
    
    try:
        success = await screenshot_service.capture_screenshot(test_url, output_path)
        
        if success:
            print("✅ Screenshot captured successfully!")
            print(f"📁 File exists: {output_path.exists()}")
            if output_path.exists():
                file_size = output_path.stat().st_size
                print(f"📊 File size: {file_size:,} bytes")
        else:
            print("❌ Screenshot capture failed")
            
    except Exception as e:
        print(f"💥 Error during screenshot capture: {str(e)}")

def test_database_integration():
    """Test database integration"""
    
    with app.app_context():
        print("\n🗄️  Testing database integration")
        print("=" * 50)
        
        # Check if we have projects and pages
        project_count = Project.query.count()
        page_count = ProjectPage.query.count()
        
        print(f"📊 Database stats:")
        print(f"  Projects: {project_count}")
        print(f"  Pages: {page_count}")
        
        if page_count > 0:
            # Check page statuses
            statuses = db.session.query(ProjectPage.status).distinct().all()
            print(f"  Page statuses: {[s[0] for s in statuses]}")
            
            # Check for pages ready for screenshot
            ready_pages = ProjectPage.query.filter(
                ProjectPage.status.in_(['crawled', 'ready_for_screenshot'])
            ).count()
            print(f"  Pages ready for screenshot: {ready_pages}")
            
            # Check for completed screenshots
            completed_pages = ProjectPage.query.filter_by(status='screenshot_complete').count()
            print(f"  Pages with completed screenshots: {completed_pages}")
            
            # Show sample pages
            sample_pages = ProjectPage.query.limit(3).all()
            print(f"\n📄 Sample pages:")
            for page in sample_pages:
                print(f"  - {page.path} ({page.status})")
                if page.staging_screenshot_path:
                    print(f"    Staging screenshot: {page.staging_screenshot_path}")
                if page.production_screenshot_path:
                    print(f"    Production screenshot: {page.production_screenshot_path}")
        
        print("\n✅ Database integration test completed!")

def main():
    """Main test function"""
    
    print("🚀 Screenshot Capture System Test")
    print("=" * 60)
    
    # Test 1: Basic service functionality
    test_screenshot_service()
    
    # Test 2: Database integration
    test_database_integration()
    
    # Test 3: Single screenshot capture (optional)
    print("\n" + "=" * 60)
    response = input("🤔 Do you want to test actual screenshot capture? (y/N): ").strip().lower()
    if response in ['y', 'yes']:
        asyncio.run(test_single_screenshot())
    else:
        print("⏭️  Skipping actual screenshot capture test")
    
    print("\n🎉 All tests completed!")
    print("\n📋 Next steps:")
    print("1. Run the migration: python migrations/add_screenshot_fields.py")
    print("2. Install Playwright browsers: playwright install chromium")
    print("3. Start the application and test screenshot capture via web interface")

if __name__ == "__main__":
    main()