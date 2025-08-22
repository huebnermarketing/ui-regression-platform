import unittest
from unittest.mock import patch, MagicMock
from app import create_app
from models import db
from models.user import User
from models.project import Project
from models.crawl_job import CrawlJob
from datetime import datetime, timedelta

class StuckJobHandlingTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(testing=True)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            self.create_user_and_project()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def create_user_and_project(self):
        self.user = User(username='testuser')
        self.user.set_password('password')
        db.session.add(self.user)
        db.session.commit()

        self.project = Project(
            name='Test Project',
            staging_url='http://staging.example.com',
            production_url='http://production.example.com',
            user_id=self.user.id
        )
        db.session.add(self.project)
        db.session.commit()

    def login(self):
        return self.client.post('/login', data=dict(
            username='testuser',
            password='password'
        ), follow_redirects=True)

    def test_start_crawl_with_stuck_job(self):
        self.login()
        with self.app.app_context():
            # Re-fetch the project to ensure it's in the current session
            project = Project.query.filter_by(name='Test Project').first()
            stuck_job = CrawlJob(project_id=project.id)
            stuck_job.status = 'Crawling'
            stuck_job.updated_at = datetime.utcnow() - timedelta(minutes=15)
            db.session.add(stuck_job)
            db.session.commit()

            with patch('projects.routes.crawler_scheduler', MagicMock()):
                response = self.client.post(f'/api/projects/{project.id}/start-crawl-job')

            self.assertEqual(response.status_code, 409)
            json_response = response.get_json()
            self.assertFalse(json_response['success'])
            self.assertEqual(json_response['message'], 'A previously stuck job was found and marked as failed. You can now start a new job.')

if __name__ == '__main__':
    unittest.main()