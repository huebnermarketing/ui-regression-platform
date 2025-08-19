#!/usr/bin/env python3
"""
Test script to verify the history functionality fix
"""

import requests
import json
import sys

def test_history_functionality():
    """Test the history functionality with proper authentication"""
    
    base_url = "http://localhost:5001"
    project_id = 1
    
    print("Testing History Functionality Fix")
    print("=" * 50)
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    try:
        # Step 1: Test login (if needed)
        print("1. Testing authentication...")
        login_response = session.get(f"{base_url}/login")
        if login_response.status_code == 200:
            print("   [OK] Login page accessible")
        
        # Step 2: Test project page access
        print("2. Testing project page access...")
        project_response = session.get(f"{base_url}/projects/{project_id}")
        if project_response.status_code == 200:
            print("   ✓ Project page accessible")
        elif project_response.status_code == 302:
            print("   ⚠️ Redirected to login - authentication required")
            return False
        else:
            print(f"   ❌ Project page failed: {project_response.status_code}")
            return False
        
        # Step 3: Test history API endpoints
        print("3. Testing history API endpoints...")
        
        # Test runs endpoint
        runs_url = f"{base_url}/api/history/project/{project_id}/runs"
        print(f"   Testing: {runs_url}")
        
        runs_response = session.get(runs_url)
        print(f"   Response status: {runs_response.status_code}")
        
        if runs_response.status_code == 200:
            runs_data = runs_response.json()
            print(f"   ✓ Runs API successful")
            print(f"   Response: {json.dumps(runs_data, indent=2)}")
            
            if runs_data.get('success') and runs_data.get('runs'):
                print(f"   ✓ Found {len(runs_data['runs'])} runs")
                
                # Test pages endpoint with first run
                first_run = runs_data['runs'][0]
                run_id = first_run['timestamp']
                
                pages_url = f"{base_url}/api/history/project/{project_id}/run/{run_id}/pages"
                print(f"   Testing: {pages_url}")
                
                pages_response = session.get(pages_url)
                print(f"   Response status: {pages_response.status_code}")
                
                if pages_response.status_code == 200:
                    pages_data = pages_response.json()
                    print(f"   ✓ Pages API successful")
                    print(f"   Response: {json.dumps(pages_data, indent=2)}")
                    
                    if pages_data.get('success') and pages_data.get('pages'):
                        print(f"   ✓ Found {len(pages_data['pages'])} pages")
                        return True
                    else:
                        print("   ❌ No pages found in response")
                        return False
                else:
                    print(f"   ❌ Pages API failed: {pages_response.status_code}")
                    return False
            else:
                print("   ❌ No runs found in response")
                return False
        else:
            print(f"   ❌ Runs API failed: {runs_response.status_code}")
            if runs_response.status_code == 302:
                print("   ⚠️ Redirected to login - authentication issue")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

def main():
    """Main test function"""
    print("Starting history functionality test...")
    
    success = test_history_functionality()
    
    if success:
        print("\n🎉 All tests passed! History functionality is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Tests failed. History functionality needs attention.")
        sys.exit(1)

if __name__ == "__main__":
    main()