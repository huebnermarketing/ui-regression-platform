from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db
from models.project import Project, ProjectPage
from urllib.parse import urlparse
import re

def register_project_routes(app, crawler_scheduler):
    @app.route('/projects')
    @login_required
    def projects_list():
        """List all projects for the current user"""
        projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.created_at.desc()).all()
        return render_template('projects/list.html', projects=projects)
    
    @app.route('/projects/add', methods=['GET', 'POST'])
    @login_required
    def add_project():
        """Add a new project"""
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            staging_url = request.form.get('staging_url', '').strip()
            production_url = request.form.get('production_url', '').strip()
            
            # Validation
            if not name:
                flash('Project name is required', 'error')
                return render_template('projects/add.html')
            
            if not staging_url or not production_url:
                flash('Both staging and production URLs are required', 'error')
                return render_template('projects/add.html')
            
            # Validate URL format
            if not _is_valid_url(staging_url):
                flash('Staging URL must start with http:// or https://', 'error')
                return render_template('projects/add.html')
            
            if not _is_valid_url(production_url):
                flash('Production URL must start with http:// or https://', 'error')
                return render_template('projects/add.html')
            
            # Check if project name already exists for this user
            existing_project = Project.query.filter_by(
                name=name, 
                user_id=current_user.id
            ).first()
            
            if existing_project:
                flash('A project with this name already exists', 'error')
                return render_template('projects/add.html')
            
            # Create new project
            try:
                project = Project(
                    name=name,
                    staging_url=staging_url,
                    production_url=production_url,
                    user_id=current_user.id
                )
                db.session.add(project)
                db.session.commit()
                
                flash('Project created successfully!', 'success')
                return redirect(url_for('project_details', project_id=project.id))
                
            except Exception as e:
                db.session.rollback()
                flash('Error creating project. Please try again.', 'error')
                app.logger.error(f"Error creating project: {str(e)}")
                return render_template('projects/add.html')
        
        return render_template('projects/add.html')
    
    @app.route('/projects/<int:project_id>')
    @login_required
    def project_details(project_id):
        """View project details and pages with search, filter, and pagination"""
        project = Project.query.filter_by(
            id=project_id,
            user_id=current_user.id
        ).first_or_404()
        
        # Get query parameters for search, filter, and pagination
        search_query = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '')
        page_num = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)  # Default 20 items per page
        
        # Build base query
        query = ProjectPage.query.filter_by(project_id=project_id)
        
        # Apply search filter
        if search_query:
            query = query.filter(
                db.or_(
                    ProjectPage.path.ilike(f'%{search_query}%'),
                    ProjectPage.page_name.ilike(f'%{search_query}%'),
                    ProjectPage.staging_url.ilike(f'%{search_query}%'),
                    ProjectPage.production_url.ilike(f'%{search_query}%')
                )
            )
        
        # Apply status filter
        if status_filter:
            query = query.filter(ProjectPage.status == status_filter)
        
        # Order by last_crawled (newest first), then by path (MySQL compatible)
        query = query.order_by(ProjectPage.last_crawled.desc(), ProjectPage.path)
        
        # Paginate results
        pagination = query.paginate(
            page=page_num,
            per_page=per_page,
            error_out=False
        )
        
        pages = pagination.items
        
        # Get job status
        job_status = crawler_scheduler.get_job_status(project_id)
        
        # Get available statuses for filter dropdown
        available_statuses = db.session.query(ProjectPage.status).filter_by(project_id=project_id).distinct().all()
        available_statuses = [status[0] for status in available_statuses]
        
        return render_template('projects/details.html',
                             project=project,
                             pages=pages,
                             pagination=pagination,
                             job_status=job_status,
                             search_query=search_query,
                             status_filter=status_filter,
                             available_statuses=available_statuses,
                             per_page=per_page)
    
    @app.route('/projects/<int:project_id>/crawl', methods=['POST'])
    @login_required
    def start_crawl(project_id):
        """Start crawling for a project"""
        project = Project.query.filter_by(
            id=project_id, 
            user_id=current_user.id
        ).first_or_404()
        
        try:
            # Schedule the crawl job
            crawler_scheduler.schedule_crawl(project_id)
            flash('Crawling started! This may take a few minutes.', 'success')
            
        except Exception as e:
            flash('Error starting crawl. Please try again.', 'error')
            app.logger.error(f"Error starting crawl for project {project_id}: {str(e)}")
        
        return redirect(url_for('project_details', project_id=project_id))
    
    @app.route('/projects/<int:project_id>/status')
    @login_required
    def crawl_status(project_id):
        """Get crawl status for a project with progress information (AJAX endpoint)"""
        project = Project.query.filter_by(
            id=project_id,
            user_id=current_user.id
        ).first_or_404()
        
        job_status = crawler_scheduler.get_job_status(project_id)
        page_count = ProjectPage.query.filter_by(project_id=project_id).count()
        
        # Get progress information if crawling
        progress_info = {}
        if job_status.get('status') == 'scheduled':
            # Get additional progress details from crawler if available
            progress_info = crawler_scheduler.get_progress_info(project_id)
        
        return jsonify({
            'job_status': job_status,
            'page_count': page_count,
            'progress': progress_info
        })
    
    @app.route('/projects/<int:project_id>/cancel', methods=['POST'])
    @login_required
    def cancel_crawl(project_id):
        """Cancel crawling for a project"""
        project = Project.query.filter_by(
            id=project_id, 
            user_id=current_user.id
        ).first_or_404()
        
        try:
            success = crawler_scheduler.cancel_crawl(project_id)
            if success:
                flash('Crawl cancelled successfully.', 'info')
            else:
                flash('No active crawl job found.', 'warning')
                
        except Exception as e:
            flash('Error cancelling crawl.', 'error')
            app.logger.error(f"Error cancelling crawl for project {project_id}: {str(e)}")
        
        return redirect(url_for('project_details', project_id=project_id))
    
    @app.route('/projects/<int:project_id>/delete', methods=['POST'])
    @login_required
    def delete_project(project_id):
        """Delete a project and all its pages"""
        project = Project.query.filter_by(
            id=project_id, 
            user_id=current_user.id
        ).first_or_404()
        
        try:
            # Cancel any running crawl jobs
            crawler_scheduler.cancel_crawl(project_id)
            
            # Delete project (pages will be deleted due to cascade)
            db.session.delete(project)
            db.session.commit()
            
            flash(f'Project "{project.name}" deleted successfully.', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash('Error deleting project.', 'error')
            app.logger.error(f"Error deleting project {project_id}: {str(e)}")
        
        return redirect(url_for('projects_list'))

def _is_valid_url(url):
    """
    Validate that URL starts with http:// or https://
    
    Args:
        url (str): URL to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not url:
        return False
    
    # Check if URL starts with http:// or https://
    url_pattern = re.compile(r'^https?://.+')
    return bool(url_pattern.match(url))