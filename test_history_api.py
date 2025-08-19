#!/usr/bin/env python3
"""
Test script to debug the history API endpoint
"""

import requests
import json

def test_history_api():
    """Test the history API endpoint"""
    
    # Test with project 78 since we know it has data
    project_id = 78
    url = f"http://localhost:5001/api/history/project/{project_id}/runs"
    
    print(f"Testing URL: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Data: {json.dumps(data, indent=2)}")
            
            if data.get('success'):
                runs = data.get('runs', [])
                print(f"Number of runs found: {len(runs)}")
                for i, run in enumerate(runs):
                    print(f"  Run {i+1}: {run}")
            else:
                print(f"API returned success=False: {data.get('error', 'Unknown error')}")
        else:
            print(f"Error response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("Connection error - make sure the Flask app is running on localhost:5000")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_history_api()