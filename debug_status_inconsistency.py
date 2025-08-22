#!/usr/bin/env python3
"""
Debug script to identify status inconsistency between project details and projects list
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db
from models.project import Project, ProjectPage
from models.crawl_job import CrawlJob
from services.run_state_service import RunStateService

def debug_project_status(project_id):
    """Debug status calculation for a specific project"""
    print(f"\n=== DEBUGGING PROJECT {project_id} STATUS ===")
    
    with app.app_context():
        # Get project
        project = Project.query.filter_by(id=project_id).first()
        if not project:
            print(f"Project {project_id} not found")
            return
        
        print(f"Project: {project.name}")
        
        # Get jobs
        jobs = CrawlJob.query.filter_by(project_id=project_id).order_by(CrawlJob.created_at.desc()).all()
        print(f"Total jobs: {len(jobs)}")
        
        for job in jobs:
            print(f"  Job {job.id}: status={job.status}, job_type={job.job_type}, job_number={job.job_number}")
            print(f"    created_at={job.created_at}, completed_at={job.completed_at}")
        
        # Get pages
        pages = ProjectPage.query.filter_by(project_id=project_id).all()
        print(f"Total pages: {len(pages)}")
        
        # Check pages with diffs
        pages_with_diffs = [
            page for page in pages
            if any([
                page.diff_status_desktop == 'completed',
                page.diff_status_tablet == 'completed',
                page.diff_status_mobile == 'completed'
            ])
        ]
        print(f"Pages with completed diffs: {len(pages_with_diffs)}")
        
        # Test RunStateService
        run_state_service = RunStateService()
        
        # Call the service multiple times to check for consistency
        print("\n=== TESTING RUN STATE SERVICE ===")
        for i in range(3):
            run_state = run_state_service.get_project_run_state(project_id)
            print(f"Call {i+1}: state={run_state.get('state')}, run_state={run_state.get('run_state')}")
            print(f"  Description: {run_state.get('description')}")
            print(f"  Pages total: {run_state.get('pages_total')}, done: {run_state.get('pages_done')}")
        
        # Test the internal methods directly
        print("\n=== TESTING INTERNAL METHODS ===")
        
        # Test _check_completed_states
        completed_info = run_state_service._check_completed_states(jobs, pages)
        print(f"_check_completed_states result: {completed_info}")
        
        # Test _check_active_jobs
        active_info = run_state_service._check_active_jobs(project_id, jobs)
        print(f"_check_active_jobs result: {active_info}")
        
        # Test _check_job_failures
        failure_info = run_state_service._check_job_failures(project_id, jobs)
        print(f"_check_job_failures result: {failure_info}")

def debug_all_projects():
    """Debug status for all projects"""
    print("\n=== DEBUGGING ALL PROJECTS ===")
    
    with app.app_context():
        projects = Project.query.all()
        run_state_service = RunStateService()
        
        for project in projects:
            run_state = run_state_service.get_project_run_state(project.id)
            print(f"Project {project.id} ({project.name}): {run_state.get('state')}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        project_id = int(sys.argv[1])
        debug_project_status(project_id)
    else:
        debug_all_projects()
        print("\nUsage: python debug_status_inconsistency.py <project_id>")
        print("Run with a specific project ID to get detailed debugging info")