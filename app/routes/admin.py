from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from datetime import date, datetime
from app import db
from app.models.user import User
from app.models.typing import TypingTest, TypingText
from app.models.challenge import DailyChallenge
from app.models.feedback import ContactMessage, FeedbackItem, RatingReview, Announcement, SiteSetting

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
@login_required
def require_admin_auth():
    if not current_user.is_admin:
        abort(403)

@admin_bp.route('/')
def index():
    total_users = User.query.count()
    total_tests = TypingTest.query.count()
    suspicious_tests = TypingTest.query.filter_by(suspicious=True).count()
    unread_messages = ContactMessage.query.filter_by(is_read=False).count()
    pending_feedback = FeedbackItem.query.filter_by(status='Pending').count()
    
    today = date.today()
    current_daily = DailyChallenge.query.filter_by(target_date=today).first()
    recent_suspicious = TypingTest.query.filter_by(suspicious=True).order_by(TypingTest.completed_at.desc()).limit(10).all()

    return render_template(
        'admin/index.html',
        total_users=total_users,
        total_tests=total_tests,
        suspicious_count=suspicious_tests,
        unread_messages=unread_messages,
        pending_feedback=pending_feedback,
        current_daily=current_daily,
        recent_suspicious=recent_suspicious
    )

# ==========================================
# 1. User Management CRUD
# ==========================================
@admin_bp.route('/users')
def manage_users():
    search = request.args.get('q', '').strip()
    query = User.query
    if search:
        query = query.filter((User.username.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%")))
    users = query.order_by(User.id.desc()).all()
    return render_template('admin/users.html', users=users, search=search)

@admin_bp.route('/users/<int:user_id>/toggle-role', methods=['POST'])
def toggle_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot demote your own active account.", 'warning')
        return redirect(url_for('admin.manage_users'))

    user.role = 'admin' if user.role == 'user' else 'user'
    db.session.commit()
    flash(f"User @{user.username} role modified to {user.role.upper()}.", 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Cannot delete your own account.", 'danger')
        return redirect(url_for('admin.manage_users'))

    db.session.delete(user)
    db.session.commit()
    flash(f"User @{user.username} deleted permanently.", 'info')
    return redirect(url_for('admin.manage_users'))

# ==========================================
# 2. Content & Prompt Management CRUD
# ==========================================
@admin_bp.route('/content', methods=['GET', 'POST'])
def manage_content():
    if request.method == 'POST':
        category = request.form.get('category', 'General').strip()
        difficulty = request.form.get('difficulty', 'moderate').strip()
        content = request.form.get('content', '').strip()
        is_code = request.form.get('is_code') == 'on'
        code_lang = request.form.get('code_lang', '').strip()

        if content:
            new_text = TypingText(
                category=category,
                difficulty=difficulty,
                content=content,
                is_code=is_code,
                code_lang=code_lang if is_code else None
            )
            db.session.add(new_text)
            db.session.commit()
            flash('New typing prompt added to database.', 'success')
            return redirect(url_for('admin.manage_content'))

    texts = TypingText.query.order_by(TypingText.id.desc()).all()
    return render_template('admin/content.html', texts=texts)

@admin_bp.route('/content/<int:text_id>/delete', methods=['POST'])
def delete_content(text_id):
    prompt = TypingText.query.get_or_404(text_id)
    db.session.delete(prompt)
    db.session.commit()
    flash(f"Prompt #{text_id} removed.", 'info')
    return redirect(url_for('admin.manage_content'))

# ==========================================
# 3. Feedback, Reviews & Contact Management
# ==========================================
@admin_bp.route('/feedback-management')
def manage_feedback():
    feedback_items = FeedbackItem.query.order_by(FeedbackItem.id.desc()).all()
    reviews = RatingReview.query.order_by(RatingReview.id.desc()).all()
    contact_msgs = ContactMessage.query.order_by(ContactMessage.id.desc()).all()
    announcements = Announcement.query.order_by(Announcement.id.desc()).all()

    return render_template(
        'admin/feedback_manage.html',
        feedback_items=feedback_items,
        reviews=reviews,
        contact_msgs=contact_msgs,
        announcements=announcements
    )

@admin_bp.route('/feedback/<int:item_id>/status', methods=['POST'])
def update_feedback_status(item_id):
    item = FeedbackItem.query.get_or_404(item_id)
    item.status = request.form.get('status', item.status)
    item.admin_response = request.form.get('admin_response', item.admin_response)
    db.session.commit()
    flash(f"Feedback #{item.id} status updated.", 'success')
    return redirect(url_for('admin.manage_feedback'))

@admin_bp.route('/contact/<int:msg_id>/toggle-read', methods=['POST'])
def toggle_contact_read(msg_id):
    msg = ContactMessage.query.get_or_404(msg_id)
    msg.is_read = not msg.is_read
    db.session.commit()
    return redirect(url_for('admin.manage_feedback'))

@admin_bp.route('/contact/<int:msg_id>/delete', methods=['POST'])
def delete_contact(msg_id):
    msg = ContactMessage.query.get_or_404(msg_id)
    db.session.delete(msg)
    db.session.commit()
    flash('Contact message deleted.', 'info')
    return redirect(url_for('admin.manage_feedback'))

@admin_bp.route('/announcements/create', methods=['POST'])
def create_announcement():
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    if title and content:
        # Deactivate old announcements
        Announcement.query.update({'is_active': False})
        ann = Announcement(title=title, content=content, is_active=True)
        db.session.add(ann)
        db.session.commit()
        flash('New platform announcement published.', 'success')
    return redirect(url_for('admin.manage_feedback'))

@admin_bp.route('/announcements/<int:ann_id>/delete', methods=['POST'])
def delete_announcement(ann_id):
    ann = Announcement.query.get_or_404(ann_id)
    db.session.delete(ann)
    db.session.commit()
    flash('Announcement deleted.', 'info')
    return redirect(url_for('admin.manage_feedback'))

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
        flash("Daily Challenge published globally.", 'success')

    return redirect(url_for('admin.index'))

@admin_bp.route('/tests/<int:test_id>/clear-flag', methods=['POST'])
def clear_flag(test_id):
    test = TypingTest.query.get_or_404(test_id)
    test.suspicious = False
    test.suspicion_reason = None
    db.session.commit()
    flash(f"Test #{test.id} reinstated on leaderboards.", 'success')
    return redirect(url_for('admin.index'))