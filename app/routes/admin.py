from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from datetime import date
from app import db
from app.models.user import User
from app.models.typing import TypingTest, TypingText
from app.models.challenge import DailyChallenge

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
@login_required
def require_admin():
    if not current_user.is_admin:
        abort(403)

@admin_bp.route('/')
def index():
    total_users = User.query.count()
    total_tests = TypingTest.query.count()
    suspicious_tests = TypingTest.query.filter_by(suspicious=True).count()
    recent_suspicious = TypingTest.query.filter_by(suspicious=True).order_by(TypingTest.completed_at.desc()).limit(15).all()
    all_users = User.query.order_by(User.created_at.desc()).limit(25).all()
    
    today = date.today()
    current_daily = DailyChallenge.query.filter_by(target_date=today).first()

    return render_template(
        'admin/index.html',
        total_users=total_users,
        total_tests=total_tests,
        suspicious_count=suspicious_tests,
        recent_suspicious=recent_suspicious,
        users=all_users,
        current_daily=current_daily
    )

@admin_bp.route('/texts', methods=['GET', 'POST'])
def manage_texts():
    if request.method == 'POST':
        category = request.form.get('category', 'General').strip()
        content = request.form.get('content', '').strip()
        is_code = request.form.get('is_code') == 'on'
        code_lang = request.form.get('code_lang', '').strip()

        if content:
            new_text = TypingText(
                category=category,
                content=content,
                is_code=is_code,
                code_lang=code_lang if is_code else None
            )
            db.session.add(new_text)
            db.session.commit()
            flash('Prompt text saved to system database.', 'success')
            return redirect(url_for('admin.manage_texts'))

    texts = TypingText.query.order_by(TypingText.id.desc()).all()
    return render_template('admin/texts.html', texts=texts)

@admin_bp.route('/texts/<int:text_id>/delete', methods=['POST'])
def delete_text(text_id):
    prompt = TypingText.query.get_or_404(text_id)
    db.session.delete(prompt)
    db.session.commit()
    flash(f"Prompt #{text_id} deleted successfully.", 'info')
    return redirect(url_for('admin.manage_texts'))

@admin_bp.route('/tests/<int:test_id>/clear-flag', methods=['POST'])
def clear_flag(test_id):
    test = TypingTest.query.get_or_404(test_id)
    test.suspicious = False
    test.suspicion_reason = None
    db.session.commit()
    flash(f"Test #{test.id} marked clean and reinstated on public boards.", 'success')
    return redirect(url_for('admin.index'))

@admin_bp.route('/users/<int:user_id>/toggle-role', methods=['POST'])
def toggle_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot demote your own active admin account.", 'warning')
        return redirect(url_for('admin.index'))

    user.role = 'admin' if user.role == 'user' else 'user'
    db.session.commit()
    flash(f"User @{user.username} role updated to: {user.role.upper()}", 'success')
    return redirect(url_for('admin.index'))

@admin_bp.route('/daily/create', methods=['POST'])
def create_daily():
    title = request.form.get('title', 'Official Daily Challenge').strip()
    content = request.form.get('content', '').strip()
    today = date.today()

    if content:
        challenge = DailyChallenge.query.filter_by(target_date=today).first()
        if challenge:
            challenge.title = title
            challenge.content = content
        else:
            challenge = DailyChallenge(target_date=today, title=title, content=content)
            db.session.add(challenge)
        db.session.commit()
        flash("Today's official benchmark passage published globally.", 'success')

    return redirect(url_for('admin.index'))