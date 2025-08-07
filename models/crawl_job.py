from datetime import datetime
from models import db

class CrawlJob(db.Model):
    __tablename__ = 'crawl_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    status = db.Column(db.Enum('pending', 'running', 'completed', 'failed', 'paused', name='crawl_job_status'),
                      default='pending', nullable=False)
    total_pages = db.Column(db.Integer, default=0, nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to project
    project = db.relationship('Project', backref=db.backref('crawl_jobs', lazy=True, cascade='all, delete-orphan'))
    
    def __init__(self, project_id):
        self.project_id = project_id
        self.status = 'pending'
        self.total_pages = 0
        self.created_at = datetime.utcnow()
    
    def start_job(self):
        """Mark job as running and set started_at timestamp"""
        self.status = 'running'
        self.started_at = datetime.utcnow()
    
    def start(self):
        """Alias for start_job for API compatibility"""
        self.start_job()
    
    def complete_job(self, total_pages):
        """Mark job as completed and set completion details"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        self.total_pages = total_pages
    
    def fail_job(self, error_message):
        """Mark job as failed and set error details"""
        self.status = 'failed'
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
    
    def fail(self, error_message):
        """Alias for fail_job for API compatibility"""
        self.fail_job(error_message)
    
    def pause(self):
        """Mark job as paused"""
        self.status = 'paused'
    
    @property
    def duration(self):
        """Calculate duration of the job in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
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