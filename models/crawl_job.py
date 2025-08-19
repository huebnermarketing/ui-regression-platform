from datetime import datetime
from models import db

class CrawlJob(db.Model):
    __tablename__ = 'crawl_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    status = db.Column(db.Enum('pending', 'Crawling', 'Crawled', 'Job Failed', name='crawl_job_status'),
                      default='pending', nullable=False)
    job_number = db.Column(db.Integer, nullable=False)  # Incremental per project
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    job_type = db.Column(db.String(20), default='crawl', nullable=False)
    total_pages = db.Column(db.Integer, default=0, nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
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
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
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
    
    @property
    def duration(self):
        """Calculate duration of the job in seconds using UTC epoch time"""
        if not self.started_at:
            return None
        
        # Convert started_at to UTC epoch seconds (always treat as UTC)
        # This avoids timezone confusion by working with raw epoch time
        if self.started_at.tzinfo is None:
            # Assume naive datetime is already in UTC
            started_epoch = self.started_at.timestamp()
        else:
            # Convert timezone-aware datetime to UTC epoch
            started_epoch = self.started_at.timestamp()
        
        # Determine end time epoch
        if self.completed_at:
            # Job is completed/failed - use completed_at
            if self.completed_at.tzinfo is None:
                # Assume naive datetime is already in UTC
                end_epoch = self.completed_at.timestamp()
            else:
                # Convert timezone-aware datetime to UTC epoch
                end_epoch = self.completed_at.timestamp()
        elif self.status == 'Crawling':
            # Job is still running, use current UTC time
            import time
            end_epoch = time.time()
        else:
            # Job is pending/paused and not completed
            return None
        
        # Calculate duration in seconds using epoch time difference
        duration_seconds = end_epoch - started_epoch
        
        # Ensure duration is not negative (can happen with clock skew)
        return max(0, duration_seconds)
    
    @property
    def duration_formatted(self):
        """Get formatted duration string"""
        duration = self.duration
        if duration is None:
            return "N/A"
        
        if duration < 60:
            return f"{int(duration)}s"
        elif duration < 3600:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def __repr__(self):
        return f'<CrawlJob {self.id} - Project {self.project_id} - {self.status}>'