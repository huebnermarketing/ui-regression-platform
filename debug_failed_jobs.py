#!/usr/bin/env python3
"""
Debug script to investigate failed crawl jobs
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_failed_jobs():
    """Debug failed crawl jobs"""
    try:
        from app import app, db, crawler_scheduler
        from models.crawl_job import CrawlJob
        from models.project import Project
        
        with app.app_context():
            print("=== Failed Jobs Debug ===")
            
            # Get all jobs
            all_jobs = CrawlJob.query.all()
            print(f"Total jobs in database: {len(all_jobs)}")
            
            # Get failed jobs
            failed_jobs = CrawlJob.query.filter_by(status='failed').all()
            print(f"Failed jobs: {len(failed_jobs)}")
            
            # Get recent jobs for project 45
            project_45_jobs = CrawlJob.query.filter_by(project_id=45).order_by(CrawlJob.id.desc()).limit(5).all()
            print(f"\nRecent jobs for project 45: {len(project_45_jobs)}")
            
            for job in project_45_jobs:
                print(f"  Job {job.id}: Status={job.status}, Started={job.started_at}, Error={job.error_message}")
            
            # Check scheduler state
            print(f"\nScheduler running jobs: {len(crawler_scheduler.running_jobs)}")
            for project_id, job_info in crawler_scheduler.running_jobs.items():
                print(f"  Project {project_id}: Job {job_info['job_id']}, Thread alive: {job_info['thread'].is_alive()}")
            
            # Check progress info
            print(f"\nScheduler progress info: {len(crawler_scheduler.progress_info)}")
            for project_id, progress in crawler_scheduler.progress_info.items():
                print(f"  Project {project_id}: {progress}")
            
            # Get the latest job
            latest_job = CrawlJob.query.order_by(CrawlJob.id.desc()).first()
            if latest_job:
                print(f"\nLatest job details:")
                print(f"  ID: {latest_job.id}")
                print(f"  Project: {latest_job.project_id}")
                print(f"  Status: {latest_job.status}")
                print(f"  Started: {latest_job.started_at}")
                print(f"  Completed: {latest_job.completed_at}")
                print(f"  Error: {latest_job.error_message}")
                print(f"  Pages: {latest_job.total_pages}")
            
    except Exception as e:
        print(f"Error during debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_failed_jobs()