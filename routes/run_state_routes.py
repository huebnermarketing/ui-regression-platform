"""
Run State API Routes - Provides endpoints for unified pipeline status

These routes expose the run state service functionality to the frontend,
allowing consistent pipeline status display across all UI components.
"""

from flask import jsonify, request
from flask_login import login_required, current_user
from models.project import Project
from services.run_state_service import RunStateService


def register_run_state_routes(app, crawler_scheduler=None):
    """Register run state API routes with the Flask app"""
    
    # Initialize run state service with scheduler
    run_state_service = RunStateService(crawler_scheduler)
    
    @app.route('/api/projects/<int:project_id>/runs/latest/state')
    @login_required
    def get_latest_run_state(project_id):
        """Get the latest run state for a project"""
        try:
            # Verify user has access to this project
            project = Project.query.filter_by(
                id=project_id,
                user_id=current_user.id
            ).first()
            
            if not project:
                return jsonify({
                    'success': False,
                    'error': 'Project not found or access denied'
                }), 404
            
            # Get latest run state
            run_state = run_state_service.get_project_run_state(project_id)
            
            return jsonify({
                'success': True,
                'run_state': run_state
            })
            
        except Exception as e:
            app.logger.error(f"Error getting latest run state for project {project_id}: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500
    
    @app.route('/api/projects/<int:project_id>/runs/<run_id>/state')
    @login_required
    def get_specific_run_state(project_id, run_id):
        """Get the run state for a specific run"""
        try:
            # Verify user has access to this project
            project = Project.query.filter_by(
                id=project_id,
                user_id=current_user.id
            ).first()
            
            if not project:
                return jsonify({
                    'success': False,
                    'error': 'Project not found or access denied'
                }), 404
            
            # Get specific run state
            run_state = run_state_service.get_project_run_state(project_id, run_id)
            
            return jsonify({
                'success': True,
                'run_state': run_state
            })
            
        except Exception as e:
            app.logger.error(f"Error getting run state for project {project_id}, run {run_id}: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500
    
    @app.route('/api/projects/<int:project_id>/runs/summary')
    @login_required
    def get_runs_summary(project_id):
        """Get summary of recent runs for a project"""
        try:
            # Verify user has access to this project
            project = Project.query.filter_by(
                id=project_id,
                user_id=current_user.id
            ).first()
            
            if not project:
                return jsonify({
                    'success': False,
                    'error': 'Project not found or access denied'
                }), 404
            
            # Get query parameters
            limit = request.args.get('limit', 10, type=int)
            limit = min(50, max(1, limit))  # Clamp between 1 and 50
            
            # Get runs summary
            runs_summary = run_state_service.get_run_summary(project_id, limit)
            
            return jsonify({
                'success': True,
                'runs': runs_summary,
                'total': len(runs_summary)
            })
            
        except Exception as e:
            app.logger.error(f"Error getting runs summary for project {project_id}: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500
    
    @app.route('/api/projects/runs/states')
    @login_required
    def get_multiple_projects_run_states():
        """Get run states for multiple projects (for projects list page)"""
        try:
            # Get project IDs from query parameter
            project_ids_param = request.args.get('project_ids', '')
            if not project_ids_param:
                return jsonify({
                    'success': False,
                    'error': 'project_ids parameter is required'
                }), 400
            
            try:
                project_ids = [int(pid.strip()) for pid in project_ids_param.split(',') if pid.strip()]
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid project_ids format'
                }), 400
            
            if not project_ids:
                return jsonify({
                    'success': True,
                    'run_states': {}
                })
            
            # Verify user has access to all requested projects
            accessible_projects = Project.query.filter(
                Project.id.in_(project_ids),
                Project.user_id == current_user.id
            ).all()
            
            accessible_project_ids = [p.id for p in accessible_projects]
            
            # Get run states for accessible projects
            run_states = run_state_service.get_multiple_projects_run_state(accessible_project_ids)
            
            return jsonify({
                'success': True,
                'run_states': run_states
            })
            
        except Exception as e:
            app.logger.error(f"Error getting multiple project run states: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500
    
    @app.route('/api/pipeline/states')
    @login_required
    def get_pipeline_states_config():
        """Get the pipeline states configuration for frontend"""
        try:
            return jsonify({
                'success': True,
                'pipeline_states': RunStateService.PIPELINE_STATES
            })
            
        except Exception as e:
            app.logger.error(f"Error getting pipeline states config: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500