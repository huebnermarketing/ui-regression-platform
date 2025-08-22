from datetime import datetime
from models import db

class CrawlJob(db.Model):
    __tablename__ = 'crawl_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    status = db.Column(db.Enum('pending', 'Crawling', 'Crawled', 'Job Failed', 'finding_difference', 'ready', 'diff_failed', name='crawl_job_status'),
                      default='pending', nullable=False)
    job_number = db.Column(db.Integer, nullable=False)  # Incremental per project
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    job_type = db.Column(db.String(20), default='crawl', nullable=False)
    total_pages = db.Column(db.Integer, default=0, nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Phase-specific timestamps for run tracking
    crawl_started_at = db.Column(db.DateTime, nullable=True)
    crawl_completed_at = db.Column(db.DateTime, nullable=True)
    fd_started_at = db.Column(db.DateTime, nullable=True)  # Find Difference started
    fd_completed_at = db.Column(db.DateTime, nullable=True)  # Find Difference completed
    
    # Relationship to project
    project = db.relationship('Project', backref=db.backref('crawl_jobs', lazy=True, cascade='all, delete-orphan'))
    
    def __init__(self, project_id, job_number=None):
        self.project_id = project_id
        self.status = 'pending'
        self.total_pages = 0
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        # Auto-generate job_number if not provided
        if job_number is None:
            # Get the highest job_number for this project and increment
            max_job = db.session.query(db.func.max(CrawlJob.job_number)).filter_by(project_id=project_id).scalar()
            self.job_number = (max_job or 0) + 1
        else:
            self.job_number = job_number
    
    def start_job(self):
        """Mark job as Crawling and set started_at timestamp"""
        self.status = 'Crawling'
        current_time = datetime.utcnow()
        self.started_at = current_time
        self.crawl_started_at = current_time  # Track crawl phase start
        self.updated_at = current_time
    
    def start(self):
        """Alias for start_job for API compatibility"""
        self.start_job()
    
    def complete_job(self, total_pages):
        """Mark job as Crawled and set completion details - ATOMIC & IDEMPOTENT"""
        from sqlalchemy import text
        from models import db
        
        # Get current UTC time for consistent timezone handling
        completion_time = datetime.utcnow()
        
        # Atomic completion - only update if still crawling
        # Use explicit UTC timestamp instead of NOW() to avoid timezone issues
        result = db.session.execute(text('''
            UPDATE crawl_jobs
            SET status='Crawled',
                completed_at=:completion_time,
                crawl_completed_at=:completion_time,
                updated_at=:completion_time,
                total_pages=:total_pages,
                error_message=NULL
            WHERE id=:job_id AND status='Crawling'
        '''), {
            'job_id': self.id,
            'total_pages': total_pages,
            'completion_time': completion_time
        })
        
        if result.rowcount == 1:
            # Update local object to reflect database changes
            self.status = 'Crawled'
            self.completed_at = completion_time
            self.crawl_completed_at = completion_time  # Track crawl phase completion
            self.updated_at = completion_time
            self.total_pages = total_pages
            self.error_message = None
            return True
        else:
            # Job was already completed or not crawling - this is OK (idempotent)
            print(f"Job {self.id} completion was idempotent (already completed or not crawling)")
            return False
    
    def fail_job(self, error_message):
        """Mark job as Job Failed and set error details"""
        self.status = 'Job Failed'
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.error_message = error_message
    
    def fail(self, error_message):
        """Alias for fail_job for API compatibility"""
        self.fail_job(error_message)
    
    def pause(self):
        """Mark job as paused"""
        self.status = 'paused'
    
    def start_find_difference(self):
        """Start Find Difference phase - transition from Crawled to finding_difference"""
        if self.status != 'Crawled':
            raise ValueError(f"Cannot start Find Difference from status '{self.status}'. Must be 'Crawled'.")
        
        current_time = datetime.utcnow()
        self.status = 'finding_difference'
        self.fd_started_at = current_time
        self.updated_at = current_time
    
    def complete_find_difference(self):
        """Complete Find Difference phase - transition from finding_difference to ready"""
        if self.status != 'finding_difference':
            raise ValueError(f"Cannot complete Find Difference from status '{self.status}'. Must be 'finding_difference'.")
        
        current_time = datetime.utcnow()
        self.status = 'ready'
        self.fd_completed_at = current_time
        self.completed_at = current_time  # Overall job completion
        self.updated_at = current_time
    
    def fail_find_difference(self, error_message):
        """Fail Find Difference phase - transition to diff_failed"""
        current_time = datetime.utcnow()
        self.status = 'diff_failed'
        self.fd_completed_at = current_time
        self.completed_at = current_time
        self.updated_at = current_time
        self.error_message = error_message
    
    # Duration properties removed - now tracking per-page duration instead of job duration
    
    # duration_formatted property removed - now tracking per-page duration instead
    
    def __repr__(self):
        return f'<CrawlJob {self.id} - Project {self.project_id} - {self.status}>'