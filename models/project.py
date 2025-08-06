from datetime import datetime
from models import db

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    staging_url = db.Column(db.Text, nullable=False)
    production_url = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to user
    user = db.relationship('User', backref=db.backref('projects', lazy=True))
    
    # Relationship to project pages
    pages = db.relationship('ProjectPage', backref='project', lazy=True, cascade='all, delete-orphan')
    
    # Unique constraint for project name per user
    __table_args__ = (db.UniqueConstraint('name', 'user_id', name='unique_project_name_per_user'),)
    
    def __init__(self, name, staging_url, production_url, user_id):
        self.name = name
        self.staging_url = staging_url
        self.production_url = production_url
        self.user_id = user_id
    
    def __repr__(self):
        return f'<Project {self.name}>'

class ProjectPage(db.Model):
    __tablename__ = 'project_pages'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    page_name = db.Column(db.String(500), nullable=True)  # New column for page title
    staging_url = db.Column(db.Text, nullable=False)
    production_url = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum('pending', 'crawled', 'ready_for_diff', name='page_status'),
                      default='pending', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_crawled = db.Column(db.DateTime, nullable=True)  # New column for tracking crawl time
    
    # Unique constraint for path per project
    __table_args__ = (db.UniqueConstraint('project_id', 'path', name='unique_path_per_project'),)
    
    def __init__(self, project_id, path, staging_url, production_url, page_name=None):
        self.project_id = project_id
        self.path = path
        self.staging_url = staging_url
        self.production_url = production_url
        self.page_name = page_name
        self.last_crawled = datetime.utcnow()
    
    def __repr__(self):
        return f'<ProjectPage {self.path} - {self.page_name or "No Title"}>'