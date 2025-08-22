#!/usr/bin/env python3
"""
Final verification that the job type fix is working
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from services.run_state_service import RunStateService
from datetime import datetime

def final_test():
    """Final test to confirm the fix"""
    print("=== FINAL VERIFICATION ===")
    
    with app.app_context():
        run_state_service = RunStateService()
        
        # Create mock objects to test the logic
        class MockJob:
            def __init__(self, status, job_type):
                self.status = status
                self.job_type = job_type
                self.created_at = datetime.utcnow()
                self.completed_at = self.created_at
        
        class MockPage:
            def __init__(self):
                self.diff_status_desktop = 'pending'
                self.diff_status_tablet = 'pending'
                self.diff_status_mobile = 'pending'
        
        # Test the key fix: 'full_crawl' job types should now be recognized
        print("Testing 'full_crawl' job type recognition...")
        jobs = [MockJob('Crawled', 'full_crawl')]
        pages = [MockPage()]
        result = run_state_service._check_completed_states(jobs, pages)
        
        if result and result.get('state') == 'crawled':
            print("✓ SUCCESS: 'full_crawl' job types are now properly recognized as 'crawled'")
            print("✓ The status inconsistency issue has been FIXED!")
        else:
            print("✗ ISSUE: The fix may not be working properly")
            print(f"  Expected: 'crawled', Got: {result.get('state') if result else 'None'}")

if __name__ == "__main__":
    final_test()