"""
UI Diff Dashboard - Flask Application
A comprehensive web application for visual regression testing and website comparison.
"""

import os
import threading
import time
import asyncio
import logging
from typing import Set, List, Tuple, Optional
from urllib.parse import quote_plus, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, redirect, url_for
from flask_migrate import Migrate
from flask_login import LoginManager, login_required, current_user
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import db for Flask-Migrate compatibility
from models import db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION MANAGEMENT
# ============================================================================

class AppConfig:
    """Application configuration management."""
    
    def __init__(self, testing: bool = False):
        self.testing = testing
        self.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
        self.db_user = os.getenv('DB_USER', 'root')
        self.db_password = os.getenv('DB_PASSWORD', '')
        self.db_host = os.getenv('DB_HOST', 'localhost')
        self.db_name = os.getenv('DB_NAME', 'ui_diff_dashboard')
    
    @property
    def database_uri(self) -> str:
        """Generate database URI based on configuration."""
        if self.testing:
            return 'sqlite:///:memory:'
        
        if self.db_password:
            encoded_password = quote_plus(self.db_password)
            return f"mysql+pymysql://{self.db_user}:{encoded_password}@{self.db_host}/{self.db_name}"
        else:
            return f"mysql+pymysql://{self.db_user}@{self.db_host}/{self.db_name}"


# ============================================================================
# WEB CRAWLER IMPLEMENTATION
# ============================================================================

class WebCrawler:
    """Enhanced web crawler for discovering and analyzing web pages."""
    
    # Class constants
    EXCLUDED_DOMAINS = {
        'facebook.com', 'www.facebook.com', 'fb.com',
        'twitter.com', 'www.twitter.com', 'x.com', 'www.x.com',
        'instagram.com', 'www.instagram.com',
        'linkedin.com', 'www.linkedin.com',
        'youtube.com', 'www.youtube.com',
        'tiktok.com', 'www.tiktok.com',
        'pinterest.com', 'www.pinterest.com',
        'snapchat.com', 'www.snapchat.com',
        'whatsapp.com', 'www.whatsapp.com',
        'telegram.org', 'www.telegram.org',
        'google.com', 'www.google.com',
        'google-analytics.com', 'www.google-analytics.com',
        'googletagmanager.com', 'www.googletagmanager.com',
        'doubleclick.net', 'www.doubleclick.net',
        'amazon.com', 'www.amazon.com',
        'microsoft.com', 'www.microsoft.com',
        'apple.com', 'www.apple.com',
        'github.com', 'www.github.com',
        'stackoverflow.com', 'www.stackoverflow.com'
    }
    
    EXCLUDED_EXTENSIONS = {
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.rar', '.tar', '.gz', '.jpg', '.jpeg', '.png',
        '.gif', '.svg', '.ico', '.css', '.js', '.xml', '.json'
    }
    
    EXCLUDED_PATHS = {
        '/api/', '/admin/', '/wp-admin/', '/wp-content/', '/wp-includes/',
        '/assets/', '/static/', '/media/', '/uploads/', '/downloads/',
        '/feed/', '/rss/', '/sitemap', '/robots.txt', '/favicon.ico'
    }
    
    def __init__(self, max_pages: int = 50, delay: float = 0.3):
        """
        Initialize the web crawler.
        
        Args:
            max_pages: Maximum number of pages to crawl per domain
            delay: Delay between requests in seconds
        """
        self.max_pages = max_pages
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PixelPulse-Crawler/2.0'
        })
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL by removing query strings, fragments, and trailing slashes."""
        try:
            parsed = urlparse(url)
            path = parsed.path.rstrip('/') or '/'
            
            return urlunparse((
                parsed.scheme,
                parsed.netloc,
                path,
                '',  # params
                '',  # query
                ''   # fragment
            ))
        except Exception as e:
            logger.warning(f"Error normalizing URL {url}: {e}")
            return url
    
    def extract_path(self, url: str) -> str:
        """Extract path from URL for matching purposes."""
        try:
            parsed = urlparse(url)
            path = parsed.path.rstrip('/')
            return path if path else '/'
        except Exception as e:
            logger.warning(f"Error extracting path from URL {url}: {e}")
            return '/'
    
    def is_valid_internal_link(self, url: str, base_domain: str) -> bool:
        """
        Validate if URL is a valid internal link.
        
        Args:
            url: URL to validate
            base_domain: Base domain to compare against
            
        Returns:
            True if valid internal link, False otherwise
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www prefix for comparison
            clean_domain = domain.replace('www.', '')
            clean_base = base_domain.replace('www.', '')
            
            # Must be same domain (internal)
            if clean_domain != clean_base:
                return False
            
            # Check excluded file types
            path = parsed.path.lower()
            if any(path.endswith(ext) for ext in self.EXCLUDED_EXTENSIONS):
                return False
            
            # Check excluded paths
            if any(excluded_path in path for excluded_path in self.EXCLUDED_PATHS):
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Error validating URL {url}: {e}")
            return False
    
    def get_page_title(self, url: str) -> str:
        """
        Extract page title from a webpage.
        
        Args:
            url: URL to extract title from
            
        Returns:
            Page title or fallback text
        """
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to get title from <title> tag
            title_tag = soup.find('title')
            if title_tag and title_tag.string:
                title = title_tag.string.strip()
                if title:
                    return title
            
            # Fallback to h1 tag
            h1_tag = soup.find('h1')
            if h1_tag and h1_tag.get_text():
                title = h1_tag.get_text().strip()
                if title:
                    return title
            
            # Fallback to meta title
            meta_title = soup.find('meta', attrs={'name': 'title'})
            if meta_title and meta_title.get('content'):
                title = meta_title.get('content').strip()
                if title:
                    return title
            
            # Final fallback
            path = self.extract_path(url)
            return f"Page: {path}"
            
        except Exception as e:
            logger.error(f"Error extracting title from {url}: {e}")
            path = self.extract_path(url)
            return f"Page: {path}"
    
    def get_internal_links(self, url: str, base_domain: str) -> Set[str]:
        """
        Extract all valid internal links from a webpage.
        
        Args:
            url: URL to crawl
            base_domain: Base domain to filter internal links
            
        Returns:
            Set of valid internal URLs found
        """
        try:
            logger.info(f"Crawling: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            links = set()
            
            # Find all anchor tags with href attributes
            for link in soup.find_all('a', href=True):
                href = link['href'].strip()
                
                # Skip empty hrefs, javascript, mailto, tel links
                if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                    continue
                
                # Convert relative URLs to absolute
                absolute_url = urljoin(url, href)
                
                # Validate as internal link
                if self.is_valid_internal_link(absolute_url, base_domain):
                    normalized_url = self.normalize_url(absolute_url)
                    links.add(normalized_url)
            
            logger.info(f"Found {len(links)} internal links on {url}")
            return links
            
        except requests.RequestException as e:
            logger.error(f"Request error crawling {url}: {e}")
            return set()
        except Exception as e:
            logger.error(f"Unexpected error crawling {url}: {e}")
            return set()
    
    def crawl_domain(self, start_url: str, scheduler=None, project_id=None) -> Set[str]:
        """
        Crawl entire domain starting from the given URL.
        
        Args:
            start_url: Starting URL for crawling
            scheduler: Optional scheduler instance for job control
            project_id: Optional project ID for job control
            
        Returns:
            Set of all discovered URLs
        """
        parsed_start = urlparse(start_url)
        base_domain = parsed_start.netloc
        
        discovered_urls = set()
        urls_to_crawl = {self.normalize_url(start_url)}
        crawled_urls = set()
        
        logger.info(f"Starting domain crawl: {base_domain} (max pages: {self.max_pages})")
        
        while urls_to_crawl and len(crawled_urls) < self.max_pages:
            # Check for stop signal
            if scheduler and project_id and scheduler._should_stop(project_id):
                logger.info(f"Crawl stopped by user signal for project {project_id}")
                break
            
            # Handle pause signal
            if scheduler and project_id:
                while scheduler._should_pause(project_id):
                    logger.info(f"Crawl paused by user signal for project {project_id}")
                    time.sleep(1)
                    
                    if scheduler._should_stop(project_id):
                        logger.info(f"Crawl stopped while paused for project {project_id}")
                        return discovered_urls
            
            current_url = urls_to_crawl.pop()
            
            if current_url in crawled_urls:
                continue
                
            crawled_urls.add(current_url)
            discovered_urls.add(current_url)
            
            logger.info(f"Progress: {len(crawled_urls)}/{self.max_pages} pages crawled, "
                       f"{len(discovered_urls)} total discovered")
            
            # Get links from current page
            new_links = self.get_internal_links(current_url, base_domain)
            
            # Add new links to crawl queue
            for link in new_links:
                if link not in crawled_urls and link not in urls_to_crawl:
                    urls_to_crawl.add(link)
            
            logger.info(f"Queue size: {len(urls_to_crawl)} URLs remaining to crawl")
            
            # Respect delay between requests
            if self.delay > 0:
                time.sleep(self.delay)
        
        logger.info(f"Domain crawl completed. Found {len(discovered_urls)} URLs for {base_domain}")
        return discovered_urls
    
    def find_matching_pages(self, staging_url: str, production_url: str, 
                          scheduler=None, project_id=None) -> List[Tuple[str, str, str, str]]:
        """
        Crawl both staging and production URLs and find matching pages with titles.
        
        Args:
            staging_url: Staging environment URL
            production_url: Production environment URL
            scheduler: Optional scheduler instance for job control
            project_id: Optional project ID for job control
            
        Returns:
            List of (path, staging_full_url, production_full_url, page_title)
        """
        logger.info("Starting crawl comparison between staging and production")
        
        # Check if page-restricted crawling is enabled
        is_page_restricted = self._check_page_restriction(project_id)
        
        if is_page_restricted:
            logger.info("Page-restricted mode: Only crawling provided URLs and their subpages")
            staging_urls = self.crawl_domain(staging_url, scheduler, project_id)  # Simplified for now
            
            if scheduler and project_id and scheduler._should_stop(project_id):
                logger.info("Crawl stopped after staging environment")
                return []
            
            production_urls = self.crawl_domain(production_url, scheduler, project_id)
        else:
            logger.info("Full site mode: Crawling entire domains from root")
            staging_urls = self.crawl_domain(staging_url, scheduler, project_id)
            
            if scheduler and project_id and scheduler._should_stop(project_id):
                logger.info("Crawl stopped after staging environment")
                return []
            
            production_urls = self.crawl_domain(production_url, scheduler, project_id)
        
        if scheduler and project_id and scheduler._should_stop(project_id):
            logger.info("Crawl stopped after production environment")
            return []
        
        # Extract paths for matching
        staging_paths = {self.extract_path(url): url for url in staging_urls}
        production_paths = {self.extract_path(url): url for url in production_urls}
        
        # Find matching paths
        common_paths = set(staging_paths.keys()) & set(production_paths.keys())
        
        matched_pages = []
        logger.info("Extracting page titles...")
        
        for i, path in enumerate(sorted(common_paths), 1):
            # Check for stop signal during title extraction
            if scheduler and project_id and scheduler._should_stop(project_id):
                logger.info("Crawl stopped during title extraction")
                break
            
            staging_full_url = staging_paths[path]
            production_full_url = production_paths[path]
            
            # Extract page title from staging URL
            logger.info(f"Extracting title {i}/{len(common_paths)}: {path}")
            page_title = self.get_page_title(staging_full_url)
            
            matched_pages.append((path, staging_full_url, production_full_url, page_title))
        
        logger.info(f"Crawl found {len(matched_pages)} matching pages with titles")
        logger.info(f"Staging pages: {len(staging_urls)}, Production pages: {len(production_urls)}")
        return matched_pages
    
    def _check_page_restriction(self, project_id: Optional[int]) -> bool:
        """Check if page-restricted crawling is enabled for the project."""
        if not project_id:
            return False
        
        try:
            from models.project import Project
            from models import db
            
            project = db.session.get(Project, project_id)
            if project and hasattr(project, 'is_page_restricted'):
                return project.is_page_restricted
        except Exception as e:
            logger.error(f"Error checking page restriction setting: {e}")
        
        return False


# ============================================================================
# CRAWLER SCHEDULER
# ============================================================================

class CrawlerScheduler:
    """Enhanced crawler scheduler with job management and progress tracking."""
    
    def __init__(self, app):
        self.app = app
        self.running_jobs = {}  # Maps project_id to job info
        self.progress_info = {}  # Store progress information for each job
        self._recover_orphaned_jobs()
    
    def _recover_orphaned_jobs(self):
        """Recover jobs that were running when the application was restarted."""
        try:
            with self.app.app_context():
                from models.crawl_job import CrawlJob
                from models import db
                from datetime import datetime, timezone
                
                # Find jobs that are marked as running but not in our scheduler
                orphaned_jobs = CrawlJob.query.filter_by(status='running').all()
                
                for job in orphaned_jobs:
                    logger.info(f"Found potentially orphaned running job {job.id} for project {job.project_id}")
                    
                    # Check if job has been running for more than 30 minutes
                    if job.started_at:
                        current_time = datetime.now(timezone.utc)
                        if job.started_at.tzinfo is None:
                            job_start_time = job.started_at.replace(tzinfo=timezone.utc)
                        else:
                            job_start_time = job.started_at
                        
                        time_since_start = current_time - job_start_time
                        if time_since_start.total_seconds() > 1800:  # 30 minutes
                            logger.info(f"Job {job.id} has been running for {time_since_start}, marking as failed")
                            job.fail_job("Job interrupted by application restart (running too long)")
                            db.session.commit()
                        else:
                            logger.info(f"Job {job.id} started recently ({time_since_start} ago), leaving as running")
                    else:
                        logger.info(f"Job {job.id} has no start time, marking as failed")
                        job.fail_job("Job interrupted by application restart (no start time)")
                        db.session.commit()
                        
        except Exception as e:
            logger.error(f"Error during orphaned job recovery: {e}")
    
    def schedule_crawl(self, project_id: int) -> Optional[int]:
        """Start a crawl job in a background thread."""
        if project_id in self.running_jobs:
            return None  # Job already running
        
        # Find existing pending job or create one
        with self.app.app_context():
            from models.crawl_job import CrawlJob
            from models import db
            
            crawl_job = CrawlJob.query.filter_by(
                project_id=project_id,
                status='pending'
            ).order_by(CrawlJob.created_at.desc()).first()
            
            if not crawl_job:
                crawl_job = CrawlJob(project_id=project_id)
                db.session.add(crawl_job)
                db.session.commit()
            
            job_id = crawl_job.id
        
        # Start crawl in background thread
        thread = threading.Thread(target=self._crawl_project_job, args=[project_id, job_id])
        thread.daemon = True
        thread.start()
        
        # Store job information
        self.running_jobs[project_id] = {
            'job_id': job_id,
            'thread': thread,
            'should_stop': False,
            'should_pause': False
        }
        
        return job_id
    
    def _crawl_project_job(self, project_id: int, job_id: int):
        """Background job to crawl a project."""
        crawl_job = None
        try:
            with self.app.app_context():
                from models.crawl_job import CrawlJob
                from models.project import Project, ProjectPage
                from models import db
                
                logger.info(f"Starting crawl job {job_id} for project {project_id}")
                
                # Get crawl job from database
                crawl_job = db.session.get(CrawlJob, job_id)
                if not crawl_job:
                    logger.error(f"Crawl job {job_id} not found")
                    return
                
                # Check for stop signal before starting
                if self._should_stop(project_id):
                    crawl_job.fail_job("Job stopped by user")
                    db.session.commit()
                    return
                
                # Start the job
                crawl_job.start_job()
                db.session.commit()
                
                # Initialize progress tracking
                self.progress_info[project_id] = {
                    'stage': 'initializing',
                    'progress': 0,
                    'message': 'Initializing crawler...',
                    'job_id': job_id
                }
                
                # Get project from database
                project = db.session.get(Project, project_id)
                if not project:
                    logger.error(f"Project {project_id} not found")
                    crawl_job.fail_job("Project not found")
                    db.session.commit()
                    return
                
                # Handle pause/stop signals
                self._handle_job_control(project_id, job_id, crawl_job)
                
                # Update progress
                self.progress_info[project_id].update({
                    'stage': 'crawling',
                    'progress': 20,
                    'message': 'Starting to crawl websites...'
                })
                
                # Initialize crawler
                crawler = WebCrawler(max_pages=50, delay=0.3)
                
                # Update progress
                self.progress_info[project_id].update({
                    'stage': 'crawling',
                    'progress': 40,
                    'message': 'Discovering pages...'
                })
                
                # Find matching pages
                matched_pages = crawler.find_matching_pages(
                    project.staging_url,
                    project.production_url,
                    self,
                    project_id
                )
                
                if self._should_stop(project_id):
                    crawl_job.fail_job("Job stopped by user")
                    db.session.commit()
                    return
                
                # Update progress
                self.progress_info[project_id].update({
                    'stage': 'processing',
                    'progress': 70,
                    'message': f'Processing {len(matched_pages)} discovered pages...'
                })
                
                # Clear existing pages and save new ones
                ProjectPage.query.filter_by(project_id=project_id).delete()
                
                self.progress_info[project_id].update({
                    'stage': 'saving',
                    'progress': 80,
                    'message': 'Saving pages to database...'
                })
                
                # Save matched pages to database
                for i, (path, staging_url, production_url, page_title) in enumerate(matched_pages):
                    if self._should_stop(project_id):
                        crawl_job.fail_job("Job stopped by user")
                        db.session.commit()
                        return
                    
                    page = ProjectPage(
                        project_id=project_id,
                        path=path,
                        staging_url=staging_url,
                        production_url=production_url,
                        page_name=page_title
                    )
                    page.status = 'crawled'
                    db.session.add(page)
                    
                    # Update progress during saving
                    if i % 5 == 0:
                        progress = 80 + (i / len(matched_pages)) * 15
                        self.progress_info[project_id].update({
                            'progress': int(progress),
                            'message': f'Saved {i+1}/{len(matched_pages)} pages...'
                        })
                
                # Complete the job
                completion_success = crawl_job.complete_job(len(matched_pages))
                db.session.commit()
                
                if completion_success:
                    logger.info(f"Crawl job {job_id} completed for project {project_id}. "
                               f"Found {len(matched_pages)} matching pages")
                    
                    self.progress_info[project_id].update({
                        'stage': 'completed',
                        'progress': 100,
                        'message': f'Crawl completed! Found {len(matched_pages)} pages.'
                    })
                    
                    # Remove from running jobs after DB commit
                    if project_id in self.running_jobs:
                        del self.running_jobs[project_id]
                        logger.info(f"Removed completed job {job_id} from running jobs")
                else:
                    logger.info(f"Job {job_id} completion was idempotent - already completed")
                
        except Exception as e:
            logger.error(f"Error in crawl job {job_id} for project {project_id}: {e}")
            self.progress_info[project_id] = {
                'stage': 'error',
                'progress': 0,
                'message': f'Error: {str(e)}',
                'job_id': job_id
            }
            with self.app.app_context():
                from models import db
                if crawl_job:
                    crawl_job.fail_job(str(e))
                    db.session.commit()
                else:
                    db.session.rollback()
        finally:
            # Clean up progress info
            if project_id in self.progress_info:
                del self.progress_info[project_id]
            
            # Ensure job is removed from running_jobs
            if project_id in self.running_jobs:
                del self.running_jobs[project_id]
                logger.info(f"Cleaned up running job {job_id} for project {project_id}")
    
    def _handle_job_control(self, project_id: int, job_id: int, crawl_job):
        """Handle pause/stop signals for a job."""
        from models import db
        
        # Check for stop signal
        if self._should_stop(project_id):
            crawl_job.fail_job("Job stopped by user")
            db.session.commit()
            return
        
        # Handle pause
        while self._should_pause(project_id):
            with self.app.app_context():
                crawl_job = db.session.get(type(crawl_job), job_id)
                crawl_job.pause()
                db.session.commit()
            
            self.progress_info[project_id].update({
                'stage': 'paused',
                'message': 'Job paused by user'
            })
            time.sleep(1)
            
            if self._should_stop(project_id):
                with self.app.app_context():
                    crawl_job = db.session.get(type(crawl_job), job_id)
                    crawl_job.fail_job("Job stopped by user")
                    db.session.commit()
                return
        
        # Resume if was paused
        with self.app.app_context():
            crawl_job = db.session.get(type(crawl_job), job_id)
            if crawl_job.status == 'paused':
                crawl_job.start_job()
                db.session.commit()
    
    def get_job_status(self, project_id: int) -> dict:
        """Get the status of a crawl job."""
        if project_id in self.running_jobs:
            return {'status': 'scheduled'}
        else:
            return {'status': 'not_scheduled'}
    
    def get_progress_info(self, project_id: int) -> dict:
        """Get progress information for a crawl job."""
        return self.progress_info.get(project_id, {
            'stage': 'unknown',
            'progress': 0,
            'message': 'No progress information available'
        })
    
    def cancel_crawl(self, project_id: int) -> bool:
        """Cancel a scheduled crawl job."""
        if project_id in self.running_jobs:
            self.running_jobs[project_id]['should_stop'] = True
            
            try:
                with self.app.app_context():
                    from models.crawl_job import CrawlJob
                    from models import db
                    
                    job_id = self.running_jobs[project_id]['job_id']
                    crawl_job = db.session.get(CrawlJob, job_id)
                    if crawl_job and crawl_job.status in ['running', 'paused']:
                        crawl_job.fail_job("Job cancelled by user")
                        db.session.commit()
                        logger.info(f"Job {job_id} marked as cancelled in database")
            except Exception as e:
                logger.error(f"Error updating job status during cancellation: {e}")
            
            logger.info(f"Cancel signal sent for project {project_id}")
            return True
        return False
    
    def _should_stop(self, project_id: int) -> bool:
        """Check if job should be stopped."""
        if project_id not in self.running_jobs:
            return False
        return self.running_jobs[project_id].get('should_stop', False)
    
    def _should_pause(self, project_id: int) -> bool:
        """Check if job should be paused."""
        if project_id not in self.running_jobs:
            return False
        return self.running_jobs[project_id].get('should_pause', False)


# ============================================================================
# APPLICATION FACTORY
# ============================================================================

def create_app(testing: bool = False) -> Flask:
    """
    Create and configure the Flask application.
    
    Args:
        testing: Whether to configure for testing
        
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    config = AppConfig(testing)
    
    # Configure Flask app
    app.config['SECRET_KEY'] = config.secret_key
    app.config['TESTING'] = testing
    app.config['SQLALCHEMY_DATABASE_URI'] = config.database_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    from models import db
    db.init_app(app)
    Migrate(app, db)
    
    # Configure login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # Import models after db initialization
    from models.user import User
    from models.project import Project, ProjectPage
    from models.crawl_job import CrawlJob
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # Configure Jinja2 filters
    _configure_jinja_filters(app)
    
    # Initialize crawler scheduler BEFORE registering routes
    try:
        crawler_scheduler = CrawlerScheduler(app)
        app.crawler_scheduler = crawler_scheduler
        logger.info("Crawler scheduler initialized successfully")
    except Exception as e:
        logger.warning(f"Scheduler initialization failed: {e}")
        app.crawler_scheduler = None
    
    # Register routes AFTER scheduler is initialized
    _register_routes(app)
    
    return app


def _configure_jinja_filters(app: Flask):
    """Configure Jinja2 template filters."""
    try:
        from utils.timestamp_utils import (
            format_ist_date, format_ist_time, format_ist_datetime,
            format_ist_short_datetime
        )
        
        app.jinja_env.filters['ist_date'] = lambda dt: format_ist_date(dt)
        app.jinja_env.filters['ist_time'] = lambda dt: format_ist_time(dt)
        app.jinja_env.filters['ist_datetime'] = lambda dt: format_ist_datetime(dt)
        app.jinja_env.filters['ist_short_datetime'] = lambda dt: format_ist_short_datetime(dt)
        
        logger.info("Jinja2 filters configured successfully")
    except ImportError as e:
        logger.warning(f"Could not import timestamp utils: {e}")


def _register_routes(app: Flask):
    """Register application routes and blueprints."""
    
    # Basic health check and root routes
    @app.route("/healthz")
    def healthz():
        return "OK", 200

    @app.route("/")
    def root():
        return redirect(url_for('login'))
    
    # Register dashboard route first (needed by auth routes)
    create_dashboard_routes(app)
    
    # Register route modules with corrected module names
    route_modules = [
        ('auth.routes', 'register_routes', 'Auth routes'),
        ('projects.routes', 'register_project_routes', 'Project routes'),  # Fixed module name
        ('history.routes', 'register_history_routes', 'History routes'),  # Fixed function name
        ('routes.asset_resolver', 'register_asset_resolver_routes', 'Asset resolver routes'),  # Fixed module name
        ('routes.run_state_routes', 'register_run_state_routes', 'Run state routes'),  # Fixed module name
        ('analytics.routes', 'register_analytics_routes', 'Analytics routes'),  # Fixed function name
    ]
    
    for module_name, function_name, description in route_modules:
        try:
            module = __import__(module_name, fromlist=[function_name])
            register_func = getattr(module, function_name)
            
            # Some routes need scheduler parameter
            if 'projects' in module_name.lower() or 'run_state' in module_name.lower():
                if hasattr(app, 'crawler_scheduler') and app.crawler_scheduler:
                    register_func(app, app.crawler_scheduler)
                else:
                    logger.warning(f"{description} skipped because scheduler is None")
            else:
                register_func(app)
                
            logger.info(f"{description} registered successfully")
        except ImportError as e:
            logger.warning(f"{description} not registered - module not found: {e}")
        except AttributeError as e:
            logger.warning(f"{description} not registered - function not found: {e}")
        except Exception as e:
            logger.warning(f"{description} not registered - unexpected error: {e}")
    
    # Register blueprints
    try:
        from settings.routes import settings_bp
        app.register_blueprint(settings_bp)
        logger.info("Settings blueprint registered successfully")
    except Exception as e:
        logger.warning(f"Settings blueprint not registered: {e}")


# ============================================================================
# DASHBOARD ROUTES
# ============================================================================

def create_dashboard_routes(app: Flask):
    """Create dashboard-related routes."""
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Enhanced dashboard with KPI data and recent projects."""
        from sqlalchemy import func, desc, or_
        from models.project import Project, ProjectPage
        from models.crawl_job import CrawlJob
        from models import db
        
        # Get KPI statistics
        total_projects = Project.query.filter_by(user_id=current_user.id).count()
        
        # Get active tasks (running crawl jobs)
        active_tasks = db.session.query(CrawlJob).join(Project).filter(
            Project.user_id == current_user.id,
            CrawlJob.status.in_(['running', 'pending', 'crawling', 'finding_difference', 'paused'])
        ).count()
        
        # Get recent diffs - count pages with actual visual differences
        recent_diffs = db.session.query(ProjectPage).join(Project).filter(
            Project.user_id == current_user.id,
            ProjectPage.find_diff_status == 'completed',
            or_(
                ProjectPage.diff_mismatch_pct_desktop > 0,
                ProjectPage.diff_mismatch_pct_tablet > 0,
                ProjectPage.diff_mismatch_pct_mobile > 0
            )
        ).count()
        
        # Calculate success rate
        total_jobs = db.session.query(CrawlJob).join(Project).filter(
            Project.user_id == current_user.id,
            CrawlJob.status.in_(['completed', 'ready', 'Job Failed', 'diff_failed'])
        ).count()
        
        successful_jobs = db.session.query(CrawlJob).join(Project).filter(
            Project.user_id == current_user.id,
            CrawlJob.status.in_(['completed', 'ready'])
        ).count()
        
        success_rate = round((successful_jobs / total_jobs * 100) if total_jobs > 0 else 0, 1)
        
        # Get recent projects
        recent_projects = Project.query.filter_by(user_id=current_user.id).order_by(
            desc(Project.created_at)
        ).limit(5).all()
        
        # Get project stats for each recent project
        for project in recent_projects:
            project.page_count = ProjectPage.query.filter_by(project_id=project.id).count()
            project.last_crawl = db.session.query(CrawlJob).filter_by(
                project_id=project.id
            ).order_by(desc(CrawlJob.created_at)).first()
            
            project.diff_count = min(project.page_count, 3)  # Placeholder logic
            
            # Determine project status
            if project.last_crawl:
                status_mapping = {
                    'running': ('Active', 'success'),
                    'completed': ('Completed', 'info'),
                    'ready': ('Ready', 'info'),
                    'failed': ('Failed', 'danger'),
                    'Job Failed': ('Failed', 'danger'),
                    'diff_failed': ('Failed', 'danger'),
                }
                project.display_status, project.status_class = status_mapping.get(
                    project.last_crawl.status, ('Pending', 'warning')
                )
            else:
                project.display_status = 'Not Crawled'
                project.status_class = 'secondary'
        
        kpis = {
            'active_projects': total_projects,
            'recent_diffs': min(recent_diffs, 999),
            'success_rate': success_rate,
            'active_tasks': active_tasks
        }
        
        return render_template('dashboard.html',
                             user=current_user,
                             kpis=kpis,
                             recent_projects=recent_projects)


# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================

# Global application instance
app = None
crawler_scheduler = None


def initialize_app():
    """Initialize the global application instance."""
    global app, crawler_scheduler
    
    if app is None:
        app = create_app()
        crawler_scheduler = getattr(app, 'crawler_scheduler', None)
        
        logger.info("Application initialized successfully")
    
    return app


def create_demo_user():
    """Create a demo user if it doesn't exist."""
    try:
        from models.user import User
        from models import db
        
        if not User.query.filter_by(username='demo').first():
            demo_user = User(username='demo')
            demo_user.set_password('demo123')
            db.session.add(demo_user)
            db.session.commit()
            logger.info("Demo user created: username='demo', password='demo123'")
    except Exception as e:
        logger.error(f"Error creating demo user: {e}")


# ============================================================================
# APPLICATION ENTRY POINTS
# ============================================================================

if __name__ == '__main__':
    # Initialize application
    app = initialize_app()
    
    with app.app_context():
        from models import db
        db.create_all()
        create_demo_user()
    
    logger.info("Starting UI Diff Dashboard with MySQL...")
    logger.info("Access the application at: http://localhost:5001")
    logger.info("Demo credentials: username='demo', password='demo123'")
    
    app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False)


# For production deployment (Gunicorn entry point)
def create_production_app():
    """Create application instance for production deployment."""
    app = initialize_app()
    
    with app.app_context():
        from models import db
        try:
            db.create_all()
            create_demo_user()
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    return app


# Gunicorn entry point
application = create_production_app()
