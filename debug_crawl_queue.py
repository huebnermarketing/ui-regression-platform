#!/usr/bin/env python3
"""
Debug script to test crawl queue functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db, crawler_scheduler
from models.crawl_job import CrawlJob
from models.project import Project

def debug_crawl_queue():
    """Debug crawl queue functionality"""
    
    with app.app_context():
        print("=== Crawl Queue Debug ===")
        
        # Get all crawl jobs
        jobs = CrawlJob.query.all()
        print(f"Total crawl jobs in database: {len(jobs)}")
        
        for job in jobs:
            print(f"Job {job.id}: Project {job.project_id}, Status: {job.status}")
        
        # Check running jobs in scheduler
        print(f"\nRunning jobs in scheduler: {len(crawler_scheduler.running_jobs)}")
        for project_id, job_info in crawler_scheduler.running_jobs.items():
            print(f"Project {project_id}: Job {job_info['job_id']}, Thread alive: {job_info['thread'].is_alive()}")
        
        # Test stop functionality for a specific job
        if jobs:
            test_job = jobs[-1]  # Get the last job
            print(f"\nTesting stop functionality for job {test_job.id}")
            
            try:
                result = crawler_scheduler.stop_job(test_job.id)
                print(f"Stop job result: {result}")
            except Exception as e:
                print(f"Error stopping job: {e}")
                import traceback
                traceback.print_exc()

if __name__ == '__main__':
    debug_crawl_queue()