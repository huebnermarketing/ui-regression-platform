#!/usr/bin/env python3

import requests
import json
import sys

def test_jobs_api():
    """Test the jobs API to see what data is being returned"""
    try:
        # Make request to the jobs API
        response = requests.get('http://localhost:5001/api/projects/99/jobs')
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("JSON Response:")
                print(json.dumps(data, indent=2))
                
                # Check if jobs exist and what their data looks like
                if 'jobs' in data and data['jobs']:
                    print(f"\nFound {len(data['jobs'])} jobs")
                    for i, job in enumerate(data['jobs']):
                        print(f"\nJob {i+1}:")
                        print(f"  ID: {job.get('id')}")
                        print(f"  Status: {job.get('status')}")
                        print(f"  Duration: {job.get('duration')}")
                        print(f"  Pages: {job.get('pages')}")
                        print(f"  Updated: {job.get('updated_at')}")
                else:
                    print("No jobs found in response")
                    
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON: {e}")
                print(f"Raw response: {response.text}")
        else:
            print(f"Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    test_jobs_api()