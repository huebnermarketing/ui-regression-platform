from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
import logging
from flask import current_app
from models import db
from models.project import Project, ProjectPage
from .crawler import WebCrawler

class CrawlerScheduler:
    def __init__(self, app=None):
        self.scheduler = None
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the scheduler with Flask app"""
        self.app = app
        
        # Configure job store to use the same database
        jobstores = {
            'default': SQLAlchemyJobStore(url=app.config['SQLALCHEMY_DATABASE_URI'])
        }
        
        executors = {
            'default': ThreadPoolExecutor(20)
        }
        
        job_defaults = {
            'coalesce': False,
            'max_instances': 3
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults
        )
        
        # Setup logging
        logging.getLogger('apscheduler').setLevel(logging.INFO)
        
        # Start scheduler
        self.scheduler.start()
        
        # Register shutdown handler
        import atexit
        atexit.register(lambda: self.scheduler.shutdown())
    
    def schedule_crawl(self, project_id: int):
        """
        Schedule an immediate crawl job for a project
        
        Args:
            project_id (int): ID of the project to crawl
        """
        job_id = f"crawl_project_{project_id}"
        
        # Remove existing job if it exists
        try:
            self.scheduler.remove_job(job_id)
        except:
            pass
        
        # Schedule new job to run immediately
        self.scheduler.add_job(
            func=self._crawl_project_job,
            args=[project_id],
            id=job_id,
            name=f"Crawl Project {project_id}",
            misfire_grace_time=300  # 5 minutes grace time
        )
        
        current_app.logger.info(f"Scheduled crawl job for project {project_id}")
    
    def _crawl_project_job(self, project_id: int):
        """
        Background job to crawl a project
        
        Args:
            project_id (int): ID of the project to crawl
        """
        with self.app.app_context():
            try:
                current_app.logger.info(f"Starting crawl job for project {project_id}")
                
                # Get project from database
                project = Project.query.get(project_id)
                if not project:
                    current_app.logger.error(f"Project {project_id} not found")
                    return
                
                # Initialize crawler
                crawler = WebCrawler(max_pages=50, delay=1)
                
                # Find matching pages
                matched_pages = crawler.find_matching_pages(
                    project.staging_url,
                    project.production_url
                )
                
                # Clear existing pages for this project
                ProjectPage.query.filter_by(project_id=project_id).delete()
                
                # Save matched pages to database
                for path, staging_url, production_url in matched_pages:
                    page = ProjectPage(
                        project_id=project_id,
                        path=path,
                        staging_url=staging_url,
                        production_url=production_url
                    )
                    db.session.add(page)
                
                db.session.commit()
                
                current_app.logger.info(
                    f"Crawl job completed for project {project_id}. "
                    f"Found {len(matched_pages)} matching pages"
                )
                
            except Exception as e:
                current_app.logger.error(f"Error in crawl job for project {project_id}: {str(e)}")
                db.session.rollback()
                raise
    
    def get_job_status(self, project_id: int):
        """
        Get the status of a crawl job
        
        Args:
            project_id (int): ID of the project
            
        Returns:
            dict: Job status information
        """
        job_id = f"crawl_project_{project_id}"
        job = self.scheduler.get_job(job_id)
        
        if job is None:
            return {'status': 'not_scheduled'}
        
        return {
            'status': 'scheduled',
            'next_run_time': job.next_run_time,
            'name': job.name
        }
    
    def cancel_crawl(self, project_id: int):
        """
        Cancel a scheduled crawl job
        
        Args:
            project_id (int): ID of the project
        """
        job_id = f"crawl_project_{project_id}"
        try:
            self.scheduler.remove_job(job_id)
            current_app.logger.info(f"Cancelled crawl job for project {project_id}")
            return True
        except:
            return False