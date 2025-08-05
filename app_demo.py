from flask import Flask, render_template, redirect, url_for
from flask_migrate import Migrate
from flask_login import LoginManager, login_required, current_user
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration for SQLite (demo mode)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'demo-secret-key-for-testing')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ui_diff_dashboard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
from models import db
db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Import models after db initialization
from models.user import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import and register routes after all initializations
from auth.routes import register_routes
register_routes(app)

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create a demo user if it doesn't exist
        if not User.query.filter_by(username='demo').first():
            demo_user = User(username='demo', password='demo123')
            db.session.add(demo_user)
            db.session.commit()
            print("Demo user created: username='demo', password='demo123'")
    
    print("Starting UI Diff Dashboard Demo...")
    print("Access the application at: http://localhost:5000")
    print("Demo credentials: username='demo', password='demo123'")
    app.run(debug=True)