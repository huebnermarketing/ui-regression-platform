from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
import logging
from datetime import datetime
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
            'max_instances': 1  # FIXED: Only allow one instance per job to prevent duplicates
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
        Schedule an immediate crawl job for a project - FIXED: Single job enforcement
        
        Args:
            project_id (int): ID of the project to crawl
        """
        job_id = f"crawl_project_{project_id}"
        
        # FIXED: Check for existing running jobs before scheduling
        from models.crawl_job import CrawlJob
        
        # Check if there's already a running or pending job for this project
        existing_job = CrawlJob.query.filter_by(
            project_id=project_id
        ).filter(CrawlJob.status.in_(['Crawling', 'pending'])).first()
        
        if existing_job:
            current_app.logger.warning(
                f"Cannot schedule crawl for project {project_id}: "
                f"Job {existing_job.job_number} is already {existing_job.status}"
            )
            return False
        
        # Check if there's already a scheduled APScheduler job
        existing_scheduler_job = self.scheduler.get_job(job_id)
        if existing_scheduler_job:
            current_app.logger.warning(
                f"Cannot schedule crawl for project {project_id}: "
                f"APScheduler job already exists"
            )
            return False
        
        # Schedule new job to run immediately with single instance enforcement
        try:
            self.scheduler.add_job(
                func=self._crawl_project_job,
                args=[project_id],
                id=job_id,
                name=f"Crawl Project {project_id}",
                misfire_grace_time=300,  # 5 minutes grace time
                replace_existing=True,   # FIXED: Replace any existing job
                max_instances=1          # FIXED: Enforce single instance per project
            )
            
            current_app.logger.info(f"Scheduled crawl job for project {project_id}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Failed to schedule crawl job for project {project_id}: {str(e)}")
            return False
    
    def _crawl_project_job(self, project_id: int):
        """
        Background job to crawl a project with proper job state management - FIXED: Single job enforcement
        
        Args:
            project_id (int): ID of the project to crawl
        """
        with self.app.app_context():
            crawl_job = None
            try:
                current_app.logger.info(f"Starting crawl job for project {project_id}")
                
                # FIXED: Double-check for running jobs before starting (race condition protection)
                from models.crawl_job import CrawlJob
                running_job = CrawlJob.query.filter_by(
                    project_id=project_id
                ).filter(CrawlJob.status.in_(['Crawling'])).first()
                
                if running_job:
                    current_app.logger.warning(
                        f"Aborting crawl job for project {project_id}: "
                        f"Job {running_job.job_number} is already running"
                    )
                    return
                
                # Get project from database
                project = Project.query.get(project_id)
                if not project:
                    current_app.logger.error(f"Project {project_id} not found")
                    return
                
                # Get the latest pending crawl job for this project
                crawl_job = CrawlJob.query.filter_by(
                    project_id=project_id,
                    status='pending'
                ).order_by(CrawlJob.created_at.desc()).first()
                
                if not crawl_job:
                    # FIXED: Don't create a new job here - jobs should only be created by the route handler
                    current_app.logger.error(
                        f"No pending crawl job found for project {project_id}. "
                        f"Jobs should be created by the route handler before scheduling."
                    )
                    return
                
                # FIXED: Use new phase transition method for atomic job start
                try:
                    crawl_job.start_job()
                    db.session.commit()
                except Exception as e:
                    current_app.logger.warning(
                        f"Could not start crawl job {crawl_job.id} for project {project_id}: {str(e)}"
                    )
                    return
                
                current_app.logger.info(f"Successfully started crawl job {crawl_job.job_number} for project {project_id}")
                
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
                
                # FIXED: Complete the job atomically (already implemented in CrawlJob.complete_job)
                success = crawl_job.complete_job(len(matched_pages))
                db.session.commit()
                
                if success:
                    current_app.logger.info(
                        f"Crawl job {crawl_job.job_number} completed for project {project_id}. "
                        f"Found {len(matched_pages)} matching pages"
                    )
                else:
                    current_app.logger.warning(
                        f"Crawl job {crawl_job.job_number} completion was idempotent for project {project_id}"
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
            finally:
                # FIXED: Ensure APScheduler job is cleaned up after completion
                job_id = f"crawl_project_{project_id}"
                try:
                    self.scheduler.remove_job(job_id)
                    current_app.logger.info(f"Cleaned up APScheduler job {job_id}")
                except:
                    pass  # Job may have already been removed
    
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
    
    def schedule_find_difference(self, project_id: int, page_ids: list = None):
        """
        Schedule a find difference job for a project (legacy method)
        
        Args:
            project_id (int): ID of the project
            page_ids (list): Optional list of page IDs to process
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
            args=[project_id, page_ids],
            id=job_id,
            name=f"Find Difference Project {project_id}",
            misfire_grace_time=300  # 5 minutes grace time
        )
        
        current_app.logger.info(f"Scheduled find difference job for project {project_id}")
    
    def schedule_find_difference_for_job(self, job_id: int, page_ids: list = None):
        """
        Schedule a find difference job for a specific CrawlJob (phase-based workflow)
        
        Args:
            job_id (int): ID of the CrawlJob to advance through phases
            page_ids (list): Optional list of page IDs to process
        """
        scheduler_job_id = f"find_difference_job_{job_id}"
        
        # Remove existing job if it exists
        try:
            self.scheduler.remove_job(scheduler_job_id)
        except:
            pass
        
        # Schedule new job to run immediately
        self.scheduler.add_job(
            func=self._find_difference_for_job,
            args=[job_id, page_ids],
            id=scheduler_job_id,
            name=f"Find Difference for Job {job_id}",
            misfire_grace_time=300  # 5 minutes grace time
        )
        
        current_app.logger.info(f"Scheduled find difference for job {job_id}")
    
    def _find_difference_job(self, project_id: int, page_ids: list = None):
        """
        Background job to find differences for a project (legacy method)
        
        Args:
            project_id (int): ID of the project
            page_ids (list): Optional list of page IDs to process
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
                
                # Run find difference for specified or all pages
                import asyncio
                successful_count, failed_count, run_id = asyncio.run(
                    find_diff_service.run_find_difference(project_id, page_ids, self)
                )
                
                current_app.logger.info(
                    f"Find difference job completed for project {project_id}. "
                    f"Successful: {successful_count}, Failed: {failed_count}, Run ID: {run_id}"
                )
                
            except Exception as e:
                current_app.logger.error(f"Error in find difference job for project {project_id}: {str(e)}")
                raise
    
    def _find_difference_for_job(self, job_id: int, page_ids: list = None):
        """
        Background job to find differences for a specific CrawlJob (phase-based workflow)
        
        Args:
            job_id (int): ID of the CrawlJob to advance through phases
            page_ids (list): Optional list of page IDs to process
        """
        with self.app.app_context():
            crawl_job = None
            try:
                current_app.logger.info(f"Starting find difference for job {job_id}")
                
                # Get the crawl job from database
                from models.crawl_job import CrawlJob
                crawl_job = CrawlJob.query.get(job_id)
                if not crawl_job:
                    current_app.logger.error(f"CrawlJob {job_id} not found")
                    return
                
                if crawl_job.status != 'finding_difference':
                    current_app.logger.error(f"CrawlJob {job_id} is not in 'finding_difference' status (current: {crawl_job.status})")
                    return
                
                # Get project from database
                project = Project.query.get(crawl_job.project_id)
                if not project:
                    current_app.logger.error(f"Project {crawl_job.project_id} not found")
                    return
                
                # Import find difference service
                from services.find_difference_service import FindDifferenceService
                find_diff_service = FindDifferenceService()
                
                # Run find difference for specified or all pages
                import asyncio
                successful_count, failed_count, run_id = asyncio.run(
                    find_diff_service.run_find_difference(crawl_job.project_id, page_ids, self)
                )
                
                # PHASE TRANSITION: Finding Difference → Ready (or diff_failed)
                if failed_count == 0:
                    crawl_job.complete_find_difference()
                    current_app.logger.info(f"CrawlJob {job_id} completed find difference phase successfully")
                else:
                    error_msg = f"Find difference completed with {failed_count} failures out of {successful_count + failed_count} pages"
                    if successful_count == 0:
                        # Complete failure
                        crawl_job.fail_find_difference(error_msg)
                        current_app.logger.error(f"CrawlJob {job_id} failed find difference phase: {error_msg}")
                    else:
                        # Partial success - still mark as ready but log the issues
                        crawl_job.complete_find_difference()
                        current_app.logger.warning(f"CrawlJob {job_id} completed find difference with partial failures: {error_msg}")
                
                db.session.commit()
                
                current_app.logger.info(
                    f"Find difference for job {job_id} completed. "
                    f"Successful: {successful_count}, Failed: {failed_count}, Run ID: {run_id}, "
                    f"Final Status: {crawl_job.status}"
                )
                
            except Exception as e:
                current_app.logger.error(f"Error in find difference for job {job_id}: {str(e)}")
                
                # PHASE TRANSITION: Finding Difference → diff_failed
                if crawl_job:
                    try:
                        crawl_job.fail_find_difference(str(e))
                        db.session.commit()
                        current_app.logger.info(f"CrawlJob {job_id} marked as diff_failed due to exception")
                    except Exception as db_error:
                        current_app.logger.error(f"Failed to update job {job_id} status to diff_failed: {str(db_error)}")
                        db.session.rollback()
                
                # Don't re-raise the exception to prevent scheduler from retrying
                # The job status has been properly set to diff_failed
                return
            finally:
                # FIXED: Ensure APScheduler job is cleaned up after completion
                scheduler_job_id = f"find_difference_job_{job_id}"
                try:
                    self.scheduler.remove_job(scheduler_job_id)
                    current_app.logger.info(f"Cleaned up APScheduler job {scheduler_job_id}")
                except:
                    pass  # Job may have already been removed