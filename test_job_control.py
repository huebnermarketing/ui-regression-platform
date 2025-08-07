"""
Test script to verify job control functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, crawler_scheduler
from models.crawl_job import CrawlJob
from models.project import Project

def test_job_control():
    with app.app_context():
        print("Testing job control functionality...")
        
        # Check if we have any running jobs
        running_jobs = CrawlJob.query.filter_by(status='running').all()
        print(f"Found {len(running_jobs)} running jobs")
        
        for job in running_jobs:
            print(f"Job {job.id}: Project {job.project.name}, Status: {job.status}")
            
            # Check if job is in scheduler
            project_id = job.project_id
            if project_id in crawler_scheduler.running_jobs:
                job_info = crawler_scheduler.running_jobs[project_id]
                print(f"  - Found in scheduler: {job_info}")
                
                # Test pause
                print(f"  - Testing pause for job {job.id}")
                success = crawler_scheduler.pause_job(job.id)
                print(f"  - Pause result: {success}")
                
                # Test stop
                print(f"  - Testing stop for job {job.id}")
                success = crawler_scheduler.stop_job(job.id)
                print(f"  - Stop result: {success}")
            else:
                print(f"  - Job not found in scheduler running_jobs")
        
        print("\nScheduler running jobs:")
        for project_id, job_info in crawler_scheduler.running_jobs.items():
            print(f"  Project {project_id}: {job_info}")

if __name__ == '__main__':
    test_job_control()