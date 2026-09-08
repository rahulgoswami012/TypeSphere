# (In app/routes/auth.py)
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from app.models.settings import UserSettings
from app.services.admin_security import record_user_activity, log_security_incident
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError

auth_bp = Blueprint('auth', __name__)

class LoginForm(FlaskForm):
    email = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 30)])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(4, 64)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Create Account')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data.strip()).first():
            raise ValidationError('Username is already taken.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError('Email address is already registered.')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard') if current_user.is_admin else url_for('typing.test_page'))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            role='user'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        settings = UserSettings(user_id=user.id)
        db.session.add(settings)
        db.session.commit()

        record_user_activity(user.id, 'REGISTER', 'Auth', 'User registered new account')
        login_user(user)
        flash(f'Account created successfully. Welcome, {user.username}!', 'success')
        return redirect(url_for('typing.test_page'))

    return render_template('auth/register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard') if current_user.is_admin else url_for('typing.test_page'))

    form = LoginForm()
    if form.validate_on_submit():
        login_input = form.email.data.strip()
        user = User.query.filter((User.email == login_input.lower()) | (User.username == login_input)).first()

        if user and user.check_password(form.password.data):
            # Check Account Moderation Status
            if user.is_banned:
                log_security_incident('BANNED_USER_LOGIN_ATTEMPT', 'MEDIUM', f"Banned user {user.username} tried logging in", identifier=user.username)
                flash(f"This account has been permanently banned: {user.status_reason or 'Terms violation'}", "danger")
                return render_template('auth/login.html', form=form)
            
            if user.is_suspended:
                log_security_incident('SUSPENDED_USER_LOGIN_ATTEMPT', 'LOW', f"Suspended user {user.username} tried logging in", identifier=user.username)
                flash(f"This account is temporarily suspended: {user.status_reason or 'Investigation pending'}", "warning")
                return render_template('auth/login.html', form=form)

            login_user(user)
            record_user_activity(user.id, 'LOGIN', 'Auth', f"User signed in via {request.user_agent.platform}")

            # Routing separation: Admins go to Admin Center; Typists go to public typing
            if user.is_admin:
                flash(f"Admin console authorized. Welcome, {user.username}.", "info")
                return redirect(url_for('admin.dashboard'))

            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('typing.test_page'))

        log_security_incident('FAILED_LOGIN', 'MEDIUM', f"Invalid credentials supplied for identifier '{login_input}'", identifier=login_input)
        flash('Invalid username/email or password.', 'danger')

    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    record_user_activity(current_user.id, 'LOGOUT', 'Auth', 'User logged out')
    logout_user()
    flash('Signed out successfully.', 'info')
    return redirect(url_for('typing.test_page'))