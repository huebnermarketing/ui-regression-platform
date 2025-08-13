"""
Master rollback script to undo all recent database changes for crawl jobs
This script executes all individual rollback scripts in the correct order
"""

import os
import sys
import importlib.util
from datetime import datetime

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_and_execute_rollback(script_name, description):
    """Load and execute a rollback script"""
    print(f"\n{'='*60}")
    print(f"EXECUTING: {description}")
    print(f"Script: {script_name}")
    print(f"{'='*60}")
    
    try:
        # Get the full path to the script
        script_path = os.path.join(os.path.dirname(__file__), script_name)
        
        if not os.path.exists(script_path):
            print(f"ERROR: Script {script_name} not found at {script_path}")
            return False
        
        # Load the module
        spec = importlib.util.spec_from_file_location("rollback_module", script_path)
        rollback_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rollback_module)
        
        # Execute the main rollback function
        if hasattr(rollback_module, 'rollback_timestamped_runs'):
            success = rollback_module.rollback_timestamped_runs()
        elif hasattr(rollback_module, 'rollback_paused_status'):
            success = rollback_module.rollback_paused_status()
        elif hasattr(rollback_module, 'rollback_screenshot_fields'):
            success = rollback_module.rollback_screenshot_fields()
        elif hasattr(rollback_module, 'rollback_multi_viewport_fields'):
            success = rollback_module.rollback_multi_viewport_fields()
        elif hasattr(rollback_module, 'rollback_job_type_field'):
            success = rollback_module.rollback_job_type_field()
        elif hasattr(rollback_module, 'rollback_diff_fields'):
            success = rollback_module.rollback_diff_fields()
        elif hasattr(rollback_module, 'rollback_capture_and_diff_complete_status'):
            success = rollback_module.rollback_capture_and_diff_complete_status()
        else:
            print(f"ERROR: No rollback function found in {script_name}")
            return False
        
        if success:
            print(f"✓ SUCCESS: {description} completed successfully")
            return True
        else:
            print(f"✗ FAILED: {description} failed")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: Exception during {description}: {str(e)}")
        return False

def create_backup_info():
    """Create a backup information file"""
    backup_info = f"""
Database Rollback Information
============================
Rollback executed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This rollback undid the following database changes:
1. Timestamped runs support (current_run_id, baseline_run_id, find_diff_status, etc.)
2. Paused status from crawl_jobs ENUM
3. Screenshot fields (staging_screenshot_path, production_screenshot_path)
4. Multi-viewport fields (desktop/tablet/mobile screenshot and diff fields)
5. Job type field from crawl_jobs table
6. Diff fields (diff_image_path, diff_mismatch_pct, etc.)
7. Capture and diff complete status from project_pages ENUM

Original migration files that were rolled back:
- add_timestamped_runs.py
- add_paused_status.py
- add_screenshot_fields.py
- add_multi_viewport_fields.py / add_multi_viewport_fields_mysql.py
- add_job_type_field.py / add_job_type_field_mysql.py
- add_diff_fields.py
- add_capture_and_diff_complete_status.py

To re-apply these changes, run the original migration files in reverse order.
"""
    
    backup_file = os.path.join(os.path.dirname(__file__), 'rollback_info.txt')
    with open(backup_file, 'w') as f:
        f.write(backup_info)
    
    print(f"Backup information saved to: {backup_file}")

def main():
    """Execute all rollback scripts in the correct order"""
    print("MASTER ROLLBACK SCRIPT")
    print("=" * 80)
    print("This script will undo ALL recent database changes for crawl jobs")
    print("=" * 80)
    
    # Define rollback scripts in the correct order (reverse of migration order)
    rollback_scripts = [
        ("rollback_timestamped_runs.py", "Remove timestamped runs support"),
        ("rollback_paused_status.py", "Remove paused status from crawl_jobs"),
        ("rollback_screenshot_fields.py", "Remove screenshot fields"),
        ("rollback_multi_viewport_fields.py", "Remove multi-viewport fields"),
        ("rollback_job_type_field.py", "Remove job_type field from crawl_jobs"),
        ("rollback_diff_fields.py", "Remove diff fields"),
        ("rollback_capture_and_diff_complete_status.py", "Remove capture_and_diff_complete status"),
    ]
    
    successful_rollbacks = 0
    failed_rollbacks = 0
    
    # Execute each rollback script
    for script_name, description in rollback_scripts:
        success = load_and_execute_rollback(script_name, description)
        if success:
            successful_rollbacks += 1
        else:
            failed_rollbacks += 1
    
    # Summary
    print(f"\n{'='*80}")
    print("ROLLBACK SUMMARY")
    print(f"{'='*80}")
    print(f"Total rollback scripts: {len(rollback_scripts)}")
    print(f"Successful rollbacks: {successful_rollbacks}")
    print(f"Failed rollbacks: {failed_rollbacks}")
    
    if failed_rollbacks == 0:
        print("\n🎉 ALL ROLLBACKS COMPLETED SUCCESSFULLY!")
        print("All recent database changes for crawl jobs have been undone.")
        create_backup_info()
    else:
        print(f"\n⚠️  {failed_rollbacks} ROLLBACK(S) FAILED!")
        print("Some database changes may not have been fully undone.")
        print("Please check the error messages above and manually fix any issues.")
    
    print(f"\n{'='*80}")

if __name__ == '__main__':
    main()