from app import app, db
from models.project import Project
from models.crawl_job import CrawlJob
from datetime import datetime, timedelta

def find_and_fix_stuck_jobs():
    """Finds and fixes jobs that are stuck in 'Crawling' or 'finding_difference' status"""
    with app.app_context():
        print("Starting check for stuck jobs...")
        
        # Get all projects
        projects = Project.query.all()
        
        for project in projects:
            # Find latest job for the project
            latest_job = CrawlJob.query.filter_by(project_id=project.id).order_by(CrawlJob.created_at.desc()).first()
            
            if latest_job and latest_job.status in ['Crawling', 'finding_difference']:
                # Check if the job has been running for more than 10 minutes
                time_since_update = datetime.utcnow() - latest_job.updated_at
                
                if time_since_update > timedelta(minutes=10):
                    print(f"Found stuck job {latest_job.id} for project {project.name} (status: {latest_job.status}).")
                    
                    # Mark job as failed
                    latest_job.status = 'Job Failed'
                    latest_job.error_message = 'Job marked as failed due to being stuck.'
                    latest_job.completed_at = datetime.utcnow()
                    
                    db.session.commit()
                    print(f"Fixed stuck job {latest_job.id}. New status: Job Failed")
        
        print("Stuck job check completed.")

if __name__ == '__main__':
    find_and_fix_stuck_jobs()