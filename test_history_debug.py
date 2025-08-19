#!/usr/bin/env python3
"""
Debug script to test history functionality and identify issues
"""

import requests
import json
from datetime import datetime

def test_history_endpoints():
    """Test all history-related endpoints"""
    
    base_url = "http://localhost:5000"
    project_id = 77  # Test project
    
    print("🔍 Testing History API Endpoints")
    print("=" * 50)
    
    # Test 1: Get project runs
    print("\n1. Testing /api/history/project/{project_id}/runs")
    try:
        response = requests.get(f"{base_url}/api/history/project/{project_id}/runs")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success', False)}")
            runs = data.get('runs', [])
            print(f"Found {len(runs)} runs")
            for i, run in enumerate(runs[:3]):  # Show first 3 runs
                print(f"  Run {i+1}: {run.get('timestamp')} - {run.get('page_count')} pages")
            
            if runs:
                # Test 2: Get pages for first run
                first_run = runs[0]
                run_id = first_run.get('timestamp')
                print(f"\n2. Testing /api/history/project/{project_id}/run/{run_id}/pages")
                
                pages_response = requests.get(f"{base_url}/api/history/project/{project_id}/run/{run_id}/pages?page=1&per_page=10")
                print(f"Status Code: {pages_response.status_code}")
                
                if pages_response.status_code == 200:
                    pages_data = pages_response.json()
                    print(f"Success: {pages_data.get('success', False)}")
                    pages = pages_data.get('pages', [])
                    pagination = pages_data.get('pagination', {})
                    
                    print(f"Found {len(pages)} pages on this page")
                    print(f"Total pages: {pagination.get('total', 0)}")
                    print(f"Pagination: page {pagination.get('page', 1)} of {pagination.get('pages', 1)}")
                    
                    # Show sample page data
                    if pages:
                        sample_page = pages[0]
                        print(f"\nSample page data:")
                        print(f"  Path: {sample_page.get('path', 'N/A')}")
                        print(f"  Name: {sample_page.get('page_name', 'N/A')}")
                        print(f"  Desktop Status: {sample_page.get('diff_status_desktop', 'N/A')}")
                        print(f"  Desktop Diff %: {sample_page.get('diff_mismatch_pct_desktop', 'N/A')}")
                else:
                    print(f"Error: {pages_response.text}")
            else:
                print("❌ No runs found to test pages endpoint")
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Server is not running on localhost:5000")
        print("💡 Please start the Flask server first:")
        print("   python app.py")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return True

def test_frontend_javascript_issues():
    """Identify potential frontend JavaScript issues"""
    
    print("\n🔍 Frontend JavaScript Issue Analysis")
    print("=" * 50)
    
    issues = []
    
    # Read the template file to analyze JavaScript
    try:
        with open('templates/projects/details.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for common issues
        if 'currentProjectId' in content:
            print("✅ currentProjectId variable found")
        else:
            issues.append("❌ currentProjectId variable not found")
            
        if 'currentRunData' in content:
            print("✅ currentRunData variable found")
        else:
            issues.append("❌ currentRunData variable not found")
            
        if '/api/history/project/' in content:
            print("✅ History API endpoints found in JavaScript")
        else:
            issues.append("❌ History API endpoints not found in JavaScript")
            
        # Check for error handling
        if '.catch(error' in content:
            print("✅ Error handling found in JavaScript")
        else:
            issues.append("❌ No error handling found in JavaScript")
            
        # Check for authentication headers
        if 'credentials' in content or 'withCredentials' in content:
            print("✅ Credentials handling found")
        else:
            issues.append("⚠️  No explicit credentials handling found (may rely on cookies)")
            
    except FileNotFoundError:
        issues.append("❌ Template file not found")
    except Exception as e:
        issues.append(f"❌ Error reading template: {e}")
    
    if issues:
        print("\n🚨 Potential Issues Found:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n✅ No obvious JavaScript issues found")
    
    return len(issues) == 0

def main():
    """Main debug function"""
    print("🔧 History Functionality Debug Tool")
    print("=" * 50)
    
    # Test backend endpoints
    backend_ok = test_history_endpoints()
    
    # Test frontend JavaScript
    frontend_ok = test_frontend_javascript_issues()
    
    print("\n📋 Summary")
    print("=" * 50)
    print(f"Backend API: {'✅ OK' if backend_ok else '❌ Issues Found'}")
    print(f"Frontend JS: {'✅ OK' if frontend_ok else '❌ Issues Found'}")
    
    if not backend_ok:
        print("\n💡 Next Steps:")
        print("1. Start the Flask server: python app.py")
        print("2. Re-run this debug script")
        print("3. Check server logs for any errors")
    
    if backend_ok and not frontend_ok:
        print("\n💡 Next Steps:")
        print("1. Check browser console for JavaScript errors")
        print("2. Verify authentication/session cookies")
        print("3. Add more error logging to frontend")

if __name__ == "__main__":
    main()