from flask import Flask, render_template, redirect, url_for
from flask_migrate import Migrate
from flask_login import LoginManager, login_required, current_user
from dotenv import load_dotenv
import os
from datetime import datetime
import pytz

# Load environment variables
load_dotenv()

# Initialize Flask app
from models.user import User
from models.project import Project, ProjectPage
from models.crawl_job import CrawlJob

def create_app(testing=False):
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['TESTING'] = testing

    # Build database URI properly handling empty password and special characters
    if testing:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    else:
        from urllib.parse import quote_plus

        db_user = os.getenv('DB_USER', 'root')
        db_password = os.getenv('DB_PASSWORD', '')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_name = os.getenv('DB_NAME', 'ui_diff_dashboard')

        if db_password:
            # URL encode the password to handle special characters like @
            encoded_password = quote_plus(db_password)
            app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}/{db_name}"
        else:
            app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}@{db_host}/{db_name}"

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    from models import db
    db.init_app(app)
    migrate = Migrate(app, db)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'

    # Import models after db initialization

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Import timestamp utilities for consistent handling
    from utils.timestamp_utils import (
        format_ist_date, format_ist_time, format_ist_datetime,
        format_ist_short_datetime, utc_now
    )

    # Custom Jinja2 filters for IST datetime formatting using timestamp utilities
    def to_ist_date(dt):
        """Convert datetime to IST and format as DD/MM/YYYY"""
        return format_ist_date(dt)

    def to_ist_time(dt):
        """Convert datetime to IST and format as HH:MM AM/PM"""
        return format_ist_time(dt)

    def to_ist_datetime(dt):
        """Convert datetime to IST and format as DD/MM/YYYY HH:MM AM/PM"""
        return format_ist_datetime(dt)

    def to_ist_short_datetime(dt):
        """Convert datetime to IST and format as DD/MM HH:MM AM/PM (short format)"""
        return format_ist_short_datetime(dt)

    # Register the filters with Jinja2
    app.jinja_env.filters['ist_date'] = to_ist_date
    app.jinja_env.filters['ist_time'] = to_ist_time
    app.jinja_env.filters['ist_datetime'] = to_ist_datetime
    app.jinja_env.filters['ist_short_datetime'] = to_ist_short_datetime
    return app

app = create_app()
# Initialize crawler scheduler (working version)
import threading
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
from typing import Set, List, Tuple
from crawler.crawler import WebCrawler

class EnhancedWebCrawler:
    def __init__(self, max_pages=50, delay=0.3):
        """
        Enhanced web crawler with better depth coverage and external link filtering
        
        Args:
            max_pages (int): Maximum number of pages to crawl per domain (limited to 50 for testing)
            delay (float): Delay between requests in seconds (reduced for faster crawling)
        """
        self.max_pages = max_pages
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PixelPulse-Crawler/2.0'
        })
        
        # External domains to exclude (social media, analytics, etc.)
        self.excluded_domains = {
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
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL by removing query strings, fragments, and trailing slashes"""
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        if not path:
            path = '/'
        
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            path,
            '',  # params
            '',  # query
            ''   # fragment
        ))
        return normalized
    
    def extract_path(self, url: str) -> str:
        """Extract path from URL for matching purposes"""
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        return path if path else '/'
    
    def is_valid_internal_link(self, url: str, base_domain: str) -> bool:
        """
        Enhanced validation for internal links with better external filtering
        
        Args:
            url (str): URL to validate
            base_domain (str): Base domain to compare against
            
        Returns:
            bool: True if valid internal link, False otherwise
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
            
            # Exclude specific file types that aren't web pages
            path = parsed.path.lower()
            excluded_extensions = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                                 '.zip', '.rar', '.tar', '.gz', '.jpg', '.jpeg', '.png',
                                 '.gif', '.svg', '.ico', '.css', '.js', '.xml', '.json'}
            
            if any(path.endswith(ext) for ext in excluded_extensions):
                return False
            
            # Exclude common non-page paths
            excluded_paths = {'/api/', '/admin/', '/wp-admin/', '/wp-content/', '/wp-includes/',
                            '/assets/', '/static/', '/media/', '/uploads/', '/downloads/',
                            '/feed/', '/rss/', '/sitemap', '/robots.txt', '/favicon.ico'}
            
            if any(excluded_path in path for excluded_path in excluded_paths):
                return False
            
            return True
            
        except Exception:
            return False
    
    def get_page_title(self, url: str) -> str:
        """
        Extract page title from a webpage
        
        Args:
            url (str): URL to extract title from
            
        Returns:
            str: Page title or fallback text
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
            print(f"Error extracting title from {url}: {str(e)}")
            path = self.extract_path(url)
            return f"Page: {path}"

    def get_internal_links(self, url: str, base_domain: str) -> Set[str]:
        """
        Extract all valid internal links from a webpage with enhanced filtering
        
        Args:
            url (str): URL to crawl
            base_domain (str): Base domain to filter internal links
            
        Returns:
            Set[str]: Set of valid internal URLs found
        """
        try:
            print(f"Crawling: {url}")
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
            
            print(f"Found {len(links)} internal links on {url}")
            return links
            
        except requests.RequestException as e:
            print(f"Error crawling {url}: {str(e)}")
            return set()
        except Exception as e:
            print(f"Unexpected error crawling {url}: {str(e)}")
            return set()
    
    def crawl_domain(self, start_url: str, scheduler=None, project_id=None) -> Set[str]:
        """
        Enhanced domain crawling with better depth coverage and job control
        
        Args:
            start_url (str): Starting URL for crawling
            scheduler: Optional scheduler instance for job control
            project_id: Optional project ID for job control
            
        Returns:
            Set[str]: Set of all discovered URLs
        """
        parsed_start = urlparse(start_url)
        base_domain = parsed_start.netloc
        
        discovered_urls = set()
        urls_to_crawl = {self.normalize_url(start_url)}
        crawled_urls = set()
        
        print(f"Starting enhanced crawl of domain: {base_domain}")
        print(f"Max pages to crawl: {self.max_pages} (limited for testing)")
        
        while urls_to_crawl and len(crawled_urls) < self.max_pages:
            # Check for stop signal
            if scheduler and project_id and scheduler._should_stop(project_id):
                print(f"Crawl stopped by user signal for project {project_id}")
                break
            
            # Handle pause signal
            if scheduler and project_id:
                while scheduler._should_pause(project_id):
                    print(f"Crawl paused by user signal for project {project_id}")
                    time.sleep(1)  # Check every second
                    
                    # Check for stop while paused
                    if scheduler._should_stop(project_id):
                        print(f"Crawl stopped while paused for project {project_id}")
                        return discovered_urls
            
            current_url = urls_to_crawl.pop()
            
            if current_url in crawled_urls:
                continue
                
            crawled_urls.add(current_url)
            discovered_urls.add(current_url)
            
            print(f"Progress: {len(crawled_urls)}/{self.max_pages} pages crawled, {len(discovered_urls)} total discovered")
            
            # Get links from current page
            new_links = self.get_internal_links(current_url, base_domain)
            
            # Add new links to crawl queue
            for link in new_links:
                if link not in crawled_urls and link not in urls_to_crawl:
                    urls_to_crawl.add(link)
            
            print(f"Queue size: {len(urls_to_crawl)} URLs remaining to crawl")
            
            # Respect delay between requests
            if self.delay > 0:
                time.sleep(self.delay)
        
        print(f"Enhanced crawl completed. Found {len(discovered_urls)} URLs for {base_domain}")
        return discovered_urls
    
    def crawl_page_restricted(self, start_url: str, scheduler=None, project_id=None) -> Set[str]:
        """
        Page-restricted crawling: Only crawl the specific page and its nested subpages
        
        Args:
            start_url (str): Starting URL for crawling
            scheduler: Optional scheduler instance for job control
            project_id: Optional project ID for job control
            
        Returns:
            Set[str]: Set of discovered URLs (limited to the page and its subpages)
        """
        parsed_start = urlparse(start_url)
        base_domain = parsed_start.netloc
        start_path = parsed_start.path.rstrip('/')
        if not start_path:
            start_path = '/'
        
        discovered_urls = set()
        urls_to_crawl = {self.normalize_url(start_url)}
        crawled_urls = set()
        
        print(f"Starting page-restricted crawl from: {start_url}")
        print(f"Base path restriction: {start_path}")
        print(f"Max pages to crawl: {self.max_pages} (limited for testing)")
        
        while urls_to_crawl and len(crawled_urls) < self.max_pages:
            # Check for stop signal
            if scheduler and project_id and scheduler._should_stop(project_id):
                print(f"Page-restricted crawl stopped by user signal for project {project_id}")
                break
            
            # Handle pause signal
            if scheduler and project_id:
                while scheduler._should_pause(project_id):
                    print(f"Page-restricted crawl paused by user signal for project {project_id}")
                    time.sleep(1)  # Check every second
                    
                    # Check for stop while paused
                    if scheduler._should_stop(project_id):
                        print(f"Page-restricted crawl stopped while paused for project {project_id}")
                        return discovered_urls
            
            current_url = urls_to_crawl.pop()
            
            if current_url in crawled_urls:
                continue
                
            crawled_urls.add(current_url)
            discovered_urls.add(current_url)
            
            print(f"Page-restricted progress: {len(crawled_urls)}/{self.max_pages} pages crawled, {len(discovered_urls)} total discovered")
            
            # Get links from current page
            new_links = self.get_internal_links(current_url, base_domain)
            
            # Filter links to only include subpages of the starting path
            for link in new_links:
                if link not in crawled_urls and link not in urls_to_crawl:
                    link_path = self.extract_path(link)
                    
                    # Only include URLs that are subpages of the starting path
                    if self.is_subpage_of(link_path, start_path):
                        urls_to_crawl.add(link)
                        print(f"Added subpage to queue: {link_path}")
                    else:
                        print(f"Skipped non-subpage: {link_path} (not under {start_path})")
            
            print(f"Page-restricted queue size: {len(urls_to_crawl)} URLs remaining to crawl")
            
            # Respect delay between requests
            if self.delay > 0:
                time.sleep(self.delay)
        
        print(f"Page-restricted crawl completed. Found {len(discovered_urls)} URLs under {start_path}")
        return discovered_urls
    
    def is_subpage_of(self, child_path: str, parent_path: str) -> bool:
        """
        Check if a path is a subpage of another path
        
        Args:
            child_path (str): Path to check
            parent_path (str): Parent path to compare against
            
        Returns:
            bool: True if child_path is a subpage of parent_path
        """
        # Normalize paths
        child_path = child_path.rstrip('/') if child_path != '/' else '/'
        parent_path = parent_path.rstrip('/') if parent_path != '/' else '/'
        
        # Root path includes everything
        if parent_path == '/':
            return True
        
        # Exact match
        if child_path == parent_path:
            return True
        
        # Check if child path starts with parent path followed by '/'
        return child_path.startswith(parent_path + '/')
    
    def find_matching_pages(self, staging_url: str, production_url: str, scheduler=None, project_id=None) -> List[Tuple[str, str, str, str]]:
        """
        Crawl both staging and production URLs and find matching pages with titles
        
        Args:
            staging_url (str): Staging environment URL
            production_url (str): Production environment URL
            scheduler: Optional scheduler instance for job control
            project_id: Optional project ID for job control
            
        Returns:
            List[Tuple[str, str, str, str]]: List of (path, staging_full_url, production_full_url, page_title)
        """
        print(f"Starting enhanced crawl comparison between staging and production")
        
        # Check if page-restricted crawling is enabled for this project
        is_page_restricted = False
        if project_id:
            try:
                from models.project import Project
                project = db.session.get(Project, project_id)
                if project and hasattr(project, 'is_page_restricted'):
                    is_page_restricted = project.is_page_restricted
                    print(f"Page-restricted crawling: {'ENABLED' if is_page_restricted else 'DISABLED'}")
            except Exception as e:
                print(f"Error checking page restriction setting: {e}")
        
        if is_page_restricted:
            # Page-restricted mode: Only crawl the specific provided URLs
            print("Page-restricted mode: Only crawling provided URLs and their subpages")
            staging_urls = self.crawl_page_restricted(staging_url, scheduler, project_id)
            
            # Check for stop signal after staging crawl
            if scheduler and project_id and scheduler._should_stop(project_id):
                print("Crawl stopped after staging environment")
                return []
            
            production_urls = self.crawl_page_restricted(production_url, scheduler, project_id)
        else:
            # Full site mode: Crawl entire domains (existing behavior)
            print("Full site mode: Crawling entire domains from root")
            staging_urls = self.crawl_domain(staging_url, scheduler, project_id)
            
            # Check for stop signal after staging crawl
            if scheduler and project_id and scheduler._should_stop(project_id):
                print("Crawl stopped after staging environment")
                return []
            
            production_urls = self.crawl_domain(production_url, scheduler, project_id)
        
        # Check for stop signal after production crawl
        if scheduler and project_id and scheduler._should_stop(project_id):
            print("Crawl stopped after production environment")
            return []
        
        # Extract paths for matching
        staging_paths = {self.extract_path(url): url for url in staging_urls}
        production_paths = {self.extract_path(url): url for url in production_urls}
        
        # Find matching paths
        common_paths = set(staging_paths.keys()) & set(production_paths.keys())
        
        matched_pages = []
        print("Extracting page titles...")
        
        for i, path in enumerate(sorted(common_paths), 1):  # Sort for consistent ordering
            # Check for stop signal during title extraction
            if scheduler and project_id and scheduler._should_stop(project_id):
                print("Crawl stopped during title extraction")
                break
            
            staging_full_url = staging_paths[path]
            production_full_url = production_paths[path]
            
            # Extract page title from staging URL (prefer staging for title)
            print(f"Extracting title {i}/{len(common_paths)}: {path}")
            page_title = self.get_page_title(staging_full_url)
            
            matched_pages.append((path, staging_full_url, production_full_url, page_title))
        
        print(f"Enhanced crawl found {len(matched_pages)} matching pages with titles")
        print(f"Staging pages: {len(staging_urls)}, Production pages: {len(production_urls)}")
        return matched_pages

class WorkingCrawlerScheduler:
    def __init__(self, app):
        self.app = app
        self.running_jobs = {}  # Maps project_id to {'job_id': int, 'thread': Thread, 'should_stop': bool, 'should_pause': bool}
        self.progress_info = {}  # Store progress information for each job
        self._recover_orphaned_jobs()
    
    def _recover_orphaned_jobs(self):
        """Recover jobs that were running when the application was restarted"""
        try:
            with self.app.app_context():
                from models.crawl_job import CrawlJob
                from sqlalchemy.exc import ProgrammingError

                # Find jobs that are marked as running but not in our scheduler
                orphaned_jobs = CrawlJob.query.filter_by(status='running').all()
                
                for job in orphaned_jobs:
                    print(f"Found potentially orphaned running job {job.id} for project {job.project_id}")
                    
                    # Check if job has been running for more than 30 minutes (likely truly orphaned)
                    from datetime import datetime, timezone
                    if job.started_at:
                        # Ensure both datetimes are timezone-aware for comparison
                        current_time = datetime.now(timezone.utc)
                        if job.started_at.tzinfo is None:
                            # If job.started_at is naive, assume it's UTC
                            job_start_time = job.started_at.replace(tzinfo=timezone.utc)
                        else:
                            job_start_time = job.started_at
                        time_since_start = current_time - job_start_time
                        if time_since_start.total_seconds() > 1800:  # 30 minutes
                            print(f"Job {job.id} has been running for {time_since_start}, marking as failed")
                            job.fail_job("Job interrupted by application restart (running too long)")
                            db.session.commit()
                            print(f"Marked truly orphaned job {job.id} as failed")
                        else:
                            print(f"Job {job.id} started recently ({time_since_start} ago), leaving as running")
                            # Job started recently, might still be running in background - leave it alone
                            # The orphan cleanup in crawl_queue routes will handle it if it's truly stuck
                    else:
                        # No start time, definitely orphaned
                        print(f"Job {job.id} has no start time, marking as failed")
                        job.fail_job("Job interrupted by application restart (no start time)")
                        db.session.commit()
                        print(f"Marked orphaned job {job.id} as failed")
        except ProgrammingError:
            # This can happen if the database is not yet initialized (e.g., during tests)
            print("Could not recover orphaned jobs: Database not initialized.")
        except Exception as e:
            print(f"An unexpected error occurred during orphaned job recovery: {e}")
    
    def schedule_crawl(self, project_id):
        """Start a crawl job in a background thread"""
        if project_id in self.running_jobs:
            return None  # Job already running
        
        # Find existing pending job or create one if none exists
        with self.app.app_context():
            # Look for existing pending job first
            crawl_job = CrawlJob.query.filter_by(
                project_id=project_id,
                status='pending'
            ).order_by(CrawlJob.created_at.desc()).first()
            
            if not crawl_job:
                # No pending job found, create a new one
                crawl_job = CrawlJob(project_id=project_id)
                db.session.add(crawl_job)
                db.session.commit()
            
            job_id = crawl_job.id
        
        # Start crawl in background thread
        thread = threading.Thread(target=self._crawl_project_job, args=[project_id, job_id])
        thread.daemon = True
        thread.start()
        
        # Store job information with control flags
        self.running_jobs[project_id] = {
            'job_id': job_id,
            'thread': thread,
            'should_stop': False,
            'should_pause': False
        }
        
        return job_id
    
    def _crawl_project_job(self, project_id, job_id):
        """Enhanced background job to crawl a project with better coverage and progress tracking"""
        crawl_job = None
        try:
            with self.app.app_context():
                print(f"Starting enhanced crawl job {job_id} for project {project_id}")
                
                # Get crawl job from database
                crawl_job = db.session.get(CrawlJob, job_id)
                if not crawl_job:
                    print(f"Crawl job {job_id} not found")
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
                    print(f"Project {project_id} not found")
                    crawl_job.fail_job("Project not found")
                    db.session.commit()
                    return
                
                # Check for stop/pause signals
                if self._should_stop(project_id):
                    crawl_job.fail_job("Job stopped by user")
                    db.session.commit()
                    return
                
                # Handle pause
                while self._should_pause(project_id):
                    with self.app.app_context():
                        crawl_job = db.session.get(CrawlJob, job_id)
                        crawl_job.pause()
                        db.session.commit()
                    
                    self.progress_info[project_id].update({
                        'stage': 'paused',
                        'message': 'Job paused by user'
                    })
                    time.sleep(1)  # Check every second
                    
                    if self._should_stop(project_id):
                        with self.app.app_context():
                            crawl_job = db.session.get(CrawlJob, job_id)
                            crawl_job.fail_job("Job stopped by user")
                            db.session.commit()
                        return
                
                # Resume if was paused
                with self.app.app_context():
                    crawl_job = db.session.get(CrawlJob, job_id)
                    if crawl_job.status == 'paused':
                        crawl_job.start_job()
                        db.session.commit()
                
                # Update progress
                self.progress_info[project_id].update({
                    'stage': 'crawling',
                    'progress': 10,
                    'message': 'Starting to crawl websites...'
                })
                
                # Check for stop signal
                if self._should_stop(project_id):
                    crawl_job.fail_job("Job stopped by user")
                    db.session.commit()
                    return
                
                # Initialize enhanced crawler with limited pages for testing
                crawler = EnhancedWebCrawler(max_pages=50, delay=0.3)
                
                # Update progress
                self.progress_info[project_id].update({
                    'stage': 'crawling',
                    'progress': 20,
                    'message': 'Discovering pages...'
                })
                
                # Check for stop signal
                if self._should_stop(project_id):
                    crawl_job.fail_job("Job stopped by user")
                    db.session.commit()
                    return
                
                # Find matching pages with enhanced crawler and job control
                matched_pages = crawler.find_matching_pages(
                    project.staging_url,
                    project.production_url,
                    self,  # Pass scheduler instance
                    project_id  # Pass project_id for job control
                )
                
                # Check for stop signal
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
                
                # Clear existing pages for this project
                ProjectPage.query.filter_by(project_id=project_id).delete()
                
                # Update progress
                self.progress_info[project_id].update({
                    'stage': 'saving',
                    'progress': 80,
                    'message': 'Saving pages to database...'
                })
                
                # Save matched pages to database with page titles
                for i, (path, staging_url, production_url, page_title) in enumerate(matched_pages):
                    # Check for stop signal during saving
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
                    page.status = 'crawled'  # Mark as crawled
                    db.session.add(page)
                    
                    # Update progress during saving
                    if i % 5 == 0:  # Update every 5 pages
                        progress = 80 + (i / len(matched_pages)) * 15
                        self.progress_info[project_id].update({
                            'progress': int(progress),
                            'message': f'Saved {i+1}/{len(matched_pages)} pages...'
                        })
                
                # Complete the job ATOMICALLY - DB first, then remove from running jobs
                completion_success = crawl_job.complete_job(len(matched_pages))
                db.session.commit()
                
                if completion_success:
                    print(f"Enhanced crawl job {job_id} completed for project {project_id}. Found {len(matched_pages)} matching pages")
                    
                    # Final progress update
                    self.progress_info[project_id].update({
                        'stage': 'completed',
                        'progress': 100,
                        'message': f'Crawl completed! Found {len(matched_pages)} pages.'
                    })
                    
                    # CRITICAL: Remove from running jobs AFTER DB commit
                    # This prevents race conditions where cleanup sees job not in running_jobs
                    # but DB status hasn't been updated yet
                    if project_id in self.running_jobs:
                        del self.running_jobs[project_id]
                        print(f"Removed completed job {job_id} from running jobs for project {project_id}")
                else:
                    print(f"Job {job_id} completion was idempotent - already completed")
                
        except Exception as e:
            print(f"Error in enhanced crawl job {job_id} for project {project_id}: {str(e)}")
            self.progress_info[project_id] = {
                'stage': 'error',
                'progress': 0,
                'message': f'Error: {str(e)}',
                'job_id': job_id
            }
            with self.app.app_context():
                if crawl_job:
                    crawl_job.fail_job(str(e))
                    db.session.commit()
                else:
                    db.session.rollback()
        finally:
            # Clean up progress info only - running_jobs cleanup is handled in completion logic
            if project_id in self.progress_info:
                del self.progress_info[project_id]
            
            # Ensure job is removed from running_jobs in case of failure/exception
            if project_id in self.running_jobs:
                del self.running_jobs[project_id]
                print(f"Cleaned up running job {job_id} for project {project_id} (failure/exception case)")
    
    def get_job_status(self, project_id):
        """Get the status of a crawl job"""
        if project_id in self.running_jobs:
            return {'status': 'scheduled'}
        else:
            return {'status': 'not_scheduled'}
    
    def get_progress_info(self, project_id):
        """Get progress information for a crawl job"""
        return self.progress_info.get(project_id, {
            'stage': 'unknown',
            'progress': 0,
            'message': 'No progress information available'
        })
    
    def cancel_crawl(self, project_id):
        """Cancel a scheduled crawl job by setting stop signal and updating database"""
        if project_id in self.running_jobs:
            # Set stop signal so the crawl thread will terminate
            self.running_jobs[project_id]['should_stop'] = True
            
            # Immediately update database status
            try:
                with self.app.app_context():
                    job_id = self.running_jobs[project_id]['job_id']
                    crawl_job = db.session.get(CrawlJob, job_id)
                    if crawl_job and crawl_job.status in ['running', 'paused']:
                        crawl_job.fail_job("Job cancelled by user")
                        db.session.commit()
                        print(f"Job {job_id} marked as cancelled in database")
            except Exception as e:
                print(f"Error updating job status during cancellation: {e}")
            
            print(f"Cancel signal sent for project {project_id}")
            return True
        return False
    
    def _should_stop(self, project_id):
        """Check if job should be stopped"""
        if project_id not in self.running_jobs:
            return False
        return self.running_jobs[project_id].get('should_stop', False)
    
    def _should_pause(self, project_id):
        """Check if job should be paused"""
        if project_id not in self.running_jobs:
            return False
        return self.running_jobs[project_id].get('should_pause', False)
    
    def start_job(self, job_id):
        """Start or resume a job and update database status"""
        # Find project_id by job_id
        project_id = None
        for pid, job_info in self.running_jobs.items():
            if job_info['job_id'] == job_id:
                project_id = pid
                break
        
        if project_id:
            self.running_jobs[project_id]['should_pause'] = False
            self.running_jobs[project_id]['should_stop'] = False
            
            # Update database status to running
            try:
                with self.app.app_context():
                    crawl_job = db.session.get(CrawlJob, job_id)
                    if crawl_job and crawl_job.status in ['paused', 'pending']:
                        crawl_job.start_job()
                        db.session.commit()
                        print(f"Job {job_id} marked as running in database")
            except Exception as e:
                print(f"Error updating job status during start/resume: {e}")
            
            return True
        
        return False
    
    def pause_job(self, job_id):
        """Pause a running job and update database status"""
        # Find project_id by job_id
        project_id = None
        for pid, job_info in self.running_jobs.items():
            if job_info['job_id'] == job_id:
                project_id = pid
                break
        
        if project_id:
            self.running_jobs[project_id]['should_pause'] = True
            
            # Immediately update database status to paused
            try:
                with self.app.app_context():
                    crawl_job = db.session.get(CrawlJob, job_id)
                    if crawl_job and crawl_job.status == 'running':
                        crawl_job.pause()
                        db.session.commit()
                        print(f"Job {job_id} marked as paused in database")
            except Exception as e:
                print(f"Error updating job status during pause: {e}")
            
            return True
        
        return False
    
    def stop_job(self, job_id):
        """Stop a running job and update database status"""
        # Find project_id by job_id
        project_id = None
        for pid, job_info in self.running_jobs.items():
            if job_info['job_id'] == job_id:
                project_id = pid
                break
        
        if project_id:
            self.running_jobs[project_id]['should_stop'] = True
            
            # Immediately update database status
            try:
                with self.app.app_context():
                    crawl_job = db.session.get(CrawlJob, job_id)
                    if crawl_job and crawl_job.status in ['running', 'paused']:
                        crawl_job.fail_job("Job stopped by user")
                        db.session.commit()
                        print(f"Job {job_id} marked as stopped in database")
            except Exception as e:
                print(f"Error updating job status during stop: {e}")
            
            return True
        
        return False
    
    def schedule_screenshot_capture(self, project_id):
        """Start a screenshot capture job in a background thread"""
        if project_id in self.running_jobs:
            return  # Job already running
        
        # Create crawl job record for screenshot capture
        with self.app.app_context():
            crawl_job = CrawlJob(project_id=project_id)
            crawl_job.job_type = 'screenshot'  # We'll need to add this field
            db.session.add(crawl_job)
            db.session.commit()
            job_id = crawl_job.id
        
        # Start screenshot capture in background thread
        thread = threading.Thread(target=self._screenshot_capture_job, args=[project_id, job_id])
        thread.daemon = True
        thread.start()
        
        # Store job information with control flags
        self.running_jobs[project_id] = {
            'job_id': job_id,
            'thread': thread,
            'should_stop': False,
            'should_pause': False,
            'job_type': 'screenshot'
        }
        
        return job_id
    
    def _screenshot_capture_job(self, project_id, job_id):
        """Background job to capture screenshots for a project"""
        crawl_job = None
        try:
            with self.app.app_context():
                print(f"Starting screenshot capture job {job_id} for project {project_id}")
                
                # Get crawl job from database
                crawl_job = db.session.get(CrawlJob, job_id)
                if not crawl_job:
                    print(f"Screenshot job {job_id} not found")
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
                    'message': 'Initializing screenshot capture...',
                    'job_id': job_id,
                    'job_type': 'screenshot'
                }
                
                # Get project from database
                project = db.session.get(Project, project_id)
                if not project:
                    print(f"Project {project_id} not found")
                    crawl_job.fail_job("Project not found")
                    db.session.commit()
                    return
                
                # Check for stop/pause signals
                if self._should_stop(project_id):
                    crawl_job.fail_job("Job stopped by user")
                    db.session.commit()
                    return
                
                # Handle pause
                while self._should_pause(project_id):
                    with self.app.app_context():
                        crawl_job = db.session.get(CrawlJob, job_id)
                        crawl_job.pause()
                        db.session.commit()
                    
                    self.progress_info[project_id].update({
                        'stage': 'paused',
                        'message': 'Screenshot capture paused by user'
                    })
                    time.sleep(1)  # Check every second
                    
                    if self._should_stop(project_id):
                        with self.app.app_context():
                            crawl_job = db.session.get(CrawlJob, job_id)
                            crawl_job.fail_job("Job stopped by user")
                            db.session.commit()
                        return
                
                # Resume if was paused
                with self.app.app_context():
                    crawl_job = db.session.get(CrawlJob, job_id)
                    if crawl_job.status == 'paused':
                        crawl_job.start_job()
                        db.session.commit()
                
                # Update progress
                self.progress_info[project_id].update({
                    'stage': 'capturing',
                    'progress': 10,
                    'message': 'Starting screenshot capture...'
                })
                
                # Check for stop signal
                if self._should_stop(project_id):
                    crawl_job.fail_job("Job stopped by user")
                    db.session.commit()
                    return
                
                # Initialize screenshot service
                from screenshot.screenshot_service import ScreenshotService
                screenshot_service = ScreenshotService()
                
                # Update progress
                self.progress_info[project_id].update({
                    'stage': 'capturing',
                    'progress': 20,
                    'message': 'Capturing screenshots...'
                })
                
                # Check for stop signal
                if self._should_stop(project_id):
                    crawl_job.fail_job("Job stopped by user")
                    db.session.commit()
                    return
                
                # Capture screenshots with job control
                successful_count, failed_count = screenshot_service.run_capture_project_screenshots(
                    project_id, self  # Pass scheduler instance for job control
                )
                
                # Check for stop signal
                if self._should_stop(project_id):
                    crawl_job.fail_job("Job stopped by user")
                    db.session.commit()
                    return
                
                # Update progress
                total_processed = successful_count + failed_count
                self.progress_info[project_id].update({
                    'stage': 'completed',
                    'progress': 100,
                    'message': f'Screenshot capture completed! Successful: {successful_count}, Failed: {failed_count}'
                })
                
                # Complete the job
                crawl_job.complete_job(total_processed)
                db.session.commit()
                
                print(f"Screenshot capture job {job_id} completed for project {project_id}. Successful: {successful_count}, Failed: {failed_count}")
                
        except Exception as e:
            print(f"Error in screenshot capture job {job_id} for project {project_id}: {str(e)}")
            self.progress_info[project_id] = {
                'stage': 'error',
                'progress': 0,
                'message': f'Error: {str(e)}',
                'job_id': job_id,
                'job_type': 'screenshot'
            }
            with self.app.app_context():
                if crawl_job:
                    crawl_job.fail_job(str(e))
                    db.session.commit()
                else:
                    db.session.rollback()
        finally:
            # Remove from running jobs after job completion with proper delay
            def cleanup():
                time.sleep(5)  # Wait 5 seconds before cleanup to avoid race conditions
                if project_id in self.running_jobs:
                    del self.running_jobs[project_id]
                    print(f"Removed screenshot job {job_id} from running jobs for project {project_id}")
                if project_id in self.progress_info:
                    del self.progress_info[project_id]
            
            cleanup_thread = threading.Thread(target=cleanup)
            cleanup_thread.daemon = True
            cleanup_thread.start()
    
    def schedule_diff_generation(self, project_id):
        """Start a diff generation job in a background thread"""
        if project_id in self.running_jobs:
            return  # Job already running
        
        # Create crawl job record for diff generation
        with self.app.app_context():
            crawl_job = CrawlJob(project_id=project_id)
            crawl_job.job_type = 'diff'
            db.session.add(crawl_job)
            db.session.commit()
            job_id = crawl_job.id
        
        # Start diff generation in background thread
        thread = threading.Thread(target=self._diff_generation_job, args=[project_id, job_id])
        thread.daemon = True
        thread.start()
        
        # Store job information with control flags
        self.running_jobs[project_id] = {
            'job_id': job_id,
            'thread': thread,
            'should_stop': False,
            'should_pause': False,
            'job_type': 'diff'
        }
        
        return job_id
    
    def _diff_generation_job(self, project_id, job_id):
        """Background job to generate visual diffs for a project"""
        crawl_job = None
        try:
            with self.app.app_context():
                print(f"Starting diff generation job {job_id} for project {project_id}")
                
                # Get crawl job from database
                crawl_job = db.session.get(CrawlJob, job_id)
                if not crawl_job:
                    print(f"Diff job {job_id} not found")
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
                    'message': 'Initializing diff generation...',
                    'job_id': job_id,
                    'job_type': 'diff'
                }
                
                # Get project from database
                project = db.session.get(Project, project_id)
                if not project:
                    print(f"Project {project_id} not found")
                    crawl_job.fail_job("Project not found")
                    db.session.commit()
                    return
                
                # Check for stop/pause signals
                if self._should_stop(project_id):
                    crawl_job.fail_job("Job stopped by user")
                    db.session.commit()
                    return
                
                # Handle pause
                while self._should_pause(project_id):
                    with self.app.app_context():
                        crawl_job = db.session.get(CrawlJob, job_id)
                        crawl_job.pause()
                        db.session.commit()
                    
                    self.progress_info[project_id].update({
                        'stage': 'paused',
                        'message': 'Diff generation paused by user'
                    })
                    time.sleep(1)  # Check every second
                    
                    if self._should_stop(project_id):
                        with self.app.app_context():
                            crawl_job = db.session.get(CrawlJob, job_id)
                            crawl_job.fail_job("Job stopped by user")
                            db.session.commit()
                        return
                
                # Resume if was paused
                with self.app.app_context():
                    crawl_job = db.session.get(CrawlJob, job_id)
                    if crawl_job.status == 'paused':
                        crawl_job.start_job()
                        db.session.commit()
                
                # Update progress
                self.progress_info[project_id].update({
                    'stage': 'processing',
                    'progress': 10,
                    'message': 'Starting diff generation...'
                })
                
                # Check for stop signal
                if self._should_stop(project_id):
                    crawl_job.fail_job("Job stopped by user")
                    db.session.commit()
                    return
                
                # Initialize diff engine
                from diff.diff_engine import DiffEngine
                diff_engine = DiffEngine()
                
                # Update progress
                self.progress_info[project_id].update({
                    'stage': 'processing',
                    'progress': 20,
                    'message': 'Generating visual diffs...'
                })
                
                # Check for stop signal
                if self._should_stop(project_id):
                    crawl_job.fail_job("Job stopped by user")
                    db.session.commit()
                    return
                
                # Generate diffs with job control
                successful_count, failed_count = diff_engine.run_generate_project_diffs(
                    project_id, self  # Pass scheduler instance for job control
                )
                
                # Check for stop signal
                if self._should_stop(project_id):
                    crawl_job.fail_job("Job stopped by user")
                    db.session.commit()
                    return
                
                # Update progress
                total_processed = successful_count + failed_count
                self.progress_info[project_id].update({
                    'stage': 'completed',
                    'progress': 100,
                    'message': f'Diff generation completed! Successful: {successful_count}, Failed: {failed_count}'
                })
                
                # Complete the job
                crawl_job.complete_job(total_processed)
                db.session.commit()
                
                print(f"Diff generation job {job_id} completed for project {project_id}. Successful: {successful_count}, Failed: {failed_count}")
                
        except Exception as e:
            print(f"Error in diff generation job {job_id} for project {project_id}: {str(e)}")
            self.progress_info[project_id] = {
                'stage': 'error',
                'progress': 0,
                'message': f'Error: {str(e)}',
                'job_id': job_id,
                'job_type': 'diff'
            }
            with self.app.app_context():
                if crawl_job:
                    crawl_job.fail_job(str(e))
                    db.session.commit()
                else:
                    db.session.rollback()
        finally:
            # Remove from running jobs after job completion with proper delay
            def cleanup():
                time.sleep(5)  # Wait 5 seconds before cleanup to avoid race conditions
                if project_id in self.running_jobs:
                    del self.running_jobs[project_id]
                    print(f"Removed diff job {job_id} from running jobs for project {project_id}")
                if project_id in self.progress_info:
                    del self.progress_info[project_id]
            
            cleanup_thread = threading.Thread(target=cleanup)
            cleanup_thread.daemon = True
            cleanup_thread.start()
    
    def schedule_find_difference(self, project_id):
        """Start a unified Find Difference job in a background thread"""
        if project_id in self.running_jobs:
            return  # Job already running
        
        # Create crawl job record for Find Difference
        with self.app.app_context():
            crawl_job = CrawlJob(project_id=project_id)
            crawl_job.job_type = 'find_difference'
            db.session.add(crawl_job)
            db.session.commit()
            job_id = crawl_job.id
        
        # Start Find Difference in background thread
        thread = threading.Thread(target=self._find_difference_job, args=[project_id, job_id])
        thread.daemon = True
        thread.start()
        
        # Store job information with control flags
        self.running_jobs[project_id] = {
            'job_id': job_id,
            'thread': thread,
            'should_stop': False,
            'should_pause': False,
            'job_type': 'find_difference'
        }
        
        return job_id
    
    def _find_difference_job(self, project_id, job_id):
        """Background job to run the unified Find Difference workflow"""
        crawl_job = None
        try:
            with self.app.app_context():
                print(f"Starting Find Difference job {job_id} for project {project_id}")
                
                # Get crawl job from database
                crawl_job = db.session.get(CrawlJob, job_id)
                if not crawl_job:
                    print(f"Find Difference job {job_id} not found")
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
                    'message': 'Initializing Find Difference workflow...',
                    'job_id': job_id,
                    'job_type': 'find_difference'
                }
                
                # Get project from database
                project = db.session.get(Project, project_id)
                if not project:
                    print(f"Project {project_id} not found")
                    crawl_job.fail_job("Project not found")
                    db.session.commit()
                    return
                
                # Check for stop/pause signals
                if self._should_stop(project_id):
                    crawl_job.fail_job("Job stopped by user")
                    db.session.commit()
                    return
                
                # Handle pause
                while self._should_pause(project_id):
                    with self.app.app_context():
                        crawl_job = db.session.get(CrawlJob, job_id)
                        crawl_job.pause()
                        db.session.commit()
                    
                    self.progress_info[project_id].update({
                        'stage': 'paused',
                        'message': 'Find Difference paused by user'
                    })
                    time.sleep(1)  # Check every second
                    
                    if self._should_stop(project_id):
                        with self.app.app_context():
                            crawl_job = db.session.get(CrawlJob, job_id)
                            crawl_job.fail_job("Job stopped by user")
                            db.session.commit()
                        return
                
                # Resume if was paused
                with self.app.app_context():
                    crawl_job = db.session.get(CrawlJob, job_id)
                    if crawl_job.status == 'paused':
                        crawl_job.start_job()
                        db.session.commit()
                
                # Update progress
                self.progress_info[project_id].update({
                    'stage': 'processing',
                    'progress': 10,
                    'message': 'Starting Find Difference workflow...'
                })
                
                # Check for stop signal
                if self._should_stop(project_id):
                    crawl_job.fail_job("Job stopped by user")
                    db.session.commit()
                    return
                
                # Initialize Find Difference service
                from services.find_difference_service import FindDifferenceService
                find_diff_service = FindDifferenceService()
                
                # Update progress
                self.progress_info[project_id].update({
                    'stage': 'processing',
                    'progress': 20,
                    'message': 'Capturing screenshots and generating diffs...'
                })
                
                # Check for stop signal
                if self._should_stop(project_id):
                    crawl_job.fail_job("Job stopped by user")
                    db.session.commit()
                    return
                
                # Run Find Difference workflow with job control
                import asyncio
                successful_count, failed_count, run_id = asyncio.run(
                    find_diff_service.run_find_difference(project_id, scheduler=self)
                )
                
                # Check for stop signal
                if self._should_stop(project_id):
                    crawl_job.fail_job("Job stopped by user")
                    db.session.commit()
                    return
                
                # Update progress
                total_processed = successful_count + failed_count
                self.progress_info[project_id].update({
                    'stage': 'completed',
                    'progress': 100,
                    'message': f'Find Difference completed! Run ID: {run_id}, Successful: {successful_count}, Failed: {failed_count}'
                })
                
                # Complete the job
                crawl_job.complete_job(total_processed)
                db.session.commit()
                
                print(f"Find Difference job {job_id} completed for project {project_id}. Run ID: {run_id}, Successful: {successful_count}, Failed: {failed_count}")
                
        except Exception as e:
            print(f"Error in Find Difference job {job_id} for project {project_id}: {str(e)}")
            self.progress_info[project_id] = {
                'stage': 'error',
                'progress': 0,
                'message': f'Error: {str(e)}',
                'job_id': job_id,
                'job_type': 'find_difference'
            }
            with self.app.app_context():
                if crawl_job:
                    crawl_job.fail_job(str(e))
                    db.session.commit()
                else:
                    db.session.rollback()
        finally:
            # Remove from running jobs after job completion with proper delay
            def cleanup():
                time.sleep(5)  # Wait 5 seconds before cleanup to avoid race conditions
                if project_id in self.running_jobs:
                    del self.running_jobs[project_id]
                    print(f"Removed Find Difference job {job_id} from running jobs for project {project_id}")
                if project_id in self.progress_info:
                    del self.progress_info[project_id]
            
            cleanup_thread = threading.Thread(target=cleanup)
            cleanup_thread.daemon = True
            cleanup_thread.start()
    
    def schedule_manual_page_capture(self, project_id, page_id, viewports=['desktop', 'tablet', 'mobile']):
        """Start a manual page capture job in a background thread"""
        # Create a unique job key for this specific page capture
        job_key = f"{project_id}_page_{page_id}"
        
        if job_key in self.running_jobs:
            return None  # Job already running for this page
        
        # Create crawl job record for manual page capture
        with self.app.app_context():
            crawl_job = CrawlJob(project_id=project_id)
            crawl_job.job_type = 'manual_page_capture'
            db.session.add(crawl_job)
            db.session.commit()
            job_id = crawl_job.id
        
        # Start manual page capture in background thread
        thread = threading.Thread(target=self._manual_page_capture_job, args=[project_id, page_id, job_id, viewports])
        thread.daemon = True
        thread.start()
        
        # Store job information with control flags
        self.running_jobs[job_key] = {
            'job_id': job_id,
            'thread': thread,
            'should_stop': False,
            'should_pause': False,
            'job_type': 'manual_page_capture',
            'page_id': page_id
        }
        
        return job_id
    
    def _manual_page_capture_job(self, project_id, page_id, job_id, viewports):
        """Background job to capture screenshots for a single page"""
        crawl_job = None
        job_key = f"{project_id}_page_{page_id}"
        
        try:
            with self.app.app_context():
                print(f"Starting manual page capture job {job_id} for project {project_id}, page {page_id}")
                
                # Get crawl job from database
                crawl_job = db.session.get(CrawlJob, job_id)
                if not crawl_job:
                    print(f"Manual page capture job {job_id} not found")
                    return
                
                # Get page from database
                page = db.session.get(ProjectPage, page_id)
                if not page or page.project_id != project_id:
                    print(f"Page {page_id} not found or doesn't belong to project {project_id}")
                    crawl_job.fail_job("Page not found or access denied")
                    db.session.commit()
                    return
                
                # Update page status to pending (queued is not a valid enum value)
                page.find_diff_status = 'pending'
                db.session.commit()
                
                # Check for stop signal before starting
                if self._should_stop_job_key(job_key):
                    crawl_job.fail_job("Job stopped by user")
                    page.find_diff_status = 'failed'
                    db.session.commit()
                    return
                
                # Start the job
                crawl_job.start_job()
                db.session.commit()
                
                # Initialize progress tracking
                self.progress_info[job_key] = {
                    'stage': 'initializing',
                    'progress': 0,
                    'message': f'Initializing capture for {page.page_name or page.path}...',
                    'job_id': job_id,
                    'job_type': 'manual_page_capture',
                    'page_id': page_id
                }
                
                # Update page status to processing
                page.find_diff_status = 'capturing'
                db.session.commit()
                
                # Update progress
                self.progress_info[job_key].update({
                    'stage': 'capturing',
                    'progress': 20,
                    'message': f'Capturing screenshots for {page.page_name or page.path}...'
                })
                
                # Check for stop signal
                if self._should_stop_job_key(job_key):
                    crawl_job.fail_job("Job stopped by user")
                    page.find_diff_status = 'failed'
                    db.session.commit()
                    return
                
                # Initialize Find Difference service
                from services.find_difference_service import FindDifferenceService
                find_diff_service = FindDifferenceService()
                
                # Update progress
                self.progress_info[job_key].update({
                    'stage': 'processing',
                    'progress': 40,
                    'message': f'Processing screenshots and generating diffs...'
                })
                
                # Check for stop signal
                if self._should_stop_job_key(job_key):
                    crawl_job.fail_job("Job stopped by user")
                    page.find_diff_status = 'failed'
                    db.session.commit()
                    return
                
                # Run capture and diff for the single page
                import asyncio
                result = asyncio.run(find_diff_service.capture_and_diff(
                    project_id=project_id,
                    page_id=page_id,
                    viewports=viewports
                ))
                
                # Check for stop signal
                if self._should_stop_job_key(job_key):
                    crawl_job.fail_job("Job stopped by user")
                    page.find_diff_status = 'failed'
                    db.session.commit()
                    return
                
                # Update progress based on result
                if result['success']:
                    self.progress_info[job_key].update({
                        'stage': 'completed',
                        'progress': 100,
                        'message': f'Screenshot capture completed for {page.page_name or page.path}!'
                    })
                    
                    # Update page status to completed
                    page.find_diff_status = 'completed'
                    page.current_run_id = result.get('run_id')
                    page.last_run_at = db.func.now()
                    
                    # Complete the job
                    crawl_job.complete_job(1)  # 1 page processed
                    db.session.commit()
                    
                    print(f"Manual page capture job {job_id} completed successfully for page {page_id}")
                else:
                    # Update page status to failed
                    page.find_diff_status = 'failed'
                    db.session.commit()
                    
                    # Fail the job
                    error_message = result.get('message', 'Unknown error during capture')
                    crawl_job.fail_job(error_message)
                    db.session.commit()
                    
                    self.progress_info[job_key].update({
                        'stage': 'error',
                        'progress': 0,
                        'message': f'Failed to capture screenshots: {error_message}'
                    })
                    
                    print(f"Manual page capture job {job_id} failed for page {page_id}: {error_message}")
                
        except Exception as e:
            print(f"Error in manual page capture job {job_id} for page {page_id}: {str(e)}")
            self.progress_info[job_key] = {
                'stage': 'error',
                'progress': 0,
                'message': f'Error: {str(e)}',
                'job_id': job_id,
                'job_type': 'manual_page_capture',
                'page_id': page_id
            }
            with self.app.app_context():
                if crawl_job:
                    crawl_job.fail_job(str(e))
                    # Update page status to failed
                    page = db.session.get(ProjectPage, page_id)
                    if page:
                        page.find_diff_status = 'failed'
                    db.session.commit()
                else:
                    db.session.rollback()
        finally:
            # Remove from running jobs after job completion with proper delay
            def cleanup():
                time.sleep(3)  # Wait 3 seconds before cleanup
                if job_key in self.running_jobs:
                    del self.running_jobs[job_key]
                    print(f"Removed manual page capture job {job_id} from running jobs for page {page_id}")
                if job_key in self.progress_info:
                    del self.progress_info[job_key]
            
            cleanup_thread = threading.Thread(target=cleanup)
            cleanup_thread.daemon = True
            cleanup_thread.start()
    
    def _should_stop_job_key(self, job_key):
        """Check if job should be stopped by job key"""
        if job_key not in self.running_jobs:
            return False
        return self.running_jobs[job_key].get('should_stop', False)
    
    def get_page_job_status(self, project_id, page_id):
        """Get the status of a manual page capture job"""
        job_key = f"{project_id}_page_{page_id}"
        if job_key in self.running_jobs:
            return {'status': 'scheduled', 'job_key': job_key}
        else:
            return {'status': 'not_scheduled', 'job_key': job_key}
    
    def get_page_progress_info(self, project_id, page_id):
        """Get progress information for a manual page capture job"""
        job_key = f"{project_id}_page_{page_id}"
        return self.progress_info.get(job_key, {
            'stage': 'unknown',
            'progress': 0,
            'message': 'No progress information available'
        })
    
    def schedule_find_difference_for_job(self, job_id, page_ids=None):
        """
        Schedule a find difference job for a specific CrawlJob (phase-based workflow)
        
        Args:
            job_id (int): ID of the CrawlJob to advance through phases
            page_ids (list): Optional list of page IDs to process
        """
        # Get the project_id from the job
        with self.app.app_context():
            from models.crawl_job import CrawlJob
            crawl_job = db.session.get(CrawlJob, job_id)
            if not crawl_job:
                print(f"CrawlJob {job_id} not found")
                return None
            
            project_id = crawl_job.project_id
        
        # Check if there's already a find difference job running for this project
        if project_id in self.running_jobs:
            job_info = self.running_jobs[project_id]
            if job_info.get('job_type') == 'find_difference':
                print(f"Find difference job already running for project {project_id}")
                return None
        
        # Create crawl job record for Find Difference (reuse existing job)
        with self.app.app_context():
            # Update the existing job to find_difference type
            crawl_job.job_type = 'find_difference'
            db.session.commit()
            
            # Use the existing job_id
            existing_job_id = job_id
        
        # Start Find Difference in background thread
        thread = threading.Thread(target=self._find_difference_for_job, args=[existing_job_id, page_ids])
        thread.daemon = True
        thread.start()
        
        # Store job information with control flags
        self.running_jobs[project_id] = {
            'job_id': existing_job_id,
            'thread': thread,
            'should_stop': False,
            'should_pause': False,
            'job_type': 'find_difference'
        }
        
        return existing_job_id
    
    def _find_difference_for_job(self, job_id, page_ids=None):
        """
        Background job to find differences for a specific CrawlJob (phase-based workflow)
        
        Args:
            job_id (int): ID of the CrawlJob to advance through phases
            page_ids (list): Optional list of page IDs to process
        """
        crawl_job = None
        project_id = None
        try:
            with self.app.app_context():
                print(f"Starting find difference for job {job_id}")
                
                # Get the crawl job from database
                from models.crawl_job import CrawlJob
                crawl_job = db.session.get(CrawlJob, job_id)
                if not crawl_job:
                    print(f"CrawlJob {job_id} not found")
                    return
                
                project_id = crawl_job.project_id
                
                if crawl_job.status != 'finding_difference':
                    print(f"CrawlJob {job_id} is not in 'finding_difference' status (current: {crawl_job.status})")
                    return
                
                # Initialize progress tracking
                self.progress_info[project_id] = {
                    'stage': 'initializing',
                    'progress': 0,
                    'message': 'Initializing Find Difference workflow...',
                    'job_id': job_id,
                    'job_type': 'find_difference'
                }
                
                # Get project from database
                from models.project import Project
                project = db.session.get(Project, crawl_job.project_id)
                if not project:
                    print(f"Project {crawl_job.project_id} not found")
                    crawl_job.fail_find_difference("Project not found")
                    db.session.commit()
                    return
                
                # Check for stop signal before starting
                if self._should_stop(project_id):
                    crawl_job.fail_find_difference("Job stopped by user")
                    db.session.commit()
                    return
                
                # Update progress
                self.progress_info[project_id].update({
                    'stage': 'processing',
                    'progress': 20,
                    'message': 'Capturing screenshots and generating diffs...'
                })
                
                # Check for stop signal
                if self._should_stop(project_id):
                    crawl_job.fail_find_difference("Job stopped by user")
                    db.session.commit()
                    return
                
                # Import find difference service
                from services.find_difference_service import FindDifferenceService
                find_diff_service = FindDifferenceService()
                
                # Update progress
                self.progress_info[project_id].update({
                    'stage': 'processing',
                    'progress': 40,
                    'message': 'Running find difference workflow...'
                })
                
                # Check for stop signal
                if self._should_stop(project_id):
                    crawl_job.fail_find_difference("Job stopped by user")
                    db.session.commit()
                    return
                
                # Run find difference for specified or all pages
                import asyncio
                successful_count, failed_count, run_id = asyncio.run(
                    find_diff_service.run_find_difference(crawl_job.project_id, page_ids, self)
                )
                
                # Check for stop signal
                if self._should_stop(project_id):
                    crawl_job.fail_find_difference("Job stopped by user")
                    db.session.commit()
                    return
                
                # Update progress
                self.progress_info[project_id].update({
                    'stage': 'completing',
                    'progress': 90,
                    'message': f'Finalizing results... Successful: {successful_count}, Failed: {failed_count}'
                })
                
                # PHASE TRANSITION: Finding Difference → Ready (or diff_failed)
                if failed_count == 0:
                    crawl_job.complete_find_difference()
                    print(f"CrawlJob {job_id} completed find difference phase successfully")
                    
                    # Final progress update
                    self.progress_info[project_id].update({
                        'stage': 'completed',
                        'progress': 100,
                        'message': f'Find Difference completed! Run ID: {run_id}, Successful: {successful_count}, Status: Ready'
                    })
                else:
                    error_msg = f"Find difference completed with {failed_count} failures out of {successful_count + failed_count} pages"
                    if successful_count == 0:
                        # Complete failure
                        crawl_job.fail_find_difference(error_msg)
                        print(f"CrawlJob {job_id} failed find difference phase: {error_msg}")
                        
                        self.progress_info[project_id].update({
                            'stage': 'error',
                            'progress': 0,
                            'message': f'Find Difference failed: {error_msg}'
                        })
                    else:
                        # Partial success - still mark as ready but log the issues
                        crawl_job.complete_find_difference()
                        print(f"CrawlJob {job_id} completed find difference with partial failures: {error_msg}")
                        
                        self.progress_info[project_id].update({
                            'stage': 'completed',
                            'progress': 100,
                            'message': f'Find Difference completed with warnings! Run ID: {run_id}, Successful: {successful_count}, Failed: {failed_count}, Status: Ready'
                        })
                
                db.session.commit()
                
                print(f"Find difference for job {job_id} completed. "
                      f"Successful: {successful_count}, Failed: {failed_count}, Run ID: {run_id}, "
                      f"Final Status: {crawl_job.status}")
                
        except Exception as e:
            print(f"Error in find difference for job {job_id}: {str(e)}")
            
            if project_id:
                self.progress_info[project_id] = {
                    'stage': 'error',
                    'progress': 0,
                    'message': f'Error: {str(e)}',
                    'job_id': job_id,
                    'job_type': 'find_difference'
                }
            
            with self.app.app_context():
                # PHASE TRANSITION: Finding Difference → diff_failed
                if crawl_job:
                    crawl_job.fail_find_difference(str(e))
                    try:
                        db.session.commit()
                    except:
                        db.session.rollback()
                else:
                    db.session.rollback()
        finally:
            # Clean up progress info and running jobs
            if project_id:
                # Remove from running jobs after job completion with proper delay
                def cleanup():
                    time.sleep(5)  # Wait 5 seconds before cleanup to avoid race conditions
                    if project_id in self.running_jobs:
                        del self.running_jobs[project_id]
                        print(f"Removed find difference job {job_id} from running jobs for project {project_id}")
                    if project_id in self.progress_info:
                        del self.progress_info[project_id]
                
                cleanup_thread = threading.Thread(target=cleanup)
                cleanup_thread.daemon = True
                cleanup_thread.start()

crawler_scheduler = WorkingCrawlerScheduler(app)

# Import and register routes after all initializations
from auth.routes import register_routes
from projects.routes import register_project_routes
from history.routes import register_history_routes
from routes.asset_resolver import register_asset_resolver_routes
from routes.run_state_routes import register_run_state_routes
from settings.routes import settings_bp
from analytics.routes import register_analytics_routes

register_routes(app)
register_project_routes(app, crawler_scheduler)
register_history_routes(app)
register_asset_resolver_routes(app)
register_run_state_routes(app, crawler_scheduler)
register_analytics_routes(app)
app.register_blueprint(settings_bp)

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Enhanced dashboard with KPI data and recent projects"""
    from sqlalchemy import func, desc
    
    # Get KPI statistics
    total_projects = Project.query.filter_by(user_id=current_user.id).count()
    
    # Get active tasks (running crawl jobs) - include all active statuses
    active_tasks = db.session.query(CrawlJob).join(Project).filter(
        Project.user_id == current_user.id,
        CrawlJob.status.in_(['running', 'pending', 'crawling', 'finding_difference', 'paused'])
    ).count()
    
    # Get recent diffs - count pages with actual visual differences
    from sqlalchemy import or_
    recent_diffs = db.session.query(ProjectPage).join(Project).filter(
        Project.user_id == current_user.id,
        ProjectPage.find_diff_status == 'completed',
        or_(
            ProjectPage.diff_mismatch_pct_desktop > 0,
            ProjectPage.diff_mismatch_pct_tablet > 0,
            ProjectPage.diff_mismatch_pct_mobile > 0
        )
    ).count()
    
    # Calculate success rate (completed and ready jobs vs total jobs)
    total_jobs = db.session.query(CrawlJob).join(Project).filter(
        Project.user_id == current_user.id,
        CrawlJob.status.in_(['completed', 'ready', 'Job Failed', 'diff_failed'])
    ).count()
    
    successful_jobs = db.session.query(CrawlJob).join(Project).filter(
        Project.user_id == current_user.id,
        CrawlJob.status.in_(['completed', 'ready'])
    ).count()
    
    success_rate = round((successful_jobs / total_jobs * 100) if total_jobs > 0 else 0, 1)
    
    # Get recent projects (last 5)
    recent_projects = Project.query.filter_by(user_id=current_user.id).order_by(desc(Project.created_at)).limit(5).all()
    
    # Get project stats for each recent project
    for project in recent_projects:
        project.page_count = ProjectPage.query.filter_by(project_id=project.id).count()
        project.last_crawl = db.session.query(CrawlJob).filter_by(
            project_id=project.id
        ).order_by(desc(CrawlJob.created_at)).first()
        
        # Get diff count (placeholder - using page count for now)
        project.diff_count = min(project.page_count, 3)  # Placeholder logic
        
        # Determine project status
        if project.last_crawl:
            if project.last_crawl.status == 'running':
                project.display_status = 'Active'
                project.status_class = 'success'
            elif project.last_crawl.status == 'completed':
                project.display_status = 'Completed'
                project.status_class = 'info'
            elif project.last_crawl.status == 'failed':
                project.display_status = 'Failed'
                project.status_class = 'danger'
            else:
                project.display_status = 'Pending'
                project.status_class = 'warning'
        else:
            project.display_status = 'Not Crawled'
            project.status_class = 'secondary'
    
    kpis = {
        'active_projects': total_projects,
        'recent_diffs': min(recent_diffs, 999),  # Cap for display
        'success_rate': success_rate,
        'active_tasks': active_tasks
    }
    
    return render_template('dashboard.html',
                         user=current_user,
                         kpis=kpis,
                         recent_projects=recent_projects)

if __name__ == '__main__':
    with app.app_context():
        from models import db
        from models.user import User
        db.create_all()
        
        # Create a demo user if it doesn't exist
        if not User.query.filter_by(username='demo').first():
            demo_user = User(username='demo')
            demo_user.set_password('demo123')
            db.session.add(demo_user)
            db.session.commit()
            print("Demo user created: username='demo', password='demo123'")
    
    print("Starting UI Diff Dashboard with MySQL...")
    print("Access the application at: http://localhost:5001")
    print("Demo credentials: username='demo', password='demo123'")
    app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False)