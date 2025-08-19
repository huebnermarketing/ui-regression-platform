#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db
from models.crawl_job import CrawlJob
from models.project import Project, ProjectPage
import app

def check_crawl_jobs():
    with app.app.app_context():
        print("=== CRAWL JOBS STATUS CHECK ===")
        
        # Get all crawl jobs
        jobs = CrawlJob.query.order_by(CrawlJob.id.desc()).limit(10).all()
        
        if not jobs:
            print("No crawl jobs found in database.")
            return
            
        print(f"Found {len(jobs)} recent crawl jobs:")
        print()
        
        for job in jobs:
            print(f"Job ID: {job.id} (Job #{job.job_number})")
            print(f"Project ID: {job.project_id}")
            print(f"Status: {job.status}")
            print(f"Created: {job.created_at}")
            print(f"Started: {job.started_at}")
            print(f"Updated: {job.updated_at}")
            print(f"Completed: {job.completed_at}")
            print(f"Total Pages: {job.total_pages}")
            print(f"Error: {job.error_message}")
            print("-" * 50)
        
        # Check project pages for the projects with crawl jobs
        print("\n=== PROJECT PAGES STATUS ===")
        project_ids = list(set([job.project_id for job in jobs]))
        
        for project_id in project_ids:
            pages = ProjectPage.query.filter_by(project_id=project_id).count()
            print(f"Project {project_id}: {pages} pages discovered")
        
        # Check for jobs that should be completed but aren't
        print("\n=== POTENTIAL ISSUES ===")
        running_jobs = [job for job in jobs if job.status == 'Crawling']
        
        for job in running_jobs:
            pages_count = ProjectPage.query.filter_by(project_id=job.project_id).count()
            if pages_count > 0 and job.total_pages == 0:
                print(f"⚠️  Job {job.id} is 'Crawling' but project {job.project_id} has {pages_count} pages - job may need completion")

if __name__ == "__main__":
    check_crawl_jobs()