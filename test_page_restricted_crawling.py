#!/usr/bin/env python3
"""
Test script to debug page-restricted crawling logic
"""

from urllib.parse import urlparse

def extract_path(url: str) -> str:
    """Extract path from URL for matching purposes"""
    parsed = urlparse(url)
    path = parsed.path.rstrip('/')
    return path if path else '/'

def is_subpage_of(child_path: str, parent_path: str) -> bool:
    """
    Check if a path is a subpage of another path
    
    Args:
        child_path (str): Path to check
        parent_path (str): Parent path to compare against
        
    Returns:
        bool: True if child_path is a subpage of parent_path
    """
    # Normalize paths
    child_path = child_path.rstrip('/') if child_path != '/' else '/'
    parent_path = parent_path.rstrip('/') if parent_path != '/' else '/'
    
    # Root path includes everything
    if parent_path == '/':
        return True
    
    # Exact match
    if child_path == parent_path:
        return True
    
    # Check if child path starts with parent path followed by '/'
    return child_path.startswith(parent_path + '/')

def test_page_restricted_logic():
    """Test the page-restricted crawling logic with various scenarios"""
    
    print("=== Testing Page-Restricted Crawling Logic ===\n")
    
    # Test scenarios
    test_cases = [
        # (start_url, discovered_links, expected_results)
        {
            'name': 'Root path crawling',
            'start_url': 'https://example.com/',
            'discovered_links': [
                'https://example.com/',
                'https://example.com/about',
                'https://example.com/contact',
                'https://example.com/products',
                'https://example.com/products/item1',
                'https://example.com/blog',
                'https://example.com/blog/post1'
            ],
            'should_include_all': True
        },
        {
            'name': 'Specific page crawling (/products)',
            'start_url': 'https://example.com/products',
            'discovered_links': [
                'https://example.com/',
                'https://example.com/about',
                'https://example.com/contact',
                'https://example.com/products',
                'https://example.com/products/item1',
                'https://example.com/products/item2',
                'https://example.com/products/category/electronics',
                'https://example.com/blog',
                'https://example.com/blog/post1'
            ],
            'expected_included': [
                'https://example.com/products',
                'https://example.com/products/item1',
                'https://example.com/products/item2',
                'https://example.com/products/category/electronics'
            ]
        },
        {
            'name': 'Deep page crawling (/blog/category)',
            'start_url': 'https://example.com/blog/category',
            'discovered_links': [
                'https://example.com/',
                'https://example.com/blog',
                'https://example.com/blog/category',
                'https://example.com/blog/category/tech',
                'https://example.com/blog/category/news',
                'https://example.com/blog/post1',
                'https://example.com/products'
            ],
            'expected_included': [
                'https://example.com/blog/category',
                'https://example.com/blog/category/tech',
                'https://example.com/blog/category/news'
            ]
        }
    ]
    
    for test_case in test_cases:
        print(f"Test: {test_case['name']}")
        print(f"Start URL: {test_case['start_url']}")
        
        # Extract start path
        start_path = extract_path(test_case['start_url'])
        print(f"Start path: '{start_path}'")
        
        # Test each discovered link
        included_links = []
        excluded_links = []
        
        for link in test_case['discovered_links']:
            link_path = extract_path(link)
            if is_subpage_of(link_path, start_path):
                included_links.append(link)
                print(f"  ✓ INCLUDED: {link} (path: '{link_path}')")
            else:
                excluded_links.append(link)
                print(f"  ✗ EXCLUDED: {link} (path: '{link_path}')")
        
        # Check results
        if 'should_include_all' in test_case and test_case['should_include_all']:
            if len(included_links) == len(test_case['discovered_links']):
                print("  ✅ PASS: All links included as expected")
            else:
                print("  ❌ FAIL: Not all links included")
        elif 'expected_included' in test_case:
            expected_set = set(test_case['expected_included'])
            actual_set = set(included_links)
            if expected_set == actual_set:
                print("  ✅ PASS: Correct links included")
            else:
                print("  ❌ FAIL: Incorrect links included")
                print(f"    Expected: {expected_set}")
                print(f"    Actual: {actual_set}")
                print(f"    Missing: {expected_set - actual_set}")
                print(f"    Extra: {actual_set - expected_set}")
        
        print(f"  Summary: {len(included_links)} included, {len(excluded_links)} excluded")
        print()

if __name__ == '__main__':
    test_page_restricted_logic()