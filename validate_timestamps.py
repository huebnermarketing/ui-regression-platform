#!/usr/bin/env python3
"""
Timestamp Validation Script for PixelPulse UI Regression Platform

This script validates that all timestamps across the application
are handled consistently and correctly.
"""

import os
import sys
from datetime import datetime, timezone
import pytz

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def validate_timestamps():
    """Validate timestamp handling across the application"""
    
    print("[CHECKING] Validating timestamp handling...")
    print("=" * 50)
    
    validation_results = {
        'database_timestamps': False,
        'filter_functions': False,
        'model_methods': False,
        'service_methods': False,
        'overall_status': False
    }
    
    try:
        from app import app
        from models import db
        from models.user import User
        from models.project import Project
        from models.crawl_job import CrawlJob
        from sqlalchemy import text
        
        with app.app_context():
            # 1. Validate database timestamps
            print("1. Validating database timestamps...")
            
            # Check for NULL timestamps
            null_check = db.session.execute(text("""
                SELECT 
                    'users' as table_name, 
                    COUNT(*) as total,
                    COUNT(created_at) as with_created_at
                FROM users
                UNION ALL
                SELECT 
                    'projects' as table_name,
                    COUNT(*) as total,
                    COUNT(created_at) as with_created_at
                FROM projects
                UNION ALL
                SELECT 
                    'crawl_jobs' as table_name,
                    COUNT(*) as total,
                    COUNT(created_at) as with_created_at
                FROM crawl_jobs
            """)).fetchall()
            
            db_issues = 0
            for table, total, with_created_at in null_check:
                if total != with_created_at:
                    print(f"   [ERROR] {table}: {total - with_created_at} NULL created_at timestamps")
                    db_issues += 1
                else:
                    print(f"   [OK] {table}: All {total} records have created_at timestamps")
            
            validation_results['database_timestamps'] = db_issues == 0
            
            # 2. Validate Jinja2 filter functions
            print("\n2. Validating Jinja2 filter functions...")
            
            try:
                from app import to_ist_date, to_ist_time, to_ist_datetime, to_ist_short_datetime
                
                # Test with timezone-aware UTC datetime
                test_utc = datetime.now(timezone.utc)
                
                # Test with naive datetime
                test_naive = datetime.now()
                
                # Test filters
                filters_working = True
                
                try:
                    result = to_ist_date(test_utc)
                    print(f"   [OK] to_ist_date(UTC): {result}")
                except Exception as e:
                    print(f"   [ERROR] to_ist_date(UTC) failed: {e}")
                    filters_working = False
                
                try:
                    result = to_ist_time(test_naive)
                    print(f"   [OK] to_ist_time(naive): {result}")
                except Exception as e:
                    print(f"   [ERROR] to_ist_time(naive) failed: {e}")
                    filters_working = False
                
                try:
                    result = to_ist_datetime(None)
                    print(f"   [OK] to_ist_datetime(None): {result}")
                except Exception as e:
                    print(f"   [ERROR] to_ist_datetime(None) failed: {e}")
                    filters_working = False
                
                validation_results['filter_functions'] = filters_working
                
            except ImportError as e:
                print(f"   [ERROR] Could not import filter functions: {e}")
                validation_results['filter_functions'] = False
            
            # 3. Validate model methods
            print("\n3. Validating model timestamp methods...")
            
            model_issues = 0
            
            # Test CrawlJob timestamp methods
            try:
                test_job = CrawlJob(project_id=1)
                
                # Check if created_at is timezone-aware
                if test_job.created_at.tzinfo is None:
                    print("   [ERROR] CrawlJob.created_at is not timezone-aware")
                    model_issues += 1
                else:
                    print("   [OK] CrawlJob.created_at is timezone-aware")
                
                # Test start_job method
                test_job.start_job()
                if test_job.started_at.tzinfo is None:
                    print("   [ERROR] CrawlJob.started_at is not timezone-aware")
                    model_issues += 1
                else:
                    print("   [OK] CrawlJob.started_at is timezone-aware")
                
            except Exception as e:
                print(f"   [ERROR] CrawlJob timestamp validation failed: {e}")
                model_issues += 1
            
            validation_results['model_methods'] = model_issues == 0
            
            # 4. Check if timestamp utility exists
            print("\n4. Validating timestamp utility module...")
            
            try:
                from utils.timestamp_utils import utc_now, ist_now, to_utc, to_ist
                
                # Test utility functions
                utc_time = utc_now()
                ist_time = ist_now()
                
                if utc_time.tzinfo is None:
                    print("   [ERROR] utc_now() returns naive datetime")
                    validation_results['service_methods'] = False
                elif ist_time.tzinfo is None:
                    print("   [ERROR] ist_now() returns naive datetime")
                    validation_results['service_methods'] = False
                else:
                    print("   [OK] Timestamp utility functions working correctly")
                    print(f"      UTC: {utc_time}")
                    print(f"      IST: {ist_time}")
                    validation_results['service_methods'] = True
                
            except ImportError:
                print("   [ERROR] Timestamp utility module not found")
                validation_results['service_methods'] = False
            except Exception as e:
                print(f"   [ERROR] Timestamp utility validation failed: {e}")
                validation_results['service_methods'] = False
            
            # 5. Overall validation
            print("\n" + "=" * 50)
            print("[SUMMARY] VALIDATION SUMMARY:")
            print("=" * 50)
            
            all_passed = True
            for check, passed in validation_results.items():
                if check != 'overall_status':
                    status = "[OK] PASS" if passed else "[ERROR] FAIL"
                    print(f"{check.replace('_', ' ').title()}: {status}")
                    if not passed:
                        all_passed = False
            
            validation_results['overall_status'] = all_passed
            
            if all_passed:
                print("\n[SUCCESS] ALL TIMESTAMP VALIDATIONS PASSED!")
                print("The application timestamp handling is consistent and correct.")
            else:
                print("\n⚠️  SOME TIMESTAMP VALIDATIONS FAILED!")
                print("Please review and fix the failing components.")
            
            return validation_results
            
    except Exception as e:
        print(f"[ERROR] Validation failed: {str(e)}")
        return validation_results

if __name__ == '__main__':
    results = validate_timestamps()
    success = results.get('overall_status', False)
    sys.exit(0 if success else 1)
