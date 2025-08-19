#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db
from models.crawl_job import CrawlJob
from models.project import Project, ProjectPage
import app
from datetime import datetime

def fix_stuck_crawl_jobs():
    """Fix crawl jobs that are stuck in 'Crawling' status when they should be completed"""
    
    with app.app.app_context():
        print("=== FIXING STUCK CRAWL JOBS ===")
        
        # Find jobs that are stuck in 'Crawling' status
        stuck_jobs = CrawlJob.query.filter_by(status='Crawling').all()
        
        if not stuck_jobs:
            print("No stuck crawl jobs found.")
            return
            
        print(f"Found {len(stuck_jobs)} jobs stuck in 'Crawling' status:")
        
        for job in stuck_jobs:
            print(f"\nJob ID: {job.id} (Job #{job.job_number}) - Project {job.project_id}")
            print(f"Created: {job.created_at}")
            print(f"Started: {job.started_at}")
            print(f"Updated: {job.updated_at}")
            
            # Check if there are pages discovered for this project
            pages_count = ProjectPage.query.filter_by(project_id=job.project_id).count()
            print(f"Pages discovered for project: {pages_count}")
            
            # Check if there's a newer completed job for the same project
            newer_completed_job = CrawlJob.query.filter(
                CrawlJob.project_id == job.project_id,
                CrawlJob.id > job.id,
                CrawlJob.status.in_(['Crawled', 'Job Failed'])
            ).first()
            
            if newer_completed_job:
                print(f"Found newer completed job {newer_completed_job.id} with status '{newer_completed_job.status}'")
                print(f"Marking job {job.id} as 'Job Failed' (superseded by newer job)")
                
                # Mark the stuck job as failed since it was superseded
                job.status = 'Job Failed'
                job.completed_at = datetime.utcnow()
                job.updated_at = datetime.utcnow()
                job.error_message = f"Job superseded by newer job {newer_completed_job.id}"
                
            elif pages_count > 0 and job.total_pages == 0:
                print(f"Job appears to have completed successfully but wasn't marked as such")
                print(f"Marking job {job.id} as 'Crawled' with {pages_count} pages")
                
                # Mark the job as completed
                job.status = 'Crawled'
                job.completed_at = datetime.utcnow()
                job.updated_at = datetime.utcnow()
                job.total_pages = pages_count
                job.error_message = None
                
            else:
                print(f"Job appears to be genuinely stuck - marking as failed")
                
                # Mark as failed
                job.status = 'Job Failed'
                job.completed_at = datetime.utcnow()
                job.updated_at = datetime.utcnow()
                job.error_message = "Job stuck in crawling status - manually failed"
            
            print(f"Updated job {job.id} status to: {job.status}")
        
        # Commit all changes
        db.session.commit()
        print(f"\n=== FIXED {len(stuck_jobs)} STUCK JOBS ===")

if __name__ == "__main__":
    fix_stuck_crawl_jobs()