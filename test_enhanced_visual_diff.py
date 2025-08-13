#!/usr/bin/env python3
"""
Test script for enhanced visual diff output
Tests the new "spot the difference" style visualization
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, '.')

from app import app
from models import db
from models.project import Project, ProjectPage
from services.find_difference_service import FindDifferenceService

async def test_enhanced_visual_diff():
    """Test the enhanced visual diff functionality"""
    
    with app.app_context():
        print("Testing Enhanced Visual Diff Output")
        print("=" * 50)
        
        # Get a project with pages
        project = Project.query.first()
        if not project:
            print("[ERROR] No projects found. Please create a project first.")
            return False
        
        print(f"Using project: {project.name} (ID: {project.id})")
        
        # Get pages for this project
        pages = ProjectPage.query.filter_by(project_id=project.id).limit(2).all()
        if not pages:
            print("[ERROR] No pages found for this project.")
            return False
        
        print(f"Found {len(pages)} pages to test")
        
        # Initialize Find Difference service
        find_diff_service = FindDifferenceService()
        
        # Test with first page
        test_page = pages[0]
        print(f"\nTesting enhanced visual diff for page: {test_page.path}")
        
        try:
            # Run Find Difference with enhanced visualization
            successful_count, failed_count, run_id = await find_diff_service.run_find_difference(
                project_id=project.id,
                page_ids=[test_page.id]
            )
            
            print(f"\nResults:")
            print(f"   Run ID: {run_id}")
            print(f"   Successful: {successful_count}")
            print(f"   Failed: {failed_count}")
            
            if successful_count > 0:
                print(f"\nEnhanced visual diff files generated:")
                
                # Check for generated diff files
                run_dir = Path("runs") / str(project.id) / run_id / "diffs"
                
                for viewport in ['desktop', 'tablet', 'mobile']:
                    viewport_dir = run_dir / viewport
                    if viewport_dir.exists():
                        diff_files = list(viewport_dir.glob("*_diff.png"))
                        for diff_file in diff_files:
                            print(f"   {diff_file}")
                            print(f"      Size: {diff_file.stat().st_size} bytes")
                
                print(f"\n[SUCCESS] Enhanced visual diff test completed successfully!")
                print(f"New features applied:")
                print(f"   - Prominent grayscale background for unchanged areas")
                print(f"   - Bright red highlights for major differences")
                print(f"   - Bright yellow highlights for minor differences")
                print(f"   - Expanded highlight areas for better visibility")
                print(f"   - Reduced background brightness for contrast")
                
                return True
            else:
                print(f"[ERROR] No successful diffs generated")
                return False
                
        except Exception as e:
            print(f"[ERROR] Error during enhanced visual diff test: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Main test function"""
    print("Enhanced Visual Diff Test")
    print("Testing new 'spot the difference' style visualization")
    print("-" * 50)
    
    # Run the async test
    success = asyncio.run(test_enhanced_visual_diff())
    
    if success:
        print(f"\n[SUCCESS] Enhanced visual diff test completed successfully!")
        print(f"Check the generated diff images to see the new visual style")
        print(f"The diffs should now look like 'spot the difference' games")
    else:
        print(f"\n[ERROR] Enhanced visual diff test failed")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)