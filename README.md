# UI Diff Dashboard - Phase 1

A Flask-based web application for tracking UI differences between website versions. This is Phase 1 implementation focusing on project setup and authentication.

## Features (Phase 1)

- ✅ User authentication (login/logout)
- ✅ MySQL database integration
- ✅ Basic dashboard with placeholder buttons
- ✅ Session management with Flask-Login
- ✅ Bootstrap-based responsive UI
- ✅ User registration for testing

## Project Structure

```
ui-diff-dashboard/
│
├── app.py                   # Flask main entry point
├── config.py                # Configuration settings
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (configure before running)
├── README.md               # This file
│
├── /templates              # Jinja2 templates
│   ├── login.html          # Login page
│   ├── register.html       # Registration page
│   └── dashboard.html      # Main dashboard
│
├── /static                 # Static files (CSS, JS, images)
│   └── style.css          # Custom styles
│
├── /models                 # Database models
│   ├── __init__.py        # Database initialization
│   └── user.py            # User model
│
└── /auth                   # Authentication routes
    ├── __init__.py
    └── routes.py           # Login/logout/register routes
```

## Setup Instructions

### 1. Prerequisites

- Python 3.9+
- MySQL Server
- Virtual environment (recommended)

### 2. Installation

1. **Clone/Download the project**
   ```bash
   cd ui-diff-dashboard
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### 3. Database Setup

1. **Create MySQL database**
   ```sql
   CREATE DATABASE ui_diff_dashboard;
   ```

2. **Configure environment variables**
   
   Edit the `.env` file with your MySQL credentials:
   ```env
   # Database Configuration
   DB_HOST=localhost
   DB_USER=your_mysql_username
   DB_PASSWORD=your_mysql_password
   DB_NAME=ui_diff_dashboard

   # Flask Configuration
   SECRET_KEY=your-secret-key-here-change-in-production
   FLASK_ENV=development
   FLASK_DEBUG=True
   ```

### 4. Run the Application

```bash
python app.py
```

The application will be available at: `http://localhost:5000`

### 5. Create Test User

1. Navigate to `http://localhost:5000/register`
2. Create a test account
3. Login with your credentials

## Usage

### Login
- Access the application at `http://localhost:5000`
- You'll be redirected to the login page
- Use your registered credentials to log in

### Dashboard
- After login, you'll see the main dashboard
- Three placeholder buttons are available:
  - **Add Project** - For creating new UI diff projects (Phase 2)
  - **Project Details** - For managing existing projects (Phase 2)
  - **Results** - For viewing comparison results (Phase 2)

### Logout
- Click the "Logout" button in the navigation bar

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Flask 2.3.3 |
| Database | MySQL with SQLAlchemy |
| Authentication | Flask-Login + bcrypt |
| Frontend | Bootstrap 5.1.3 |
| Templates | Jinja2 |
| Environment | python-dotenv |

## Security Features

- Password hashing with Werkzeug
- Session management with Flask-Login
- CSRF protection (built into Flask)
- Environment variable configuration
- Login required decorators

## Development Notes

### Database Migrations

If you need to modify the database schema:

```bash
# Initialize migrations (first time only)
flask db init

# Create migration
flask db migrate -m "Description of changes"

# Apply migration
flask db upgrade
```

### Adding New Routes

1. Add routes to `auth/routes.py` or create new route modules
2. Register routes in `app.py`
3. Create corresponding templates in `templates/`

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Verify MySQL is running
   - Check credentials in `.env` file
   - Ensure database exists

2. **Import Errors**
   - Verify virtual environment is activated
   - Check all dependencies are installed

3. **Template Not Found**
   - Ensure templates are in the `templates/` directory
   - Check template names match route returns

## Next Phases

- **Phase 2**: Project management and website crawling
- **Phase 3**: Screenshot capture and comparison
- **Phase 4**: Difference detection and reporting
- **Phase 5**: Advanced features and optimization

## License

This project is for educational/development purposes.