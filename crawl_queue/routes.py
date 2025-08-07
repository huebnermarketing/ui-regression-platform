from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from models.crawl_job import CrawlJob
from models.project import Project
from models import db
from sqlalchemy import desc, func

def register_crawl_queue_routes(app, crawler_scheduler=None):
    """Register crawl queue routes with the Flask app"""
    
    @app.route('/crawl-queue')
    @login_required
    def crawl_queue():
        """Display the crawl queue page with all jobs"""
        # Get filter parameters
        status_filter = request.args.get('status', '')
        search_query = request.args.get('search', '')
        
        # Base query - only show jobs for current user's projects
        base_query = db.session.query(CrawlJob).join(Project).filter(
            Project.user_id == current_user.id
        )
        
        # Get KPI statistics
        kpi_stats = db.session.query(
            CrawlJob.status,
            func.count(CrawlJob.id).label('count')
        ).join(Project).filter(
            Project.user_id == current_user.id
        ).group_by(CrawlJob.status).all()
        
        # Convert to dictionary for easy access
        kpis = {
            'queued': 0,
            'running': 0,
            'completed': 0,
            'failed': 0,
            'paused': 0
        }
        
        for stat in kpi_stats:
            if stat.status == 'pending':
                kpis['queued'] = stat.count
            elif stat.status in kpis:
                kpis[stat.status] = stat.count
        
        # Get active (running) jobs
        active_jobs = base_query.filter(CrawlJob.status == 'running').order_by(desc(CrawlJob.started_at)).all()
        
        # Apply filters for all jobs query
        query = base_query
        if status_filter and status_filter != 'all':
            query = query.filter(CrawlJob.status == status_filter)
        
        # Apply search filter (search in project name)
        if search_query:
            query = query.filter(Project.name.ilike(f'%{search_query}%'))
        
        # Order by created_at descending (newest first)
        all_jobs = query.order_by(desc(CrawlJob.created_at)).all()
        
        # Check if any jobs are running for auto-refresh
        has_running_jobs = len(active_jobs) > 0
        
        return render_template('crawl_queue/list.html',
                             kpis=kpis,
                             active_jobs=active_jobs,
                             all_jobs=all_jobs,
                             has_running_jobs=has_running_jobs,
                             status_filter=status_filter,
                             search_query=search_query)
    
    @app.route('/api/crawl-jobs')
    @login_required
    def api_crawl_jobs():
        """API endpoint to get crawl jobs data (for auto-refresh)"""
        # Get filter parameters
        status_filter = request.args.get('status', '')
        search_query = request.args.get('search', '')
        
        # Base query - only show jobs for current user's projects
        base_query = db.session.query(CrawlJob).join(Project).filter(
            Project.user_id == current_user.id
        )
        
        # Get KPI statistics
        kpi_stats = db.session.query(
            CrawlJob.status,
            func.count(CrawlJob.id).label('count')
        ).join(Project).filter(
            Project.user_id == current_user.id
        ).group_by(CrawlJob.status).all()
        
        # Convert to dictionary for easy access
        kpis = {
            'queued': 0,
            'running': 0,
            'completed': 0,
            'failed': 0,
            'paused': 0
        }
        
        for stat in kpi_stats:
            if stat.status == 'pending':
                kpis['queued'] = stat.count
            elif stat.status in kpis:
                kpis[stat.status] = stat.count
        
        # Get active (running) jobs
        active_jobs = base_query.filter(CrawlJob.status == 'running').order_by(desc(CrawlJob.started_at)).all()
        
        # Apply filters for all jobs query
        query = base_query
        if status_filter and status_filter != 'all':
            query = query.filter(CrawlJob.status == status_filter)
        
        # Apply search filter
        if search_query:
            query = query.filter(Project.name.ilike(f'%{search_query}%'))
        
        # Order by created_at descending
        all_jobs = query.order_by(desc(CrawlJob.created_at)).all()
        
        # Convert active jobs to JSON format
        active_jobs_data = []
        for job in active_jobs:
            active_jobs_data.append({
                'id': job.id,
                'project_name': job.project.name,
                'status': job.status,
                'total_pages': job.total_pages,
                'started_at': job.started_at.strftime('%Y-%m-%d %H:%M:%S') if job.started_at else None,
                'duration_formatted': job.duration_formatted,
                'project_id': job.project_id
            })
        
        # Convert all jobs to JSON format
        all_jobs_data = []
        for job in all_jobs:
            all_jobs_data.append({
                'id': job.id,
                'project_name': job.project.name,
                'status': job.status,
                'total_pages': job.total_pages,
                'started_at': job.started_at.strftime('%Y-%m-%d %H:%M:%S') if job.started_at else None,
                'completed_at': job.completed_at.strftime('%Y-%m-%d %H:%M:%S') if job.completed_at else None,
                'duration_formatted': job.duration_formatted,
                'error_message': job.error_message,
                'project_id': job.project_id
            })
        
        # Check if any jobs are running
        has_running_jobs = len(active_jobs) > 0
        
        return jsonify({
            'kpis': kpis,
            'active_jobs': active_jobs_data,
            'all_jobs': all_jobs_data,
            'has_running_jobs': has_running_jobs
        })
    
    @app.route('/api/crawl-jobs/<int:job_id>')
    @login_required
    def api_crawl_job_detail(job_id):
        """API endpoint to get specific crawl job details"""
        # Get job and verify it belongs to current user
        job = db.session.query(CrawlJob).join(Project).filter(
            CrawlJob.id == job_id,
            Project.user_id == current_user.id
        ).first()
        
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        return jsonify({
            'id': job.id,
            'project_name': job.project.name,
            'status': job.status,
            'total_pages': job.total_pages,
            'started_at': job.started_at.strftime('%Y-%m-%d %H:%M:%S') if job.started_at else None,
            'completed_at': job.completed_at.strftime('%Y-%m-%d %H:%M:%S') if job.completed_at else None,
            'duration_formatted': job.duration_formatted,
            'error_message': job.error_message,
            'project_id': job.project_id,
            'created_at': job.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    @app.route('/api/crawl-jobs/<int:job_id>/start', methods=['POST'])
    @login_required
    def api_start_crawl_job(job_id):
        """API endpoint to start a crawl job"""
        try:
            # Get job and verify it belongs to current user
            job = db.session.query(CrawlJob).join(Project).filter(
                CrawlJob.id == job_id,
                Project.user_id == current_user.id
            ).first()
            
            if not job:
                return jsonify({'success': False, 'message': 'Job not found'}), 404
            
            # Check if job can be started
            if job.status not in ['pending', 'paused']:
                return jsonify({'success': False, 'message': f'Cannot start job with status: {job.status}'}), 400
            
            # Use scheduler to start/resume the job
            if crawler_scheduler:
                success = crawler_scheduler.start_job(job_id)
                if success:
                    # Update job status in database
                    job.start()
                    db.session.commit()
                    return jsonify({'success': True, 'message': 'Job started successfully'})
                else:
                    return jsonify({'success': False, 'message': 'Failed to start job in scheduler'}), 500
            else:
                # Fallback: just update database status
                job.start()
                db.session.commit()
                return jsonify({'success': True, 'message': 'Job started successfully'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/crawl-jobs/<int:job_id>/pause', methods=['POST'])
    @login_required
    def api_pause_crawl_job(job_id):
        """API endpoint to pause a crawl job"""
        try:
            # Get job and verify it belongs to current user
            job = db.session.query(CrawlJob).join(Project).filter(
                CrawlJob.id == job_id,
                Project.user_id == current_user.id
            ).first()
            
            if not job:
                return jsonify({'success': False, 'message': 'Job not found'}), 404
            
            # Check if job can be paused
            if job.status != 'running':
                return jsonify({'success': False, 'message': f'Cannot pause job with status: {job.status}'}), 400
            
            # Use scheduler to pause the job
            if crawler_scheduler:
                success = crawler_scheduler.pause_job(job_id)
                if success:
                    return jsonify({'success': True, 'message': 'Job pause signal sent successfully'})
                else:
                    return jsonify({'success': False, 'message': 'Failed to pause job in scheduler'}), 500
            else:
                # Fallback: just update database status
                job.pause()
                db.session.commit()
                return jsonify({'success': True, 'message': 'Job paused successfully'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/crawl-jobs/<int:job_id>/stop', methods=['POST'])
    @login_required
    def api_stop_crawl_job(job_id):
        """API endpoint to stop a crawl job"""
        try:
            # Get job and verify it belongs to current user
            job = db.session.query(CrawlJob).join(Project).filter(
                CrawlJob.id == job_id,
                Project.user_id == current_user.id
            ).first()
            
            if not job:
                return jsonify({'success': False, 'message': 'Job not found'}), 404
            
            # Check if job can be stopped
            if job.status not in ['running', 'pending', 'paused']:
                return jsonify({'success': False, 'message': f'Cannot stop job with status: {job.status}'}), 400
            
            # Use scheduler to stop the job
            if crawler_scheduler:
                success = crawler_scheduler.stop_job(job_id)
                if success:
                    return jsonify({'success': True, 'message': 'Job stop signal sent successfully'})
                else:
                    return jsonify({'success': False, 'message': 'Failed to stop job in scheduler'}), 500
            else:
                # Fallback: just update database status
                job.fail('Job stopped by user')
                db.session.commit()
                return jsonify({'success': True, 'message': 'Job stopped successfully'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500