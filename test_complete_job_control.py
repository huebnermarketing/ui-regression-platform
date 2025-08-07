"""
Complete test script to verify job control functionality
"""

import sys
import os
import time
import threading
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, crawler_scheduler
from models.crawl_job import CrawlJob
from models.project import Project

def test_complete_job_control():
    with app.app_context():
        print("Testing complete job control functionality...")
        
        # Find a project to test with
        project = Project.query.first()
        if not project:
            print("No projects found. Please create a project first.")
            return
        
        print(f"Using project: {project.name} (ID: {project.id})")
        
        # Start a new crawl job
        print("Starting new crawl job...")
        job_id = crawler_scheduler.schedule_crawl(project.id)
        print(f"Started job ID: {job_id}")
        
        # Wait a moment for the job to start and be committed to database
        time.sleep(3)
        
        # Check job status
        job = CrawlJob.query.get(job_id)
        if job:
            print(f"Job status in database: {job.status}")
        else:
            print(f"Job {job_id} not found in database yet, waiting...")
            time.sleep(2)
            job = CrawlJob.query.get(job_id)
            if job:
                print(f"Job status in database: {job.status}")
            else:
                print("Job still not found, exiting test")
                return
        
        # Check if job is in scheduler
        if project.id in crawler_scheduler.running_jobs:
            job_info = crawler_scheduler.running_jobs[project.id]
            print(f"Job found in scheduler: {job_info}")
            
            # Test pause functionality
            print("\nTesting PAUSE functionality...")
            success = crawler_scheduler.pause_job(job_id)
            print(f"Pause command result: {success}")
            
            # Wait a moment and check flags
            time.sleep(1)
            if project.id in crawler_scheduler.running_jobs:
                flags = crawler_scheduler.running_jobs[project.id]
                print(f"Scheduler flags after pause: should_pause={flags.get('should_pause')}, should_stop={flags.get('should_stop')}")
            
            # Test stop functionality
            print("\nTesting STOP functionality...")
            success = crawler_scheduler.stop_job(job_id)
            print(f"Stop command result: {success}")
            
            # Wait a moment and check flags
            time.sleep(1)
            if project.id in crawler_scheduler.running_jobs:
                flags = crawler_scheduler.running_jobs[project.id]
                print(f"Scheduler flags after stop: should_pause={flags.get('should_pause')}, should_stop={flags.get('should_stop')}")
            
            # Wait for job to actually stop
            print("\nWaiting for job to stop...")
            for i in range(10):
                time.sleep(1)
                job = CrawlJob.query.get(job_id)
                print(f"Job status after {i+1}s: {job.status}")
                if job.status != 'running':
                    break
            
        else:
            print("Job not found in scheduler running_jobs")
        
        print("\nFinal job status:")
        job = CrawlJob.query.get(job_id)
        print(f"Job {job_id}: Status = {job.status}, Error = {job.error_message}")

if __name__ == '__main__':
    test_complete_job_control()