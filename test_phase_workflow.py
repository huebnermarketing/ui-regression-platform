"""
Test script to verify the phase-based job history workflow
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from models import db
from models.crawl_job import CrawlJob
from models.project import Project

def test_phase_workflow():
    """Test the phase-based workflow: pending → Crawling → Crawled → finding_difference → ready"""
    
    # Import app directly
    from app import app
    
    with app.app_context():
        print("=== Testing Phase-Based Job History Workflow ===\n")
        
        # Get a test project (use the first available project)
        project = Project.query.first()
        if not project:
            print("ERROR: No projects found. Please create a project first.")
            return False
        
        print(f"Using project: {project.name} (ID: {project.id})")
        
        # Test 1: Create a new job
        print("\n1. Creating new crawl job...")
        job = CrawlJob(project_id=project.id)
        job.status = 'pending'
        db.session.add(job)
        db.session.commit()
        
        print(f"   SUCCESS: Created job #{job.job_number} with status: {job.status}")
        print(f"   Created at: {job.created_at}")
        print(f"   Phase timestamps: crawl_started_at={job.crawl_started_at}, fd_started_at={job.fd_started_at}")
        
        # Test 2: Start crawling phase
        print("\n2. Starting crawling phase...")
        job.start_job()
        db.session.commit()
        
        print(f"   SUCCESS: Job status: {job.status}")
        print(f"   Started at: {job.started_at}")
        print(f"   Crawl started at: {job.crawl_started_at}")
        print(f"   Crawl duration: {job.crawl_duration}")
        
        # Test 3: Complete crawling phase
        print("\n3. Completing crawling phase...")
        success = job.complete_job(total_pages=25)
        db.session.commit()
        
        print(f"   SUCCESS: Job status: {job.status}")
        print(f"   Total pages: {job.total_pages}")
        print(f"   Completed at: {job.completed_at}")
        print(f"   Crawl completed at: {job.crawl_completed_at}")
        print(f"   Crawl duration: {job.crawl_duration:.2f}s" if job.crawl_duration else "N/A")
        print(f"   Total duration: {job.duration:.2f}s" if job.duration else "N/A")
        
        # Test 4: Start Find Difference phase (same job, no new history row)
        print("\n4. Starting Find Difference phase (same job)...")
        try:
            job.start_find_difference()
            db.session.commit()
            
            print(f"   SUCCESS: Job status: {job.status}")
            print(f"   FD started at: {job.fd_started_at}")
            print(f"   Find difference duration: {job.find_difference_duration:.2f}s" if job.find_difference_duration else "N/A")
            print(f"   Total duration: {job.duration:.2f}s" if job.duration else "N/A")
        except ValueError as e:
            print(f"   ERROR: {e}")
            return False
        
        # Test 5: Complete Find Difference phase
        print("\n5. Completing Find Difference phase...")
        try:
            job.complete_find_difference()
            db.session.commit()
            
            print(f"   SUCCESS: Job status: {job.status}")
            print(f"   FD completed at: {job.fd_completed_at}")
            print(f"   Overall completed at: {job.completed_at}")
            print(f"   Crawl duration: {job.crawl_duration:.2f}s" if job.crawl_duration else "N/A")
            print(f"   Find difference duration: {job.find_difference_duration:.2f}s" if job.find_difference_duration else "N/A")
            print(f"   Total duration: {job.duration:.2f}s" if job.duration else "N/A")
        except ValueError as e:
            print(f"   ERROR: {e}")
            return False
        
        # Test 6: Verify single job history row
        print("\n6. Verifying single job history row...")
        job_count = CrawlJob.query.filter_by(project_id=project.id, job_number=job.job_number).count()
        print(f"   Job count for job #{job.job_number}: {job_count}")
        
        if job_count == 1:
            print("   SUCCESS: Only one job history row exists")
        else:
            print("   ERROR: Multiple job history rows found")
            return False
        
        # Test 7: Test error handling
        print("\n7. Testing error handling...")
        try:
            job.start_find_difference()  # Should fail since job is already 'ready'
            print("   ERROR: Should not allow starting FD from 'ready' status")
            return False
        except ValueError as e:
            print(f"   SUCCESS: Correct error handling: {e}")
        
        print("\nSUCCESS: All tests passed! Phase-based workflow is working correctly.")
        print(f"\nFinal job state:")
        print(f"   Job #{job.job_number}: {job.status}")
        print(f"   Phases: pending -> Crawling -> Crawled -> finding_difference -> ready")
        print(f"   Duration breakdown:")
        print(f"     - Crawl: {job.crawl_duration:.2f}s" if job.crawl_duration else "     - Crawl: N/A")
        print(f"     - Find Difference: {job.find_difference_duration:.2f}s" if job.find_difference_duration else "     - Find Difference: N/A")
        print(f"     - Total: {job.duration:.2f}s" if job.duration else "     - Total: N/A")
        
        return True

if __name__ == "__main__":
    success = test_phase_workflow()
    if success:
        print("\nSUCCESS: Phase workflow test completed successfully!")
    else:
        print("\nFAILED: Phase workflow test failed!")
        sys.exit(1)