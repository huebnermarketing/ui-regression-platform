from flask import Flask, render_template, redirect, url_for
from flask_migrate import Migrate
from flask_login import LoginManager, login_required, current_user
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Build database URI properly handling empty password and special characters
from urllib.parse import quote_plus

db_user = os.getenv('DB_USER', 'root')
db_password = os.getenv('DB_PASSWORD', '')
db_host = os.getenv('DB_HOST', 'localhost')
db_name = os.getenv('DB_NAME', 'ui_diff_dashboard')

if db_password:
    # URL encode the password to handle special characters like @
    encoded_password = quote_plus(db_password)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}/{db_name}"
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}@{db_host}/{db_name}"

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
    app.run(debug=True)