#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to reproduce the Find Difference workflow error
"""

import sys
import os
sys.path.append('.')

from flask import Flask
from models import db
from models.project import Project
from models.crawl_job import CrawlJob
from crawler.scheduler import CrawlerScheduler

def test_find_difference_import():
    """Test if we can import the FindDifferenceService"""
    try:
        from services.find_difference_service import FindDifferenceService
        print("[OK] Successfully imported FindDifferenceService")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to import FindDifferenceService: {str(e)}")
        return False

def test_find_difference_workflow():
    """Test the Find Difference workflow components"""
    
    # Test imports
    if not test_find_difference_import():
        return False
    
    try:
        # Create a minimal Flask app for testing
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Initialize database
        db.init_app(app)
        
        with app.app_context():
            # Test scheduler initialization
            scheduler = CrawlerScheduler(app)
            print("[OK] Successfully initialized CrawlerScheduler")
            
            # Test FindDifferenceService initialization
            from services.find_difference_service import FindDifferenceService
            find_diff_service = FindDifferenceService()
            print("[OK] Successfully initialized FindDifferenceService")
            
            # Test method existence
            if hasattr(find_diff_service, 'run_find_difference'):
                print("[OK] run_find_difference method exists")
            else:
                print("[ERROR] run_find_difference method missing")
                return False
            
            # Test scheduler method existence
            if hasattr(scheduler, 'schedule_find_difference_for_job'):
                print("[OK] schedule_find_difference_for_job method exists")
            else:
                print("[ERROR] schedule_find_difference_for_job method missing")
                return False
            
            print("[OK] All Find Difference workflow components are available")
            return True
            
    except Exception as e:
        print(f"[ERROR] Error testing Find Difference workflow: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_crawl_job_methods():
    """Test CrawlJob model methods"""
    try:
        from models.crawl_job import CrawlJob
        
        # Test if start_find_difference method exists
        if hasattr(CrawlJob, 'start_find_difference'):
            print("[OK] CrawlJob.start_find_difference method exists")
        else:
            print("[ERROR] CrawlJob.start_find_difference method missing")
            return False
            
        # Test if complete_find_difference method exists
        if hasattr(CrawlJob, 'complete_find_difference'):
            print("[OK] CrawlJob.complete_find_difference method exists")
        else:
            print("[ERROR] CrawlJob.complete_find_difference method missing")
            return False
            
        print("[OK] All CrawlJob methods are available")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error testing CrawlJob methods: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing Find Difference workflow components...")
    print("=" * 50)
    
    # Test individual components
    test_crawl_job_methods()
    print()
    test_find_difference_workflow()
    
    print("\nTest completed.")