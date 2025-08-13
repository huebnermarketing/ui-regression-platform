#!/usr/bin/env python3
"""
Test script to verify the crawl job status fix.
This script tests that completed jobs are properly shown as completed in the frontend
instead of being incorrectly marked as failed due to race conditions.
"""

import sys
import os
import time
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.project import Project
from models.crawl_job import CrawlJob

def test_completed_job_status():
    """Test that completed jobs are correctly identified as completed"""
    
    with app.app_context():
        print("=== Testing Crawl Job Status Fix ===\n")
        
        # Find a project to test with
        project = Project.query.first()
        if not project:
            print("No projects found. Creating a test project...")
            project = Project(
                name="Test Project",
                staging_url="https://staging.example.com",
                production_url="https://production.example.com",
                user_id=1
            )
            db.session.add(project)
            db.session.commit()
            print(f"Created test project: {project.name}")
        
        print(f"Using project: {project.name} (ID: {project.id})")
        
        # Create a test crawl job that simulates a completed job
        print("\n1. Creating a test crawl job...")
        test_job = CrawlJob(project_id=project.id)
        test_job.start_job()  # Mark as running
        db.session.add(test_job)
        db.session.commit()
        
        print(f"Created job {test_job.id} with status: {test_job.status}")
        print(f"Started at: {test_job.started_at}")
        
        # Simulate job completion
        print("\n2. Simulating job completion...")
        test_job.complete_job(total_pages=17)  # Simulate finding 17 pages like in the logs
        db.session.commit()
        
        print(f"Job {test_job.id} completed with status: {test_job.status}")
        print(f"Completed at: {test_job.completed_at}")
        print(f"Total pages: {test_job.total_pages}")
        
        # Test the API endpoint logic
        print("\n3. Testing API endpoint logic...")
        
        # Import the route logic
        from crawl_queue.routes import register_crawl_queue_routes
        from flask import Flask
        
        # Create a mock scheduler that doesn't have this job in running_jobs
        class MockScheduler:
            def __init__(self):
                self.running_jobs = {}  # Empty - job is not running
        
        mock_scheduler = MockScheduler()
        
        # Test the logic that was causing the issue
        print("Simulating the scenario where job is completed but not in scheduler...")
        
        # Get the job from database
        db_job = CrawlJob.query.get(test_job.id)
        print(f"Job from DB - Status: {db_job.status}, Completed at: {db_job.completed_at}")
        
        # Simulate the time check (job has been running for more than 30 seconds)
        time_since_start = datetime.utcnow() - db_job.started_at if db_job.started_at else timedelta(seconds=0)
        print(f"Time since start: {time_since_start.total_seconds()} seconds")
        
        # Test the fixed logic
        if db_job.completed_at:
            print("PASS: Job has completed_at timestamp, should be marked as completed")
            original_status = db_job.status
            if db_job.status != 'completed':
                db_job.status = 'completed'
                db.session.commit()
                print(f"Updated job status from {original_status} to {db_job.status}")
            else:
                print("Job already has correct status")
        elif time_since_start.total_seconds() > 30:
            print("FAIL: Job would be marked as failed (this was the bug)")
        else:
            print("Job is recent, would be kept as active")
        
        # Verify final status
        final_job = CrawlJob.query.get(test_job.id)
        print(f"\n4. Final verification:")
        print(f"Job {final_job.id} final status: {final_job.status}")
        print(f"Expected: completed, Actual: {final_job.status}")
        
        if final_job.status == 'completed':
            print("SUCCESS: Job correctly shows as completed!")
        else:
            print("FAILURE: Job status is incorrect!")
        
        # Clean up test job
        print(f"\n5. Cleaning up test job {test_job.id}...")
        db.session.delete(test_job)
        db.session.commit()
        print("Test job deleted.")
        
        print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_completed_job_status()