#!/usr/bin/env python3
"""
Fix job 52 that was incorrectly marked as failed due to race condition
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fix_job_52():
    """Fix job 52 status"""
    try:
        from app import app, db
        from models.crawl_job import CrawlJob
        from models.project import ProjectPage
        
        with app.app_context():
            print("=== Fixing Job 52 ===")
            
            # Get job 52
            job = db.session.get(CrawlJob, 52)
            if not job:
                print("Job 52 not found")
                return
            
            print(f"Current status: {job.status}")
            print(f"Started at: {job.started_at}")
            print(f"Completed at: {job.completed_at}")
            print(f"Error message: {job.error_message}")
            print(f"Total pages: {job.total_pages}")
            
            # Check if pages were actually created for this project
            pages = ProjectPage.query.filter_by(project_id=job.project_id).all()
            print(f"Pages found for project {job.project_id}: {len(pages)}")
            
            if len(pages) > 0 and job.completed_at:
                # Job actually completed successfully, fix the status
                job.status = 'completed'
                job.total_pages = len(pages)
                job.error_message = None
                db.session.commit()
                print(f"✅ Fixed job 52: Status changed to 'completed' with {len(pages)} pages")
            else:
                print("❌ Job 52 appears to have genuinely failed")
            
    except Exception as e:
        print(f"Error fixing job 52: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    fix_job_52()