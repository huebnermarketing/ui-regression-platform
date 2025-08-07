#!/usr/bin/env python3
"""
Simple test script for pause/resume/stop workflow
Tests the complete job control functionality
"""

import requests
import time
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5001"
USERNAME = "demo"
PASSWORD = "demo123"

class CrawlJobTester:
    def __init__(self):
        self.session = requests.Session()
        self.logged_in = False
        
    def login(self):
        """Login to the application"""
        print("Logging in...")
        
        # Get login page first
        login_page = self.session.get(f"{BASE_URL}/login")
        if login_page.status_code != 200:
            print(f"Failed to access login page: {login_page.status_code}")
            return False
            
        # Attempt login
        login_data = {
            'username': USERNAME,
            'password': PASSWORD
        }
        
        response = self.session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
        
        if response.status_code == 302:  # Redirect indicates successful login
            print("Login successful")
            self.logged_in = True
            return True
        else:
            print(f"Login failed: {response.status_code}")
            return False
    
    def get_crawl_queue_data(self):
        """Get crawl queue data including KPIs"""
        response = self.session.get(f"{BASE_URL}/api/crawl-jobs")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get crawl queue data: {response.status_code}")
            return None
    
    def print_kpi_stats(self):
        """Print current KPI statistics"""
        data = self.get_crawl_queue_data()
        if data:
            kpis = data.get('kpis', {})
            print("\nCurrent KPI Statistics:")
            print(f"   Queued: {kpis.get('queued', 0)}")
            print(f"   Running: {kpis.get('running', 0)}")
            print(f"   Paused: {kpis.get('paused', 0)}")
            print(f"   Completed: {kpis.get('completed', 0)}")
            print(f"   Failed: {kpis.get('failed', 0)}")
            print()
    
    def start_crawl_job(self, project_id):
        """Start a crawl job for a project"""
        print(f"Starting crawl for project {project_id}...")
        
        response = self.session.post(f"{BASE_URL}/projects/{project_id}/crawl")
        if response.status_code == 200:
            print("Crawl job started successfully")
            return True
        else:
            print(f"Failed to start crawl: {response.status_code}")
            return False
    
    def get_job_status(self, job_id):
        """Get status of a specific job"""
        response = self.session.get(f"{BASE_URL}/api/crawl-jobs/{job_id}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get job status: {response.status_code}")
            return None
    
    def pause_job(self, job_id):
        """Pause a running job"""
        print(f"Pausing job {job_id}...")
        
        response = self.session.post(f"{BASE_URL}/api/crawl-jobs/{job_id}/pause")
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("Pause signal sent successfully")
                return True
            else:
                print(f"Pause failed: {result.get('message')}")
                return False
        else:
            print(f"Failed to pause job: {response.status_code}")
            return False
    
    def resume_job(self, job_id):
        """Resume a paused job"""
        print(f"Resuming job {job_id}...")
        
        response = self.session.post(f"{BASE_URL}/api/crawl-jobs/{job_id}/start")
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("Resume signal sent successfully")
                return True
            else:
                print(f"Resume failed: {result.get('message')}")
                return False
        else:
            print(f"Failed to resume job: {response.status_code}")
            return False
    
    def stop_job(self, job_id):
        """Stop a job"""
        print(f"Stopping job {job_id}...")
        
        response = self.session.post(f"{BASE_URL}/api/crawl-jobs/{job_id}/stop")
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("Stop signal sent successfully")
                return True
            else:
                print(f"Stop failed: {result.get('message')}")
                return False
        else:
            print(f"Failed to stop job: {response.status_code}")
            return False
    
    def wait_for_status(self, job_id, expected_status, timeout=30):
        """Wait for job to reach expected status"""
        print(f"Waiting for job {job_id} to reach status '{expected_status}'...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            job_data = self.get_job_status(job_id)
            if job_data:
                current_status = job_data.get('status')
                print(f"   Current status: {current_status}")
                
                if current_status == expected_status:
                    print(f"Job reached status '{expected_status}'")
                    return True
                    
            time.sleep(2)
        
        print(f"Timeout waiting for status '{expected_status}'")
        return False
    
    def test_basic_functionality(self):
        """Test basic functionality"""
        print("Starting Basic Functionality Test")
        print("=" * 50)
        
        # Step 1: Login
        if not self.login():
            return False
        
        # Step 2: Get initial KPI stats
        print("\nInitial State:")
        self.print_kpi_stats()
        
        # Step 3: Test that we can access the crawl queue
        data = self.get_crawl_queue_data()
        if not data:
            print("Failed to get crawl queue data")
            return False
        
        jobs = data.get('all_jobs', [])
        print(f"Found {len(jobs)} total jobs")
        
        # Step 4: Check if we have any projects to work with
        project_ids = set()
        for job in jobs:
            project_ids.add(job.get('project_id'))
        
        if not project_ids:
            print("No projects found. Please create a project first.")
            return False
        
        test_project_id = list(project_ids)[0]
        print(f"Using project {test_project_id} for testing")
        
        # Step 5: Test starting a crawl
        if not self.start_crawl_job(test_project_id):
            return False
        
        # Wait for job to appear
        time.sleep(3)
        
        # Step 6: Find the new job
        data = self.get_crawl_queue_data()
        if not data:
            return False
        
        jobs = data.get('all_jobs', [])
        running_job = None
        for job in jobs:
            if job.get('project_id') == test_project_id and job.get('status') == 'running':
                running_job = job
                break
        
        if not running_job:
            print("Could not find running job")
            return False
        
        job_id = running_job['id']
        print(f"Testing with job ID: {job_id}")
        
        print("\nAfter Starting Job:")
        self.print_kpi_stats()
        
        # Step 7: Test pause
        print("Testing PAUSE functionality...")
        if not self.pause_job(job_id):
            return False
        
        # Wait for pause
        if not self.wait_for_status(job_id, 'paused', timeout=15):
            print("Job did not pause properly")
            return False
        
        print("\nAfter Pausing Job:")
        self.print_kpi_stats()
        
        # Step 8: Test resume
        print("Testing RESUME functionality...")
        if not self.resume_job(job_id):
            return False
        
        # Wait for resume
        if not self.wait_for_status(job_id, 'running', timeout=10):
            print("Job did not resume properly")
            return False
        
        print("\nAfter Resuming Job:")
        self.print_kpi_stats()
        
        # Step 9: Test stop
        print("Testing STOP functionality...")
        if not self.stop_job(job_id):
            return False
        
        # Wait for stop
        time.sleep(5)
        
        job_data = self.get_job_status(job_id)
        if job_data:
            final_status = job_data.get('status')
            error_message = job_data.get('error_message', '')
            
            print(f"   Final status: {final_status}")
            print(f"   Error message: {error_message}")
            
            if final_status == 'failed' and 'stopped by user' in error_message.lower():
                print("Job stopped correctly")
            else:
                print("Job did not stop as expected")
                return False
        
        print("\nAfter Stopping Job:")
        self.print_kpi_stats()
        
        print("\nAll tests PASSED!")
        return True

def main():
    """Main test function"""
    tester = CrawlJobTester()
    
    try:
        success = tester.test_basic_functionality()
        if success:
            print("\nALL TESTS PASSED!")
            print("Pause/Resume/Stop workflow is working correctly")
        else:
            print("\nTESTS FAILED!")
            print("Some functionality is not working correctly")
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")

if __name__ == "__main__":
    main()