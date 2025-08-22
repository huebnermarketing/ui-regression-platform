#!/usr/bin/env python3

from app import app
from models.project import Project
from models.crawl_job import CrawlJob

def check_project_104():
    with app.app_context():
        # Check if project 104 exists
        project = Project.query.filter_by(id=104).first()
        
        if project:
            print(f"[FOUND] Project 104: '{project.name}'")
            print(f"   Created: {project.created_at}")
            print(f"   User ID: {project.user_id}")
            print(f"   Staging URL: {project.staging_url}")
            print(f"   Production URL: {project.production_url}")
            
            # Check for crawl jobs
            jobs = CrawlJob.query.filter_by(project_id=104).order_by(CrawlJob.created_at.desc()).all()
            print(f"   Number of crawl jobs: {len(jobs)}")
            
            if jobs:
                print("   Recent jobs:")
                for job in jobs[:5]:  # Show last 5 jobs
                    print(f"     Job {job.id}: Status={job.status}, Created={job.created_at}, Type={job.job_type}")
            else:
                print("   [NO JOBS] No crawl jobs found for this project")
                print("   [INFO] This means no screenshots have been captured yet")
                
        else:
            print("[NOT FOUND] Project 104 does not exist in the database")
            
        # Also check what projects do exist
        print("\n[LIST] Existing projects:")
        all_projects = Project.query.order_by(Project.id.desc()).limit(10).all()
        for p in all_projects:
            print(f"   Project {p.id}: {p.name}")

if __name__ == "__main__":
    check_project_104()