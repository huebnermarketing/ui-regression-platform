#!/usr/bin/env python3
"""
Test script for the new Jobs History feature
Tests the complete workflow from frontend to backend
"""

import requests
import json
import time
from datetime import datetime

class JobsHistoryTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.project_id = None
        
    def login(self, username="admin", password="admin"):
        """Login to the application"""
        print("🔐 Logging in...")
        
        # Get login page first to get CSRF token if needed
        login_page = self.session.get(f"{self.base_url}/login")
        
        # Attempt login
        login_data = {
            'username': username,
            'password': password
        }
        
        response = self.session.post(f"{self.base_url}/login", data=login_data)
        
        if response.status_code == 200 and "dashboard" in response.url:
            print("✅ Login successful")
            return True
        else:
            print(f"❌ Login failed: {response.status_code}")
            return False
    
    def create_test_project(self):
        """Create a test project for testing"""
        print("📁 Creating test project...")
        
        project_data = {
            'name': f'Jobs History Test Project {datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'staging_url': 'https://httpbin.org',
            'production_url': 'https://httpbin.org',
            'is_page_restricted': False
        }
        
        response = self.session.post(f"{self.base_url}/projects/add", data=project_data)
        
        if response.status_code == 200:
            # Extract project ID from redirect URL
            if "/projects/" in response.url:
                self.project_id = int(response.url.split("/projects/")[1])
                print(f"✅ Test project created with ID: {self.project_id}")
                return True
        
        print(f"❌ Failed to create test project: {response.status_code}")
        return False
    
    def test_get_jobs_history_empty(self):
        """Test getting jobs history when no jobs exist"""
        print("📋 Testing empty jobs history...")
        
        response = self.session.get(f"{self.base_url}/api/projects/{self.project_id}/jobs")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and len(data.get('jobs', [])) == 0:
                print("✅ Empty jobs history retrieved successfully")
                return True
        
        print(f"❌ Failed to get empty jobs history: {response.status_code}")
        return False
    
    def test_start_crawl_job(self):
        """Test starting a new crawl job"""
        print("🚀 Testing start crawl job...")
        
        # Generate job ID in the expected format
        job_id = datetime.now().strftime('%Y%m%d-%H%M%S')
        
        job_data = {
            'job_id': job_id
        }
        
        response = self.session.post(
            f"{self.base_url}/api/projects/{self.project_id}/start-crawl-job",
            json=job_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Crawl job started successfully with ID: {job_id}")
                return job_id
        
        print(f"❌ Failed to start crawl job: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
        return None
    
    def test_get_job_status(self, job_id):
        """Test getting job status"""
        print(f"📊 Testing job status for job: {job_id}")
        
        response = self.session.get(f"{self.base_url}/api/projects/{self.project_id}/jobs/{job_id}/status")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                job_data = data.get('job', {})
                print(f"✅ Job status retrieved: {job_data.get('status')}")
                return job_data
        
        print(f"❌ Failed to get job status: {response.status_code}")
        return None
    
    def test_jobs_history_with_job(self):
        """Test getting jobs history after creating a job"""
        print("📋 Testing jobs history with existing job...")
        
        response = self.session.get(f"{self.base_url}/api/projects/{self.project_id}/jobs")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and len(data.get('jobs', [])) > 0:
                jobs = data.get('jobs', [])
                print(f"✅ Jobs history retrieved with {len(jobs)} job(s)")
                for job in jobs:
                    print(f"   - Job {job.get('id')}: {job.get('status')}")
                return True
        
        print(f"❌ Failed to get jobs history with job: {response.status_code}")
        return False
    
    def test_project_details_page(self):
        """Test that the project details page loads with Jobs History section"""
        print("🌐 Testing project details page...")
        
        response = self.session.get(f"{self.base_url}/projects/{self.project_id}")
        
        if response.status_code == 200:
            content = response.text
            if "Jobs History" in content and "startJobBtn" in content:
                print("✅ Project details page contains Jobs History section")
                return True
        
        print(f"❌ Project details page missing Jobs History section: {response.status_code}")
        return False
    
    def cleanup_test_project(self):
        """Clean up the test project"""
        if self.project_id:
            print("🧹 Cleaning up test project...")
            response = self.session.post(f"{self.base_url}/projects/{self.project_id}/delete")
            if response.status_code == 200:
                print("✅ Test project cleaned up")
            else:
                print(f"⚠️ Failed to clean up test project: {response.status_code}")
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🧪 Starting Jobs History Feature Tests")
        print("=" * 50)
        
        try:
            # Login
            if not self.login():
                return False
            
            # Create test project
            if not self.create_test_project():
                return False
            
            # Test empty jobs history
            if not self.test_get_jobs_history_empty():
                return False
            
            # Test project details page
            if not self.test_project_details_page():
                return False
            
            # Test starting a crawl job
            job_id = self.test_start_crawl_job()
            if not job_id:
                return False
            
            # Wait a moment for job to be processed
            print("⏳ Waiting for job to be processed...")
            time.sleep(3)
            
            # Test getting job status
            job_status = self.test_get_job_status(job_id)
            if not job_status:
                return False
            
            # Test jobs history with existing job
            if not self.test_jobs_history_with_job():
                return False
            
            print("\n" + "=" * 50)
            print("🎉 All Jobs History tests passed successfully!")
            return True
            
        except Exception as e:
            print(f"\n❌ Test failed with exception: {str(e)}")
            return False
        
        finally:
            # Always cleanup
            self.cleanup_test_project()

def main():
    """Main test function"""
    print("Jobs History Feature Test Suite")
    print("Make sure the application is running on http://localhost:5000")
    print()
    
    tester = JobsHistoryTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ All tests completed successfully!")
        exit(0)
    else:
        print("\n❌ Some tests failed!")
        exit(1)

if __name__ == "__main__":
    main()