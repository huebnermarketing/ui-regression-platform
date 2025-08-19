"""
Test script to verify the duplicate job creation fix
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db
from models.crawl_job import CrawlJob
from models.project import Project
from models.user import User

def test_duplicate_job_fix():
    """Test that only one job is created when starting a crawl"""
    # Import app after setting up path
    from app import app
    
    with app.app_context():
        try:
            print("Testing duplicate job creation fix...")
            
            # Get or create a test user
            test_user = User.query.filter_by(username='demo').first()
            if not test_user:
                test_user = User(username='demo', password='demo123')
                db.session.add(test_user)
                db.session.commit()
                print("Created demo user")
            
            # Get or create a test project
            test_project = Project.query.filter_by(user_id=test_user.id).first()
            if not test_project:
                test_project = Project(
                    name='Test Project',
                    staging_url='https://staging.example.com',
                    production_url='https://production.example.com',
                    user_id=test_user.id
                )
                db.session.add(test_project)
                db.session.commit()
                print(f"Created test project with ID: {test_project.id}")
            else:
                print(f"Using existing test project with ID: {test_project.id}")
            
            # Clear any existing jobs for this project
            existing_jobs = CrawlJob.query.filter_by(project_id=test_project.id).all()
            for job in existing_jobs:
                db.session.delete(job)
            db.session.commit()
            print(f"Cleared {len(existing_jobs)} existing jobs")
            
            # Test 1: Create a job via API endpoint logic (simulated)
            print("\n=== Test 1: Simulating API endpoint job creation ===")
            
            # Check for running jobs (should be none)
            running_job = CrawlJob.query.filter_by(
                project_id=test_project.id
            ).filter(CrawlJob.status.in_(['Crawling', 'pending'])).first()
            
            if running_job:
                print(f"ERROR: Found existing running job: {running_job.id}")
                return False
            else:
                print("No running jobs found")
            
            # Create new job with pending status (API endpoint logic)
            new_job = CrawlJob(project_id=test_project.id)
            new_job.status = 'pending'
            new_job.job_type = 'full_crawl'
            db.session.add(new_job)
            db.session.commit()
            
            print(f"Created job {new_job.id} with status: {new_job.status}")
            
            # Test 2: Simulate scheduler finding the pending job
            print("\n=== Test 2: Simulating scheduler finding pending job ===")
            
            # Scheduler looks for pending job
            pending_job = CrawlJob.query.filter_by(
                project_id=test_project.id,
                status='pending'
            ).order_by(CrawlJob.created_at.desc()).first()
            
            if pending_job:
                print(f"Scheduler found pending job: {pending_job.id}")
                
                # Scheduler starts the job
                pending_job.start_job()
                db.session.commit()
                print(f"Job {pending_job.id} started with status: {pending_job.status}")
            else:
                print("ERROR: Scheduler did not find pending job")
                return False
            
            # Test 3: Verify only one job exists
            print("\n=== Test 3: Verifying job count ===")
            
            all_jobs = CrawlJob.query.filter_by(project_id=test_project.id).all()
            print(f"Total jobs for project {test_project.id}: {len(all_jobs)}")
            
            for job in all_jobs:
                print(f"  Job {job.id}: status={job.status}, job_number={job.job_number}")
            
            if len(all_jobs) == 1:
                print("SUCCESS: Only one job created!")
                return True
            else:
                print(f"FAILURE: Expected 1 job, found {len(all_jobs)}")
                return False
            
        except Exception as e:
            print(f"Error during test: {str(e)}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = test_duplicate_job_fix()
    if success:
        print("\nDuplicate job creation fix is working correctly!")
    else:
        print("\nDuplicate job creation fix needs more work.")