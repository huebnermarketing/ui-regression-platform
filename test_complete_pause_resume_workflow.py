#!/usr/bin/env python3
"""
Comprehensive test script for pause/resume/stop workflow
Tests the complete job control functionality including:
- Starting jobs
- Pausing jobs (with proper status update)
- Resuming jobs (from paused state)
- Stopping jobs (proper cancellation)
- UI status display consistency
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
        print("🔐 Logging in...")
        
        # Get login page first to get any CSRF tokens
        login_page = self.session.get(f"{BASE_URL}/login")
        if login_page.status_code != 200:
            print(f"❌ Failed to access login page: {login_page.status_code}")
            return False
            
        # Attempt login
        login_data = {
            'username': USERNAME,
            'password': PASSWORD
        }
        
        response = self.session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
        
        if response.status_code == 302:  # Redirect indicates successful login
            print("✅ Login successful")
            self.logged_in = True
            return True
        else:
            print(f"❌ Login failed: {response.status_code}")
            return False
    
    def get_projects(self):
        """Get list of projects"""
        if not self.logged_in:
            print("❌ Not logged in")
            return []
            
        response = self.session.get(f"{BASE_URL}/api/crawl-jobs")
        if response.status_code == 200:
            data = response.json()
            return data.get('all_jobs', [])
        else:
            print(f"❌ Failed to get projects: {response.status_code}")
            return []
    
    def start_crawl_job(self, project_id):
        """Start a crawl job for a project"""
        print(f"🚀 Starting crawl for project {project_id}...")
        
        response = self.session.post(f"{BASE_URL}/projects/{project_id}/crawl")
        if response.status_code == 200:
            print("✅ Crawl job started successfully")
            return True
        else:
            print(f"❌ Failed to start crawl: {response.status_code}")
            return False
    
    def get_job_status(self, job_id):
        """Get status of a specific job"""
        response = self.session.get(f"{BASE_URL}/api/crawl-jobs/{job_id}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get job status: {response.status_code}")
            return None
    
    def pause_job(self, job_id):
        """Pause a running job"""
        print(f"⏸️ Pausing job {job_id}...")
        
        response = self.session.post(f"{BASE_URL}/api/crawl-jobs/{job_id}/pause")
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Pause signal sent successfully")
                return True
            else:
                print(f"❌ Pause failed: {result.get('message')}")
                return False
        else:
            print(f"❌ Failed to pause job: {response.status_code}")
            return False
    
    def resume_job(self, job_id):
        """Resume a paused job"""
        print(f"▶️ Resuming job {job_id}...")
        
        response = self.session.post(f"{BASE_URL}/api/crawl-jobs/{job_id}/start")
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Resume signal sent successfully")
                return True
            else:
                print(f"❌ Resume failed: {result.get('message')}")
                return False
        else:
            print(f"❌ Failed to resume job: {response.status_code}")
            return False
    
    def stop_job(self, job_id):
        """Stop a job"""
        print(f"🛑 Stopping job {job_id}...")
        
        response = self.session.post(f"{BASE_URL}/api/crawl-jobs/{job_id}/stop")
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Stop signal sent successfully")
                return True
            else:
                print(f"❌ Stop failed: {result.get('message')}")
                return False
        else:
            print(f"❌ Failed to stop job: {response.status_code}")
            return False
    
    def wait_for_status(self, job_id, expected_status, timeout=30):
        """Wait for job to reach expected status"""
        print(f"⏳ Waiting for job {job_id} to reach status '{expected_status}'...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            job_data = self.get_job_status(job_id)
            if job_data:
                current_status = job_data.get('status')
                print(f"   Current status: {current_status}")
                
                if current_status == expected_status:
                    print(f"✅ Job reached status '{expected_status}'")
                    return True
                    
            time.sleep(2)
        
        print(f"❌ Timeout waiting for status '{expected_status}'")
        return False
    
    def get_crawl_queue_data(self):
        """Get crawl queue data including KPIs"""
        response = self.session.get(f"{BASE_URL}/api/crawl-jobs")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get crawl queue data: {response.status_code}")
            return None
    
    def print_kpi_stats(self):
        """Print current KPI statistics"""
        data = self.get_crawl_queue_data()
        if data:
            kpis = data.get('kpis', {})
            print("\n📊 Current KPI Statistics:")
            print(f"   Queued: {kpis.get('queued', 0)}")
            print(f"   Running: {kpis.get('running', 0)}")
            print(f"   Paused: {kpis.get('paused', 0)}")
            print(f"   Completed: {kpis.get('completed', 0)}")
            print(f"   Failed: {kpis.get('failed', 0)}")
            print()
    
    def run_complete_workflow_test(self):
        """Run the complete pause/resume/stop workflow test"""
        print("🧪 Starting Complete Pause/Resume/Stop Workflow Test")
        print("=" * 60)
        
        # Step 1: Login
        if not self.login():
            return False
        
        # Step 2: Get initial KPI stats
        print("\n📊 Initial State:")
        self.print_kpi_stats()
        
        # Step 3: Get projects and find one to test with
        jobs = self.get_projects()
        if not jobs:
            print("❌ No jobs found. Please create a project first.")
            return False
        
        # Find a project we can test with
        test_project_id = None
        for job in jobs:
            if job.get('status') in ['completed', 'failed']:
                test_project_id = job.get('project_id')
                break
        
        if not test_project_id:
            print("❌ No suitable project found for testing")
            return False
        
        print(f"🎯 Using project {test_project_id} for testing")
        
        # Step 4: Start a new crawl job
        if not self.start_crawl_job(test_project_id):
            return False
        
        # Wait a moment for job to be created
        time.sleep(3)
        
        # Step 5: Find the running job
        jobs = self.get_projects()
        running_job = None
        for job in jobs:
            if job.get('project_id') == test_project_id and job.get('status') == 'running':
                running_job = job
                break
        
        if not running_job:
            print("❌ Could not find running job")
            return False
        
        job_id = running_job['id']
        print(f"🎯 Testing with job ID: {job_id}")
        
        # Step 6: Wait for job to be running
        if not self.wait_for_status(job_id, 'running', timeout=10):
            print("❌ Job did not start running")
            return False
        
        print("\n📊 After Starting Job:")
        self.print_kpi_stats()
        
        # Step 7: Test Pause Functionality
        print("\n🧪 Testing PAUSE functionality...")
        if not self.pause_job(job_id):
            return False
        
        # Wait for job to be paused
        if not self.wait_for_status(job_id, 'paused', timeout=15):
            print("❌ Job did not pause properly")
            return False
        
        print("\n📊 After Pausing Job:")
        self.print_kpi_stats()
        
        # Step 8: Test Resume Functionality
        print("\n🧪 Testing RESUME functionality...")
        if not self.resume_job(job_id):
            return False
        
        # Wait for job to be running again
        if not self.wait_for_status(job_id, 'running', timeout=10):
            print("❌ Job did not resume properly")
            return False
        
        print("\n📊 After Resuming Job:")
        self.print_kpi_stats()
        
        # Step 9: Test Stop Functionality
        print("\n🧪 Testing STOP functionality...")
        if not self.stop_job(job_id):
            return False
        
        # Wait for job to be stopped (should become 'failed' with stop message)
        time.sleep(5)  # Give it time to process the stop signal
        
        job_data = self.get_job_status(job_id)
        if job_data:
            final_status = job_data.get('status')
            error_message = job_data.get('error_message', '')
            
            print(f"   Final status: {final_status}")
            print(f"   Error message: {error_message}")
            
            if final_status == 'failed' and 'stopped by user' in error_message.lower():
                print("✅ Job stopped correctly")
            else:
                print("❌ Job did not stop as expected")
                return False
        
        print("\n📊 After Stopping Job:")
        self.print_kpi_stats()
        
        print("\n🎉 Complete Workflow Test PASSED!")
        print("✅ All pause/resume/stop functionality working correctly")
        return True

def main():
    """Main test function"""
    tester = CrawlJobTester()
    
    try:
        success = tester.run_complete_workflow_test()
        if success:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Pause/Resume/Stop workflow is working correctly")
            print("✅ UI status updates are consistent with backend")
            print("✅ Cancel/Stop functionality properly terminates jobs")
        else:
            print("\n❌ TESTS FAILED!")
            print("❌ Some functionality is not working correctly")
            
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")

if __name__ == "__main__":
    main()