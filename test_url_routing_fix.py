#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify URL routing fix for diff images
Tests the serve_run_file route with the actual file structure
"""

import os
import sys
import requests
from pathlib import Path

def test_url_routing():
    """Test the URL routing fix for diff images"""
    
    print("Testing URL routing fix for diff images...")
    
    # Test URLs based on the actual file structure we found
    test_cases = [
        {
            'url': 'http://localhost:5001/runs/73/20250813-160258/diffs/mobile/home_diff.png',
            'expected_file': 'screenshots/73/20250813-160258/Mobile/home-diff.png',
            'description': 'Mobile diff image'
        },
        {
            'url': 'http://localhost:5001/runs/73/20250813-160258/diffs/desktop/home_diff.png', 
            'expected_file': 'screenshots/73/20250813-160258/Desktop/home-diff.png',
            'description': 'Desktop diff image'
        },
        {
            'url': 'http://localhost:5001/runs/73/20250813-160258/diffs/tablet/home_diff.png',
            'expected_file': 'screenshots/73/20250813-160258/Tablet/home-diff.png', 
            'description': 'Tablet diff image'
        },
        {
            'url': 'http://localhost:5001/runs/73/20250813-160258/mobile/home-staging.png',
            'expected_file': 'screenshots/73/20250813-160258/Mobile/home-staging.png',
            'description': 'Mobile staging screenshot'
        }
    ]
    
    print(f"\nChecking if expected files exist...")
    for case in test_cases:
        file_path = Path(case['expected_file'])
        exists = file_path.exists()
        print(f"  {'OK' if exists else 'MISSING'} {case['expected_file']} - {exists}")
    
    print(f"\nTesting URL routing (requires Flask app to be running)...")
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing {case['description']}")
        print(f"   URL: {case['url']}")
        print(f"   Expected file: {case['expected_file']}")
        
        try:
            # Test the URL
            response = requests.get(case['url'], timeout=10)
            
            if response.status_code == 200:
                print(f"   SUCCESS: HTTP {response.status_code}")
                print(f"   Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
                print(f"   Content-Length: {len(response.content)} bytes")
            elif response.status_code == 403:
                print(f"   AUTHENTICATION REQUIRED: HTTP {response.status_code}")
                print(f"   This is expected if not logged in - the route is working!")
            elif response.status_code == 404:
                print(f"   NOT FOUND: HTTP {response.status_code}")
                print(f"   The routing fix may need adjustment")
            else:
                print(f"   UNEXPECTED: HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"   CONNECTION ERROR: Flask app not running on localhost:5001")
            print(f"   Start the app with: python app.py")
        except Exception as e:
            print(f"   ERROR: {str(e)}")
    
    print(f"\nSummary:")
    print(f"   - Updated serve_run_file route to handle multiple file locations")
    print(f"   - Added case conversion: mobile -> Mobile, tablet -> Tablet, desktop -> Desktop")
    print(f"   - Added filename conversion: home_diff.png -> home-diff.png")
    print(f"   - Route now checks both /runs/ and /screenshots/ directories")
    print(f"   - This should make diff image URLs work dynamically for all viewports")

if __name__ == "__main__":
    test_url_routing()