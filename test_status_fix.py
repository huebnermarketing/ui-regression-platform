#!/usr/bin/env python3
"""
Test script to verify the status inconsistency fix
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db
from models.project import Project, ProjectPage
from models.crawl_job import CrawlJob
from services.run_state_service import RunStateService

def test_status_fix():
    """Test that the status fix is working"""
    print("=== TESTING STATUS FIX ===")
    
    with app.app_context():
        # Get all projects and their statuses
        projects = Project.query.all()
        run_state_service = RunStateService()
        
        print(f"Found {len(projects)} projects")
        
        for project in projects:
            jobs = CrawlJob.query.filter_by(project_id=project.id).order_by(CrawlJob.created_at.desc()).all()
            pages = ProjectPage.query.filter_by(project_id=project.id).all()
            run_state = run_state_service.get_project_run_state(project.id)
            
            print(f"\nProject {project.id} ({project.name}):")
            print(f"  Status: {run_state.get('state')}")
            print(f"  Jobs: {len(jobs)}")
            print(f"  Pages: {len(pages)}")
            
            if jobs:
                latest_job = jobs[0]
                print(f"  Latest job: {latest_job.id} - {latest_job.status} ({latest_job.job_type})")
                
                # Check for specific cases
                has_crawled_jobs = any(job.status == 'Crawled' for job in jobs)
                has_ready_jobs = any(job.status == 'ready' for job in jobs)
                has_running_jobs = any(job.status in ['Crawling', 'pending', 'finding_difference'] for job in jobs)
                
                print(f"  Has crawled jobs: {has_crawled_jobs}")
                print(f"  Has ready jobs: {has_ready_jobs}")
                print(f"  Has running jobs: {has_running_jobs}")
                
                # Test the specific case mentioned in the issue
                if has_crawled_jobs and not has_ready_jobs and not has_running_jobs and len(pages) > 0:
                    expected_status = 'crawled'
                    actual_status = run_state.get('state')
                    if actual_status == expected_status:
                        print(f"  [OK] CORRECT: Should show '{expected_status}' and shows '{actual_status}'")
                    else:
                        print(f"  [ISSUE] Should show '{expected_status}' but shows '{actual_status}'")
                        # Check if there are failed jobs causing this
                        failed_jobs = [job for job in jobs if job.status in ['Job Failed', 'diff_failed']]
                        if failed_jobs:
                            print(f"    Reason: Has {len(failed_jobs)} failed jobs taking precedence")

if __name__ == "__main__":
    test_status_fix()