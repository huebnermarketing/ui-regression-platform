from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models.user import User
from models import db

def register_routes(app):
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user)
                flash('Login successful!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
        
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('login'))

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """Registration route for creating new users"""
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            confirm_password = request.form.get('confirm_password')
            
            # Validate input
            if not username or not password:
                flash('Username and password are required', 'error')
                return render_template('register.html')
            
            # Check password confirmation
            if confirm_password and password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('register.html')
            
            # Check if user already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'error')
                return render_template('register.html')
            
            # Create new user
            try:
                user = User(username=username)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                flash('Registration failed. Please try again.', 'error')
                return render_template('register.html')
        
        return render_template('register.html')