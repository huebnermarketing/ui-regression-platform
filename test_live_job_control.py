"""
Test script to verify job control functionality with a live job
"""

import sys
import os
import time
import threading
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, crawler_scheduler
from models.crawl_job import CrawlJob
from models.project import Project

def test_live_job_control():
    with app.app_context():
        print("Testing live job control functionality...")
        
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
        
        # Wait a moment for the job to start
        time.sleep(1)
        
        # Check if job is in scheduler immediately
        print(f"Checking scheduler running_jobs: {crawler_scheduler.running_jobs}")
        
        if project.id in crawler_scheduler.running_jobs:
            job_info = crawler_scheduler.running_jobs[project.id]
            print(f"Job found in scheduler: {job_info}")
            
            # Test pause functionality immediately
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
            
        else:
            print("Job not found in scheduler running_jobs immediately")
            
        print("\nWaiting 10 seconds to see job behavior...")
        time.sleep(10)
        
        # Check final status
        with app.app_context():
            job = CrawlJob.query.get(job_id)
            if job:
                print(f"Final job status: {job.status}, Error: {job.error_message}")
            else:
                print("Job not found in database")

if __name__ == '__main__':
    test_live_job_control()