#!/usr/bin/env python3
"""
Test script to verify status consistency between different service calls
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db
from models.project import Project, ProjectPage
from models.crawl_job import CrawlJob
from services.run_state_service import RunStateService
from datetime import datetime

def test_status_consistency():
    """Test status consistency between single and multiple project calls"""
    
    with app.app_context():
        # Get all projects
        projects = Project.query.all()
        if not projects:
            print("No projects found")
            return
        
        print(f"Testing status consistency for {len(projects)} projects")
        
        # Initialize service
        run_state_service = RunStateService()
        
        # Test each project individually
        print("\n=== INDIVIDUAL PROJECT CALLS ===")
        individual_results = {}
        for project in projects:
            result = run_state_service.get_project_run_state(project.id)
            individual_results[project.id] = result
            print(f"Project {project.id} ({project.name}): {result.get('state')}")
        
        # Test multiple projects call
        print("\n=== MULTIPLE PROJECTS CALL ===")
        project_ids = [p.id for p in projects]
        multiple_results = run_state_service.get_multiple_projects_run_state(project_ids)
        
        for project_id, result in multiple_results.items():
            project = next((p for p in projects if p.id == project_id), None)
            project_name = project.name if project else "Unknown"
            print(f"Project {project_id} ({project_name}): {result.get('state')}")
        
        # Compare results
        print("\n=== CONSISTENCY CHECK ===")
        inconsistencies = []
        for project_id in project_ids:
            individual_state = individual_results[project_id].get('state')
            multiple_state = multiple_results[project_id].get('state')
            
            if individual_state != multiple_state:
                project = next((p for p in projects if p.id == project_id), None)
                project_name = project.name if project else "Unknown"
                inconsistencies.append({
                    'project_id': project_id,
                    'project_name': project_name,
                    'individual': individual_state,
                    'multiple': multiple_state
                })
                print(f"[X] INCONSISTENCY: Project {project_id} ({project_name})")
                print(f"   Individual call: {individual_state}")
                print(f"   Multiple call: {multiple_state}")
            else:
                project = next((p for p in projects if p.id == project_id), None)
                project_name = project.name if project else "Unknown"
                print(f"[OK] CONSISTENT: Project {project_id} ({project_name}): {individual_state}")
        
        if inconsistencies:
            print(f"\n[X] Found {len(inconsistencies)} inconsistencies!")
            return False
        else:
            print(f"\n[OK] All {len(projects)} projects are consistent!")
            return True

def test_repeated_calls():
    """Test if repeated calls to the same project return consistent results"""
    
    with app.app_context():
        projects = Project.query.all()
        if not projects:
            print("No projects found")
            return
        
        # Test the first project with multiple calls
        test_project = projects[0]
        print(f"\n=== TESTING REPEATED CALLS FOR PROJECT {test_project.id} ({test_project.name}) ===")
        
        run_state_service = RunStateService()
        
        results = []
        for i in range(5):
            result = run_state_service.get_project_run_state(test_project.id)
            state = result.get('state')
            results.append(state)
            print(f"Call {i+1}: {state}")
        
        # Check if all results are the same
        if len(set(results)) == 1:
            print(f"[OK] All repeated calls returned consistent result: {results[0]}")
            return True
        else:
            print(f"[X] Repeated calls returned different results: {set(results)}")
            return False

if __name__ == "__main__":
    print("Testing status consistency...")
    
    consistency_ok = test_status_consistency()
    repeated_ok = test_repeated_calls()
    
    if consistency_ok and repeated_ok:
        print("\n[SUCCESS] All tests passed! Status calculation is consistent.")
    else:
        print("\n[WARNING] Some tests failed. There may be consistency issues.")