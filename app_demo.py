from flask import Flask, render_template, redirect, url_for
from flask_migrate import Migrate
from flask_login import LoginManager, login_required, current_user
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration for SQLite (demo mode)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'demo-secret-key-for-testing')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ui_diff_dashboard.db'
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize crawler scheduler (working demo version)
import threading
import time
from crawler.crawler import WebCrawler

class DemoCrawlerScheduler:
    def __init__(self, app):
        self.app = app
        self.running_jobs = {}
    
    def schedule_crawl(self, project_id):
        """Start a crawl job in a background thread"""
        if project_id in self.running_jobs:
            return  # Job already running
        
        # Mark job as running
        self.running_jobs[project_id] = True
        
        # Start crawl in background thread
        thread = threading.Thread(target=self._crawl_project_job, args=[project_id])
        thread.daemon = True
        thread.start()
    
    def _crawl_project_job(self, project_id):
        """Background job to crawl a project"""
        try:
            with self.app.app_context():
                print(f"Starting crawl job for project {project_id}")
                
                # Get project from database
                project = Project.query.get(project_id)
                if not project:
                    print(f"Project {project_id} not found")
                    return
                
                # Initialize crawler
                crawler = WebCrawler(max_pages=10, delay=0.5)  # Smaller limits for demo
                
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
                    page.status = 'crawled'  # Mark as crawled
                    db.session.add(page)
                
                db.session.commit()
                
                print(f"Crawl job completed for project {project_id}. Found {len(matched_pages)} matching pages")
                
        except Exception as e:
            print(f"Error in crawl job for project {project_id}: {str(e)}")
            with self.app.app_context():
                db.session.rollback()
        finally:
            # Remove from running jobs
            if project_id in self.running_jobs:
                del self.running_jobs[project_id]
    
    def get_job_status(self, project_id):
        """Get the status of a crawl job"""
        if project_id in self.running_jobs:
            return {'status': 'scheduled'}
        else:
            return {'status': 'not_scheduled'}
    
    def cancel_crawl(self, project_id):
        """Cancel a scheduled crawl job"""
        if project_id in self.running_jobs:
            del self.running_jobs[project_id]
            return True
        return False

crawler_scheduler = DemoCrawlerScheduler(app)

# Import and register routes after all initializations
from auth.routes import register_routes
from projects.routes import register_project_routes

register_routes(app)
register_project_routes(app, crawler_scheduler)

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create a demo user if it doesn't exist
        if not User.query.filter_by(username='demo').first():
            demo_user = User(username='demo', password='demo123')
            db.session.add(demo_user)
            db.session.commit()
            print("Demo user created: username='demo', password='demo123'")
    
    print("Starting UI Diff Dashboard Demo...")
    print("Access the application at: http://localhost:5000")
    print("Demo credentials: username='demo', password='demo123'")
    app.run(debug=True)