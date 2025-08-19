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
        Background job to crawl a project with proper job state management
        
        Args:
            project_id (int): ID of the project to crawl
        """
        with self.app.app_context():
            crawl_job = None
            try:
                current_app.logger.info(f"Starting crawl job for project {project_id}")
                
                # Get project from database
                project = Project.query.get(project_id)
                if not project:
                    current_app.logger.error(f"Project {project_id} not found")
                    return
                
                # Get the latest crawl job for this project
                from models.crawl_job import CrawlJob
                crawl_job = CrawlJob.query.filter_by(
                    project_id=project_id,
                    status='pending'
                ).order_by(CrawlJob.created_at.desc()).first()
                
                if not crawl_job:
                    # Create a new crawl job if none exists
                    crawl_job = CrawlJob(project_id=project_id)
                    crawl_job.job_type = 'full_crawl'
                    db.session.add(crawl_job)
                    db.session.commit()
                
                # Start the job
                crawl_job.start_job()
                db.session.commit()
                
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
                
                # Complete the job
                crawl_job.complete_job(len(matched_pages))
                db.session.commit()
                
                current_app.logger.info(
                    f"Crawl job completed for project {project_id}. "
                    f"Found {len(matched_pages)} matching pages"
                )
                
            except Exception as e:
                current_app.logger.error(f"Error in crawl job for project {project_id}: {str(e)}")
                
                # Mark job as failed if it exists
                if crawl_job:
                    crawl_job.fail_job(str(e))
                    try:
                        db.session.commit()
                    except:
                        db.session.rollback()
                else:
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
    
    def get_page_job_status(self, project_id: int, page_id: int):
        """
        Get the status of a manual page capture job
        
        Args:
            project_id (int): ID of the project
            page_id (int): ID of the page
            
        Returns:
            dict: Job status information
        """
        job_id = f"manual_capture_{project_id}_{page_id}"
        job = self.scheduler.get_job(job_id)
        
        if job is None:
            return {'status': 'not_scheduled'}
        
        return {
            'status': 'scheduled',
            'next_run_time': job.next_run_time,
            'name': job.name
        }
    
    def get_page_progress_info(self, project_id: int, page_id: int):
        """
        Get progress information for a page job
        
        Args:
            project_id (int): ID of the project
            page_id (int): ID of the page
            
        Returns:
            dict: Progress information
        """
        # For now, return basic progress info
        # This can be enhanced with more detailed progress tracking
        return {
            'stage': 'processing',
            'progress': 50,
            'message': 'Processing screenshots and differences...'
        }
    
    def schedule_manual_page_capture(self, project_id: int, page_id: int, viewports: list):
        """
        Schedule a manual page capture job
        
        Args:
            project_id (int): ID of the project
            page_id (int): ID of the page
            viewports (list): List of viewports to capture
            
        Returns:
            str: Job ID if scheduled successfully, None otherwise
        """
        job_id = f"manual_capture_{project_id}_{page_id}"
        
        # Check if job already exists
        existing_job = self.scheduler.get_job(job_id)
        if existing_job:
            return None
        
        # Schedule new job to run immediately
        try:
            self.scheduler.add_job(
                func=self._manual_page_capture_job,
                args=[project_id, page_id, viewports],
                id=job_id,
                name=f"Manual Capture Project {project_id} Page {page_id}",
                misfire_grace_time=300  # 5 minutes grace time
            )
            
            current_app.logger.info(f"Scheduled manual capture job for project {project_id}, page {page_id}")
            return job_id
        except Exception as e:
            current_app.logger.error(f"Error scheduling manual capture job: {str(e)}")
            return None
    
    def _manual_page_capture_job(self, project_id: int, page_id: int, viewports: list):
        """
        Background job for manual page capture
        
        Args:
            project_id (int): ID of the project
            page_id (int): ID of the page
            viewports (list): List of viewports to capture
        """
        with self.app.app_context():
            try:
                current_app.logger.info(f"Starting manual capture job for project {project_id}, page {page_id}")
                
                # Get page from database
                page = ProjectPage.query.filter_by(
                    id=page_id,
                    project_id=project_id
                ).first()
                
                if not page:
                    current_app.logger.error(f"Page {page_id} not found in project {project_id}")
                    return
                
                # Import screenshot service
                from screenshot.screenshot_service import ScreenshotService
                screenshot_service = ScreenshotService()
                
                # Run manual screenshot capture
                import asyncio
                successful_count, failed_count = asyncio.run(
                    screenshot_service.capture_manual_screenshots(
                        page_ids=[page_id],
                        viewports=viewports,
                        environments=['staging', 'production']
                    )
                )
                
                if successful_count > 0:
                    current_app.logger.info(
                        f"Manual capture completed for page {page_id}. "
                        f"Successful: {successful_count}, Failed: {failed_count}"
                    )
                else:
                    current_app.logger.error(
                        f"Manual capture failed for page {page_id}. "
                        f"Failed: {failed_count}"
                    )
                
            except Exception as e:
                current_app.logger.error(f"Error in manual capture job for page {page_id}: {str(e)}")
                raise
    
    def schedule_find_difference(self, project_id: int):
        """
        Schedule a find difference job for a project
        
        Args:
            project_id (int): ID of the project
        """
        job_id = f"find_difference_{project_id}"
        
        # Remove existing job if it exists
        try:
            self.scheduler.remove_job(job_id)
        except:
            pass
        
        # Schedule new job to run immediately
        self.scheduler.add_job(
            func=self._find_difference_job,
            args=[project_id],
            id=job_id,
            name=f"Find Difference Project {project_id}",
            misfire_grace_time=300  # 5 minutes grace time
        )
        
        current_app.logger.info(f"Scheduled find difference job for project {project_id}")
    
    def _find_difference_job(self, project_id: int):
        """
        Background job to find differences for a project
        
        Args:
            project_id (int): ID of the project
        """
        with self.app.app_context():
            try:
                current_app.logger.info(f"Starting find difference job for project {project_id}")
                
                # Get project from database
                project = Project.query.get(project_id)
                if not project:
                    current_app.logger.error(f"Project {project_id} not found")
                    return
                
                # Import find difference service
                from services.find_difference_service import FindDifferenceService
                find_diff_service = FindDifferenceService()
                
                # Run find difference for all pages
                import asyncio
                result = asyncio.run(find_diff_service.process_project(project_id))
                
                current_app.logger.info(
                    f"Find difference job completed for project {project_id}. "
                    f"Result: {result}"
                )
                
            except Exception as e:
                current_app.logger.error(f"Error in find difference job for project {project_id}: {str(e)}")
                raise