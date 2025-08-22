from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from services.analytics_service import AnalyticsService
import json

def register_analytics_routes(app):
    """Register analytics routes with the Flask app"""
    
    analytics_service = AnalyticsService()
    
    @app.route('/analytics')
    @login_required
    def analytics_dashboard():
        """Analytics dashboard page"""
        return render_template('analytics/dashboard.html', user=current_user)
    
    @app.route('/api/analytics/kpis')
    @login_required
    def api_analytics_kpis():
        """API endpoint for KPI data"""
        try:
            kpis = analytics_service.get_dashboard_kpis(current_user.id)
            return jsonify({
                'success': True,
                'data': kpis
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/analytics/runs-over-time')
    @login_required
    def api_runs_over_time():
        """API endpoint for runs over time chart data"""
        try:
            days = request.args.get('days', 30, type=int)
            data = analytics_service.get_runs_over_time(current_user.id, days)
            return jsonify({
                'success': True,
                'data': data
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/analytics/change-distribution')
    @login_required
    def api_change_distribution():
        """API endpoint for change distribution histogram data"""
        try:
            data = analytics_service.get_change_distribution(current_user.id)
            return jsonify({
                'success': True,
                'data': data
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/analytics/top-changed-pages')
    @login_required
    def api_top_changed_pages():
        """API endpoint for top changed pages table data"""
        try:
            limit = request.args.get('limit', 10, type=int)
            data = analytics_service.get_top_changed_pages(current_user.id, limit)
            return jsonify({
                'success': True,
                'data': data
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/analytics/slowest-pages')
    @login_required
    def api_slowest_pages():
        """API endpoint for slowest pages table data"""
        try:
            limit = request.args.get('limit', 10, type=int)
            data = analytics_service.get_slowest_pages(current_user.id, limit)
            return jsonify({
                'success': True,
                'data': data
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/analytics/storage-usage')
    @login_required
    def api_storage_usage():
        """API endpoint for storage usage by project data"""
        try:
            data = analytics_service.get_storage_usage_by_project(current_user.id)
            return jsonify({
                'success': True,
                'data': data
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/analytics/daily-scans-heatmap')
    @login_required
    def api_daily_scans_heatmap():
        """API endpoint for daily scans heatmap data"""
        try:
            days = request.args.get('days', 30, type=int)
            data = analytics_service.get_daily_scans_heatmap(current_user.id, days)
            return jsonify({
                'success': True,
                'data': data
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500