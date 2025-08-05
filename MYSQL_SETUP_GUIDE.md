# MySQL Setup Guide for UI Diff Dashboard

This guide will help you install MySQL and configure the UI Diff Dashboard to work with a MySQL database.

## Option 1: Install MySQL Server (Recommended)

### Step 1: Download and Install MySQL

1. **Download MySQL Community Server:**
   - Visit: https://dev.mysql.com/downloads/mysql/
   - Select "Windows" as your operating system
   - Download the MySQL Installer for Windows

2. **Run the MySQL Installer:**
   - Choose "Developer Default" setup type
   - This will install MySQL Server, MySQL Workbench, and other tools

3. **Configure MySQL Server:**
   - Set a **root password** (remember this - you'll need it!)
   - Keep the default port: **3306**
   - Configure MySQL to run as a Windows service
   - Complete the installation

### Step 2: Verify MySQL Installation

Open Command Prompt as Administrator and run:
```cmd
mysql --version
```

If this works, MySQL is installed correctly.

### Step 3: Configure Your Application

1. **Update your .env file** with your MySQL root password:
   ```env
   # Database Configuration
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=your_actual_mysql_root_password_here
   DB_NAME=ui_diff_dashboard

   # Flask Configuration
   SECRET_KEY=your-secret-key-here-change-in-production
   FLASK_ENV=development
   FLASK_DEBUG=True
   ```

2. **Run the setup script:**
   ```cmd
   python setup_mysql.py
   ```

3. **Start the application:**
   ```cmd
   python app.py
   ```

## Option 2: Use XAMPP (Easier Alternative)

### Step 1: Download and Install XAMPP

1. **Download XAMPP:**
   - Visit: https://www.apachefriends.org/download.html
   - Download XAMPP for Windows

2. **Install XAMPP:**
   - Run the installer
   - Select at least "Apache" and "MySQL" components
   - Install to default location (C:\xampp)

### Step 2: Start MySQL Service

1. **Open XAMPP Control Panel**
2. **Start MySQL** by clicking the "Start" button next to MySQL
3. **Verify** that MySQL is running (should show "Running" status)

### Step 3: Configure Your Application

1. **Update your .env file:**
   ```env
   # Database Configuration (XAMPP default settings)
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=
   DB_NAME=ui_diff_dashboard

   # Flask Configuration
   SECRET_KEY=your-secret-key-here-change-in-production
   FLASK_ENV=development
   FLASK_DEBUG=True
   ```
   
   **Note:** XAMPP MySQL has no password by default (empty password)

2. **Run the setup script:**
   ```cmd
   python setup_mysql.py
   ```

3. **Start the application:**
   ```cmd
   python app.py
   ```

## Option 3: Use Docker (Advanced Users)

If you have Docker installed:

```bash
# Start MySQL container
docker run --name mysql-ui-diff \
  -e MYSQL_ROOT_PASSWORD=rootpassword \
  -e MYSQL_DATABASE=ui_diff_dashboard \
  -p 3306:3306 \
  -d mysql:8.0

# Update .env file
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=rootpassword
DB_NAME=ui_diff_dashboard
```

## Troubleshooting

### Common Issues:

1. **"mysql command not found"**
   - MySQL is not installed or not in PATH
   - Try Option 2 (XAMPP) for easier setup

2. **"Access denied for user 'root'"**
   - Wrong password in .env file
   - Check your MySQL root password

3. **"Can't connect to MySQL server"**
   - MySQL service is not running
   - Check if MySQL service is started

4. **"Database connection failed"**
   - Verify MySQL is running
   - Check .env file configuration
   - Run: `python setup_mysql.py` to diagnose

### Testing Your Setup:

Run the setup script to test everything:
```cmd
python setup_mysql.py
```

This script will:
- ✅ Test MySQL connection
- ✅ Create the database
- ✅ Create tables
- ✅ Create an admin user

## Default Login Credentials

After successful setup:
- **Username:** admin
- **Password:** admin123

## Next Steps

Once MySQL is set up:

1. **Run the application:**
   ```cmd
   python app.py
   ```

2. **Access the application:**
   - Open browser: http://localhost:5000
   - Login with admin/admin123

3. **Create additional users:**
   - Use the registration page: http://localhost:5000/register

## Need Help?

If you encounter issues:
1. Run `python setup_mysql.py` for diagnostics
2. Check the error messages carefully
3. Verify your .env file configuration
4. Ensure MySQL service is running

---

**Recommendation:** Start with Option 2 (XAMPP) if you're new to MySQL - it's the easiest to set up and manage.