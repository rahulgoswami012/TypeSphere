from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from app.models.settings import UserSettings
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError

auth_bp = Blueprint('auth', __name__)

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 30)])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(4, 64)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Create Account')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data.strip()).first():
            raise ValidationError('Username is already taken. Please pick another.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError('Email address is already registered.')

class LoginForm(FlaskForm):
    email = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

# ==========================================
# 1. Simple Instant Registration
# ==========================================
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('typing.test_page'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            is_verified=True # Satisfies SQLite NOT NULL constraint and instantly activates account
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.flush()

        settings = UserSettings(user_id=user.id)
        db.session.add(settings)
        db.session.commit()

        login_user(user)
        flash(f'Account created successfully! Welcome to TypeSphere, {user.username}!', 'success')
        return redirect(url_for('typing.test_page'))

    return render_template('auth/register.html', form=form)

# ==========================================
# 2. Simple Direct Sign In
# ==========================================
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('typing.test_page'))
    
    form = LoginForm()
    if form.validate_on_submit():
        login_input = form.email.data.strip()
        user = User.query.filter((User.email == login_input.lower()) | (User.username == login_input)).first()
        
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f'Signed in as {user.username}!', 'success')
            next_p = request.args.get('next')
            return redirect(next_p) if next_p else redirect(url_for('typing.test_page'))

        flash('Invalid username or password. Please try again.', 'danger')

    return render_template('auth/login.html', form=form)

# ==========================================
# 3. Simple Logout
# ==========================================
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('typing.test_page'))