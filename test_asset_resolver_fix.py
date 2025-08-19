#!/usr/bin/env python3
"""
Test Asset Resolver Fix
Test the asset resolver with actual files that exist
"""

import requests
import sys
from pathlib import Path

def test_asset_resolver():
    """Test the asset resolver with known files"""
    
    base_url = "http://localhost:5001"
    
    # Create session and login first
    session = requests.Session()
    
    # Login to get authenticated session
    login_data = {
        'username': 'demo',
        'password': 'demo123'
    }
    
    print("Logging in...")
    login_response = session.post(f"{base_url}/login", data=login_data)
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.status_code}")
        return
    
    print("Login successful!")
    
    # Test cases based on actual files we found
    test_cases = [
        {
            "name": "Project 86 Desktop Diff (current run)",
            "url": f"{base_url}/assets/runs/86/current/desktop/product-category_computing-solutions-diff.png",
            "expected": "Should find the actual diff file"
        },
        {
            "name": "Project 86 Desktop Staging (current run)", 
            "url": f"{base_url}/assets/runs/86/current/desktop/product-category_computing-solutions-staging.png",
            "expected": "Should find the actual staging file"
        },
        {
            "name": "Project 86 Desktop Production (current run)",
            "url": f"{base_url}/assets/runs/86/current/desktop/product-category_computing-solutions-production.png", 
            "expected": "Should find the actual production file"
        },
        {
            "name": "Project 75 Home Diff (current run)",
            "url": f"{base_url}/assets/runs/75/current/desktop/home-diff.png",
            "expected": "Should find the home diff file"
        },
        {
            "name": "Non-existent file",
            "url": f"{base_url}/assets/runs/999/current/desktop/nonexistent-diff.png",
            "expected": "Should return placeholder"
        }
    ]
    
    print("Testing Asset Resolver...")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   URL: {test_case['url']}")
        print(f"   Expected: {test_case['expected']}")
        
        try:
            response = session.get(test_case['url'], timeout=10)
            print(f"   Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
            print(f"   Content-Length: {len(response.content)} bytes")
            
            if response.status_code == 200:
                if response.headers.get('Content-Type', '').startswith('image/'):
                    print(f"   [SUCCESS] SUCCESS: Image served successfully")
                else:
                    print(f"   [WARNING]  WARNING: Non-image content returned")
            else:
                print(f"   [FAILED] FAILED: HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"   [FAILED] ERROR: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Asset Resolver Test Complete")

if __name__ == '__main__':
    test_asset_resolver()