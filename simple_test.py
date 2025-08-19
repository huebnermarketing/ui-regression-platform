#!/usr/bin/env python3
"""
Simple test for Jobs History feature without Unicode characters
"""

import requests
import time

def test_jobs_api():
    """Test the Jobs History API endpoints"""
    base_url = "http://localhost:5001"
    
    print("Testing Jobs History API...")
    
    # Test getting jobs for project 91 (from the logs)
    try:
        response = requests.get(f"{base_url}/api/projects/91/jobs")
        print(f"GET /api/projects/91/jobs - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {data}")
            if data.get('success'):
                jobs = data.get('jobs', [])
                print(f"Found {len(jobs)} jobs")
                for job in jobs:
                    print(f"  Job {job.get('job_number', 'N/A')}: {job.get('status', 'N/A')}")
            else:
                print(f"API returned error: {data.get('error', 'Unknown error')}")
        else:
            print(f"HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to http://localhost:5000")
        print("Make sure the Flask application is running")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Jobs History Feature - Simple Test")
    print("=" * 40)
    test_jobs_api()