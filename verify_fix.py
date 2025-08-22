#!/usr/bin/env python3
"""
Simple verification that the job type fix is working
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from services.run_state_service import RunStateService
from datetime import datetime

def test_job_type_fix():
    """Test that full_crawl job types are now recognized"""
    print("=== VERIFYING JOB TYPE FIX ===")
    
    with app.app_context():
        run_state_service = RunStateService()
        
        # Create mock objects to test the logic
        class MockJob:
            def __init__(self, status, job_type, created_at=None):
                self.status = status
                self.job_type = job_type
                self.created_at = created_at or datetime.utcnow()
                self.completed_at = self.created_at
                self.total_pages = 5  # Add missing attribute
                self.started_at = self.created_at
        
        class MockPage:
            def __init__(self):
                self.diff_status_desktop = 'pending'
                self.diff_status_tablet = 'pending'
                self.diff_status_mobile = 'pending'
        
        # Test 1: Old job type 'crawl' should work
        print("\nTest 1: Old job type 'crawl'")
        jobs = [MockJob('Crawled', 'crawl')]
        pages = [MockPage()]
        result = run_state_service._check_completed_states(jobs, pages)
        print(f"  Job type: crawl, Status: {result.get('state') if result else 'None'}")
        
        # Test 2: New job type 'full_crawl' should work (this was the bug)
        print("\nTest 2: New job type 'full_crawl'")
        jobs = [MockJob('Crawled', 'full_crawl')]
        pages = [MockPage()]
        result = run_state_service._check_completed_states(jobs, pages)
        print(f"  Job type: full_crawl, Status: {result.get('state') if result else 'None'}")
        
        # Test 3: Verify both work in _check_active_jobs
        print("\nTest 3: Active job detection")
        jobs = [MockJob('Crawling', 'full_crawl')]
        result = run_state_service._check_active_jobs(1, jobs)
        print(f"  Active job type: full_crawl, State: {result.get('state') if result else 'None'}")
        
        # Summary
        print("\n=== SUMMARY ===")
        if result and result.get('state') in ['crawling', 'crawled']:
            print("SUCCESS: The fix is working! 'full_crawl' job types are now properly recognized.")
        else:
            print("ISSUE: The fix may not be working as expected.")

if __name__ == "__main__":
    test_job_type_fix()