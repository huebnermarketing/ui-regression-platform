from datetime import datetime
from models import db
import hashlib

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    staging_url = db.Column(db.Text, nullable=False)
    production_url = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_page_restricted = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationship to user
    user = db.relationship('User', backref=db.backref('projects', lazy=True))
    
    # Relationship to project pages
    pages = db.relationship('ProjectPage', backref='project', lazy=True, cascade='all, delete-orphan')
    
    # Unique constraint for project name per user
    __table_args__ = (db.UniqueConstraint('name', 'user_id', name='unique_project_name_per_user'),)
    
    def __init__(self, name, staging_url, production_url, user_id, is_page_restricted=False):
        self.name = name
        self.staging_url = staging_url
        self.production_url = production_url
        self.user_id = user_id
        self.is_page_restricted = is_page_restricted
    
    def __repr__(self):
        return f'<Project {self.name}>'

class ProjectPage(db.Model):
    __tablename__ = 'project_pages'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    path = db.Column(db.String(767), nullable=False)
    page_name = db.Column(db.String(500), nullable=True)  # New column for page title
    staging_url = db.Column(db.Text, nullable=False)
    production_url = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum('pending', 'crawled', 'ready_for_screenshot', 'screenshot_complete', 'screenshot_failed', 'ready_for_diff', 'diff_pending', 'diff_running', 'diff_generated', 'diff_failed', name='page_status'),
                      default='pending', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_crawled = db.Column(db.DateTime, nullable=True)  # New column for tracking crawl time
    staging_screenshot_path = db.Column(db.Text, nullable=True)  # Path to staging screenshot (legacy)
    production_screenshot_path = db.Column(db.Text, nullable=True)  # Path to production screenshot (legacy)
    
    # Multi-viewport screenshot paths
    staging_screenshot_path_desktop = db.Column(db.Text, nullable=True)
    staging_screenshot_path_tablet = db.Column(db.Text, nullable=True)
    staging_screenshot_path_mobile = db.Column(db.Text, nullable=True)
    production_screenshot_path_desktop = db.Column(db.Text, nullable=True)
    production_screenshot_path_tablet = db.Column(db.Text, nullable=True)
    production_screenshot_path_mobile = db.Column(db.Text, nullable=True)
    
    # Legacy diff generation fields
    diff_image_path = db.Column(db.Text, nullable=True)  # Path to highlighted diff image (legacy)
    diff_raw_image_path = db.Column(db.Text, nullable=True)  # Path to raw diff image (legacy)
    diff_mismatch_pct = db.Column(db.Numeric(6, 3), nullable=True)  # Percentage of changed pixels (legacy)
    diff_pixels_changed = db.Column(db.Integer, nullable=True)  # Total changed pixels (legacy)
    diff_bounding_boxes = db.Column(db.JSON, nullable=True)  # List of [x,y,w,h] bounding boxes (legacy)
    diff_generated_at = db.Column(db.DateTime, nullable=True)  # When diff was generated
    diff_error = db.Column(db.Text, nullable=True)  # Error message if diff failed
    
    # Multi-viewport diff paths
    diff_image_path_desktop = db.Column(db.Text, nullable=True)
    diff_image_path_tablet = db.Column(db.Text, nullable=True)
    diff_image_path_mobile = db.Column(db.Text, nullable=True)
    diff_raw_image_path_desktop = db.Column(db.Text, nullable=True)
    diff_raw_image_path_tablet = db.Column(db.Text, nullable=True)
    diff_raw_image_path_mobile = db.Column(db.Text, nullable=True)
    
    # Multi-viewport diff metrics
    diff_mismatch_pct_desktop = db.Column(db.Numeric(6, 3), nullable=True)
    diff_mismatch_pct_tablet = db.Column(db.Numeric(6, 3), nullable=True)
    diff_mismatch_pct_mobile = db.Column(db.Numeric(6, 3), nullable=True)
    diff_pixels_changed_desktop = db.Column(db.Integer, nullable=True)
    diff_pixels_changed_tablet = db.Column(db.Integer, nullable=True)
    diff_pixels_changed_mobile = db.Column(db.Integer, nullable=True)
    diff_bounding_boxes_desktop = db.Column(db.Text, nullable=True)  # JSON string
    diff_bounding_boxes_tablet = db.Column(db.Text, nullable=True)  # JSON string
    diff_bounding_boxes_mobile = db.Column(db.Text, nullable=True)  # JSON string
    
    # Timestamped run support
    current_run_id = db.Column(db.String(20), nullable=True)  # Current run ID (YYYYMMDD-HHmmss format)
    baseline_run_id = db.Column(db.String(20), nullable=True)  # Baseline run ID for comparison
    find_diff_status = db.Column(db.Enum('pending', 'capturing', 'captured', 'diffing', 'finding_difference', 'ready', 'completed', 'failed', 'no_baseline', name='find_diff_status'),
                                default='pending', nullable=False)
    last_run_at = db.Column(db.DateTime, nullable=True)  # When last run was executed
    
    # Per-page duration tracking (time taken for screenshot capture + diff generation)
    duration = db.Column(db.Numeric(8, 3), nullable=True)  # Duration in seconds with millisecond precision
    processing_started_at = db.Column(db.DateTime, nullable=True)  # When processing started for this page
    processing_completed_at = db.Column(db.DateTime, nullable=True)  # When processing completed for this page
    
    # Multi-viewport diff status tracking
    diff_status_desktop = db.Column(db.Enum('pending', 'processing', 'completed', 'failed', 'no_baseline', name='diff_status_desktop'),
                                   default='pending', nullable=False)
    diff_status_tablet = db.Column(db.Enum('pending', 'processing', 'completed', 'failed', 'no_baseline', name='diff_status_tablet'),
                                  default='pending', nullable=False)
    diff_status_mobile = db.Column(db.Enum('pending', 'processing', 'completed', 'failed', 'no_baseline', name='diff_status_mobile'),
                                  default='pending', nullable=False)
    
    # Error messages per viewport
    diff_error_desktop = db.Column(db.Text, nullable=True)
    diff_error_tablet = db.Column(db.Text, nullable=True)
    diff_error_mobile = db.Column(db.Text, nullable=True)
    
    # Unique constraint for path per project
    __table_args__ = (db.UniqueConstraint('project_id', 'path', name='unique_path_per_project'),)

    def __init__(self, project_id, path, staging_url, production_url, page_name=None):
        self.project_id = project_id
        self.path = path
        self.staging_url = staging_url
        self.production_url = production_url
        self.page_name = page_name
        self.last_crawled = datetime.utcnow()
    
    def start_processing(self):
        """Mark the start of processing (screenshot capture + diff generation) for this page"""
        self.processing_started_at = datetime.utcnow()
        self.find_diff_status = 'capturing'
    
    def complete_processing(self):
        """Mark the completion of processing and calculate duration"""
        if self.processing_started_at:
            self.processing_completed_at = datetime.utcnow()
            # Calculate duration in seconds with millisecond precision
            duration_seconds = (self.processing_completed_at - self.processing_started_at).total_seconds()
            self.duration = round(duration_seconds, 3)
        self.find_diff_status = 'completed'
    
    def fail_processing(self, error_message=None):
        """Mark processing as failed and calculate partial duration if started"""
        if self.processing_started_at:
            self.processing_completed_at = datetime.utcnow()
            # Calculate duration even for failed processing
            duration_seconds = (self.processing_completed_at - self.processing_started_at).total_seconds()
            self.duration = round(duration_seconds, 3)
        self.find_diff_status = 'failed'
    
    @property
    def duration_formatted(self):
        """Get formatted duration string for display"""
        if self.duration is None:
            return "N/A"
        
        duration_float = float(self.duration)
        
        if duration_float < 1:
            # Show milliseconds for very fast operations
            return f"{int(duration_float * 1000)}ms"
        elif duration_float < 60:
            # Show seconds with 1 decimal place
            return f"{duration_float:.1f}s"
        elif duration_float < 3600:
            # Show minutes and seconds
            minutes = int(duration_float // 60)
            seconds = int(duration_float % 60)
            return f"{minutes}m {seconds}s"
        else:
            # Show hours and minutes
            hours = int(duration_float // 3600)
            minutes = int((duration_float % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def __repr__(self):
        return f'<ProjectPage {self.path} - {self.page_name or "No Title"}>'