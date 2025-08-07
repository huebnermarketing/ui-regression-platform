from flask import Flask, render_template, redirect, url_for
from flask_migrate import Migrate
from flask_login import LoginManager, login_required, current_user
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Build database URI properly handling empty password and special characters
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
from models.user import User
from models.project import Project, ProjectPage
from models.crawl_job import CrawlJob

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize crawler scheduler (working version)
import threading
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
from typing import Set, List, Tuple
from crawler.crawler import WebCrawler

class EnhancedWebCrawler:
    def __init__(self, max_pages=200, delay=0.3):
        """
        Enhanced web crawler with better depth coverage and external link filtering
        
        Args:
            max_pages (int): Maximum number of pages to crawl per domain (increased for better coverage)
            delay (float): Delay between requests in seconds (reduced for faster crawling)
        """
        self.max_pages = max_pages
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'UI-Regression-Platform-Crawler/2.0'
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
        print(f"Max pages to crawl: {self.max_pages}")
        
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
        
        # Crawl both domains with enhanced crawler and job control
        print("Crawling staging environment...")
        staging_urls = self.crawl_domain(staging_url, scheduler, project_id)
        
        # Check for stop signal after staging crawl
        if scheduler and project_id and scheduler._should_stop(project_id):
            print("Crawl stopped after staging environment")
            return []
        
        print("Crawling production environment...")
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
        with self.app.app_context():
            # Find jobs that are marked as running but not in our scheduler
            orphaned_jobs = CrawlJob.query.filter_by(status='running').all()
            
            for job in orphaned_jobs:
                print(f"Found orphaned running job {job.id} for project {job.project_id}")
                # Mark these jobs as failed since we can't recover the actual threads
                job.fail_job("Job interrupted by application restart")
                db.session.commit()
                print(f"Marked orphaned job {job.id} as failed")
    
    def schedule_crawl(self, project_id):
        """Start a crawl job in a background thread"""
        if project_id in self.running_jobs:
            return  # Job already running
        
        # Create crawl job record
        with self.app.app_context():
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
                crawl_job = CrawlJob.query.get(job_id)
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
                project = Project.query.get(project_id)
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
                        crawl_job = CrawlJob.query.get(job_id)
                        crawl_job.pause()
                        db.session.commit()
                    
                    self.progress_info[project_id].update({
                        'stage': 'paused',
                        'message': 'Job paused by user'
                    })
                    time.sleep(1)  # Check every second
                    
                    if self._should_stop(project_id):
                        with self.app.app_context():
                            crawl_job = CrawlJob.query.get(job_id)
                            crawl_job.fail_job("Job stopped by user")
                            db.session.commit()
                        return
                
                # Resume if was paused
                with self.app.app_context():
                    crawl_job = CrawlJob.query.get(job_id)
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
                
                # Initialize enhanced crawler with better settings
                crawler = EnhancedWebCrawler(max_pages=200, delay=0.3)
                
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
                
                # Complete the job
                crawl_job.complete_job(len(matched_pages))
                db.session.commit()
                
                # Final progress update
                self.progress_info[project_id].update({
                    'stage': 'completed',
                    'progress': 100,
                    'message': f'Crawl completed! Found {len(matched_pages)} pages.'
                })
                
                print(f"Enhanced crawl job {job_id} completed for project {project_id}. Found {len(matched_pages)} matching pages")
                
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
            # Remove from running jobs after a delay to allow final status check
            def cleanup():
                time.sleep(5)  # Wait 5 seconds before cleanup
                if project_id in self.running_jobs:
                    del self.running_jobs[project_id]
                if project_id in self.progress_info:
                    del self.progress_info[project_id]
            
            cleanup_thread = threading.Thread(target=cleanup)
            cleanup_thread.daemon = True
            cleanup_thread.start()
    
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
                    crawl_job = CrawlJob.query.get(job_id)
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
                    crawl_job = CrawlJob.query.get(job_id)
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
                    crawl_job = CrawlJob.query.get(job_id)
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
                    crawl_job = CrawlJob.query.get(job_id)
                    if crawl_job and crawl_job.status in ['running', 'paused']:
                        crawl_job.fail_job("Job stopped by user")
                        db.session.commit()
                        print(f"Job {job_id} marked as stopped in database")
            except Exception as e:
                print(f"Error updating job status during stop: {e}")
            
            return True
        
        return False

crawler_scheduler = WorkingCrawlerScheduler(app)

# Import and register routes after all initializations
from auth.routes import register_routes
from projects.routes import register_project_routes
from crawl_queue.routes import register_crawl_queue_routes

register_routes(app)
register_project_routes(app, crawler_scheduler)
register_crawl_queue_routes(app, crawler_scheduler)

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
    
    # Get active tasks (running crawl jobs)
    active_tasks = db.session.query(CrawlJob).join(Project).filter(
        Project.user_id == current_user.id,
        CrawlJob.status == 'running'
    ).count()
    
    # Get recent diffs (for now, use total pages as placeholder)
    recent_diffs = db.session.query(func.sum(ProjectPage.id)).join(Project).filter(
        Project.user_id == current_user.id
    ).scalar() or 0
    
    # Calculate success rate (completed jobs vs total jobs)
    total_jobs = db.session.query(CrawlJob).join(Project).filter(
        Project.user_id == current_user.id
    ).count()
    
    completed_jobs = db.session.query(CrawlJob).join(Project).filter(
        Project.user_id == current_user.id,
        CrawlJob.status == 'completed'
    ).count()
    
    success_rate = round((completed_jobs / total_jobs * 100) if total_jobs > 0 else 0, 1)
    
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
        db.create_all()
        
        # Create a demo user if it doesn't exist
        if not User.query.filter_by(username='demo').first():
            demo_user = User(username='demo', password='demo123')
            db.session.add(demo_user)
            db.session.commit()
            print("Demo user created: username='demo', password='demo123'")
    
    print("Starting UI Diff Dashboard with MySQL...")
    print("Access the application at: http://localhost:5001")
    print("Demo credentials: username='demo', password='demo123'")
    app.run(debug=True, port=5001)