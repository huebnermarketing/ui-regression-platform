#!/usr/bin/env python3
"""
Test script to verify web interface button functionality
Creates a running job and tests pause/stop buttons through web interface
"""

import time
import requests
import threading
from app import app, crawler_scheduler
from models.crawl_job import CrawlJob
from models.project import Project
from models import db

def test_web_interface_buttons():
    """Test the web interface button functionality"""
    print("Testing web interface button functionality...")
    
    with app.app_context():
        # Get a project to test with
        project = Project.query.first()
        if not project:
            print("No projects found. Please create a project first.")
            return
        
        print(f"Using project: {project.name} (ID: {project.id})")
        
        # Start a new crawl job
        print("Starting new crawl job...")
        job_id = crawler_scheduler.schedule_crawl(project.id)
        print(f"Started job ID: {job_id}")
        
        # Wait a moment for job to start
        time.sleep(2)
        
        # Check job status in database
        job = CrawlJob.query.get(job_id)
        print(f"Job status in database: {job.status}")
        
        # Check scheduler state
        print(f"Scheduler running jobs: {len(crawler_scheduler.running_jobs)}")
        for project_id, job_info in crawler_scheduler.running_jobs.items():
            print(f"  Project {project_id}: Job {job_info['job_id']} - Thread alive: {job_info['thread'].is_alive()}")
        
        # Test API endpoints
        base_url = "http://localhost:5001"
        
        print("\nTesting API endpoints...")
        
        # Test pause endpoint
        print(f"Testing PAUSE API for job {job_id}...")
        try:
            response = requests.post(f"{base_url}/api/crawl-jobs/{job_id}/pause", 
                                   headers={'Content-Type': 'application/json'})
            print(f"Pause API response: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"Pause API error: {e}")
        
        # Wait a moment
        time.sleep(1)
        
        # Test stop endpoint
        print(f"Testing STOP API for job {job_id}...")
        try:
            response = requests.post(f"{base_url}/api/crawl-jobs/{job_id}/stop", 
                                   headers={'Content-Type': 'application/json'})
            print(f"Stop API response: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"Stop API error: {e}")
        
        # Wait for job to process signals
        print("\nWaiting 5 seconds for job to process signals...")
        time.sleep(5)
        
        # Check final status
        job = CrawlJob.query.get(job_id)
        print(f"Final job status: {job.status}, Error: {job.error_message}")
        
        # Check scheduler state
        print(f"Final scheduler running jobs: {len(crawler_scheduler.running_jobs)}")

if __name__ == "__main__":
    test_web_interface_buttons()