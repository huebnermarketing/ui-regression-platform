"""
Settings routes for UI Regression Platform
Handles user settings and administrative functions
"""

import os
import sys
import subprocess
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db
from models.user import User
from models.project import Project, ProjectPage
from models.crawl_job import CrawlJob

# Create blueprint
settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/')
@login_required
def settings_page():
    """Display settings page"""
    # Get user statistics
    user_stats = get_user_statistics(current_user.id)
    
    return render_template('settings/index.html', 
                         user=current_user,
                         stats=user_stats)


@settings_bp.route('/cleanup/preview')
@login_required
def cleanup_preview():
    """Preview what would be deleted in cleanup"""
    try:
        # Get user statistics
        stats = get_user_statistics(current_user.id)
        
        # Get file system statistics
        file_stats = get_file_system_statistics(current_user.id)
        
        preview_data = {
            'success': True,
            'user': {
                'username': current_user.username,
                'id': current_user.id,
                'created_at': current_user.created_at.isoformat()
            },
            'database': stats,
            'filesystem': file_stats
        }
        
        return jsonify(preview_data)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@settings_bp.route('/cleanup/execute', methods=['POST'])
@login_required
def cleanup_execute():
    """Execute cleanup for current user"""
    try:
        # Get confirmation from request
        data = request.get_json()
        if not data or not data.get('confirmed'):
            return jsonify({
                'success': False,
                'error': 'Cleanup must be confirmed'
            }), 400
        
        # Execute cleanup using the script
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cleanup_user_data.py')
        
        # Run cleanup script with current user
        result = subprocess.run([
            sys.executable, script_path,
            '--user-id', str(current_user.id),
            '--confirm'
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': 'All data has been successfully cleaned up!',
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Cleanup failed: {result.stderr}',
                'output': result.stdout
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def get_user_statistics(user_id):
    """Get database statistics for a user"""
    try:
        # Get projects
        projects = Project.query.filter_by(user_id=user_id).all()
        project_ids = [p.id for p in projects]
        
        # Get pages and jobs
        page_count = ProjectPage.query.filter(ProjectPage.project_id.in_(project_ids)).count() if project_ids else 0
        job_count = CrawlJob.query.filter(CrawlJob.project_id.in_(project_ids)).count() if project_ids else 0
        
        return {
            'projects': len(projects),
            'pages': page_count,
            'jobs': job_count,
            'project_list': [{'id': p.id, 'name': p.name, 'created_at': p.created_at.isoformat()} for p in projects]
        }
    except Exception:
        return {
            'projects': 0,
            'pages': 0,
            'jobs': 0,
            'project_list': []
        }


def get_file_system_statistics(user_id):
    """Get file system statistics for a user"""
    try:
        from pathlib import Path
        
        # Get projects for this user
        projects = Project.query.filter_by(user_id=user_id).all()
        project_ids = [p.id for p in projects]
        
        if not project_ids:
            return {
                'total_files': 0,
                'total_directories': 0,
                'directories_found': []
            }
        
        # Directories to check
        base_directories = ['screenshots', 'diffs', 'runs', 'test_screenshots']
        
        total_files = 0
        total_directories = 0
        directories_found = []
        
        for base_dir in base_directories:
            if not os.path.exists(base_dir):
                continue
                
            for project_id in project_ids:
                project_dir = Path(base_dir) / str(project_id)
                
                if project_dir.exists():
                    # Count files and directories
                    file_count = sum(1 for _ in project_dir.rglob('*') if _.is_file())
                    dir_count = sum(1 for _ in project_dir.rglob('*') if _.is_dir())
                    
                    total_files += file_count
                    total_directories += dir_count + 1  # +1 for project directory itself
                    
                    directories_found.append({
                        'path': str(project_dir),
                        'files': file_count,
                        'directories': dir_count
                    })
        
        return {
            'total_files': total_files,
            'total_directories': total_directories,
            'directories_found': directories_found
        }
        
    except Exception:
        return {
            'total_files': 0,
            'total_directories': 0,
            'directories_found': []
        }


def register_settings_routes(app):
    """Register settings routes with the Flask app"""
    app.register_blueprint(settings_bp)