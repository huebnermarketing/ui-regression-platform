#!/usr/bin/env python3
"""
Test script to verify atomic completion prevents race conditions.
This tests the new robust completion logic.
"""

import sys
import os
import time
import threading
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.project import Project
from models.crawl_job import CrawlJob

def test_atomic_completion():
    """Test that atomic completion prevents race conditions"""
    with app.app_context():
        print("=== Testing Atomic Completion Logic ===\n")
        
        # Find a project to test with
        project = Project.query.first()
        if not project:
            print("No projects found. Creating a test project...")
            project = Project(
                name="Atomic Test Project",
                staging_url="https://staging.example.com",
                production_url="https://production.example.com",
                user_id=1
            )
            db.session.add(project)
            db.session.commit()
            print(f"Created test project: {project.name}")
        
        print(f"Using project: {project.name} (ID: {project.id})")
        
        # Test 1: Normal atomic completion
        print("\n1. Testing normal atomic completion...")
        test_job = CrawlJob(project_id=project.id)
        test_job.start_job()  # Mark as running
        db.session.add(test_job)
        db.session.commit()
        
        print(f"Created job {test_job.id} with status: {test_job.status}")
        
        # Complete the job atomically
        success = test_job.complete_job(total_pages=17)
        db.session.commit()
        
        if success:
            print(f"SUCCESS: Job {test_job.id} completed atomically")
            print(f"  Status: {test_job.status}")
            print(f"  Total pages: {test_job.total_pages}")
            print(f"  Completed at: {test_job.completed_at}")
        else:
            print(f"UNEXPECTED: Job {test_job.id} completion was not successful")
        
        # Test 2: Idempotent completion (try to complete again)
        print(f"\n2. Testing idempotent completion...")
        success2 = test_job.complete_job(total_pages=20)  # Different page count
        db.session.commit()
        
        if not success2:
            print(f"SUCCESS: Job {test_job.id} completion was idempotent (already completed)")
            print(f"  Status remains: {test_job.status}")
            print(f"  Total pages unchanged: {test_job.total_pages}")
        else:
            print(f"UNEXPECTED: Job {test_job.id} was completed again (should be idempotent)")
        
        # Test 3: Concurrent completion simulation
        print(f"\n3. Testing concurrent completion simulation...")
        
        # Create another job for concurrent test
        concurrent_job = CrawlJob(project_id=project.id)
        concurrent_job.start_job()
        db.session.add(concurrent_job)
        db.session.commit()
        
        print(f"Created concurrent job {concurrent_job.id}")
        
        # Simulate two threads trying to complete the same job
        results = []
        
        def complete_job_thread(job_id, pages, thread_name):
            with app.app_context():
                job = CrawlJob.query.get(job_id)
                success = job.complete_job(pages)
                db.session.commit()
                results.append((thread_name, success, job.status, job.total_pages))
                print(f"  {thread_name}: success={success}, status={job.status}, pages={job.total_pages}")
        
        # Start two threads trying to complete the same job
        thread1 = threading.Thread(target=complete_job_thread, args=[concurrent_job.id, 15, "Thread1"])
        thread2 = threading.Thread(target=complete_job_thread, args=[concurrent_job.id, 25, "Thread2"])
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Analyze results
        successful_completions = sum(1 for _, success, _, _ in results if success)
        print(f"Successful completions: {successful_completions}/2")
        
        if successful_completions == 1:
            print("SUCCESS: Exactly one thread completed the job (atomic)")
        else:
            print("FAILURE: Multiple threads completed the job (race condition)")
        
        # Test 4: Safe orphan cleanup test
        print(f"\n4. Testing safe orphan cleanup...")
        
        # Create an old running job (simulate orphaned job)
        old_job = CrawlJob(project_id=project.id)
        old_job.start_job()
        # Manually set old start time
        old_job.started_at = datetime.utcnow() - timedelta(minutes=15)
        db.session.add(old_job)
        db.session.commit()
        
        print(f"Created old job {old_job.id} (started 15 minutes ago)")
        
        # Test the safe cleanup logic
        from sqlalchemy import text
        result = db.session.execute(text('''
            UPDATE crawl_jobs 
            SET status='failed', 
                error_message='Job process terminated unexpectedly (orphaned)',
                completed_at=NOW()
            WHERE id=:job_id 
              AND status='running' 
              AND completed_at IS NULL
              AND started_at < NOW() - INTERVAL 10 MINUTE
        '''), {'job_id': old_job.id})
        
        if result.rowcount == 1:
            print(f"SUCCESS: Old job {old_job.id} was safely marked as orphaned")
            db.session.refresh(old_job)
            print(f"  Status: {old_job.status}")
            print(f"  Error: {old_job.error_message}")
        else:
            print(f"UNEXPECTED: Old job {old_job.id} was not marked as orphaned")
        
        db.session.commit()
        
        # Clean up test jobs
        print(f"\n5. Cleaning up test jobs...")
        for job in [test_job, concurrent_job, old_job]:
            db.session.delete(job)
        db.session.commit()
        print("Test jobs cleaned up.")
        
        print("\n=== Atomic Completion Test Complete ===")

if __name__ == "__main__":
    test_atomic_completion()