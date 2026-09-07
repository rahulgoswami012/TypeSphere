from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from datetime import date
from app import db
from app.models.user import User
from app.models.typing import TypingTest, TypingText
from app.models.challenge import DailyChallenge
from app.models.feedback import ContactMessage, FeedbackItem, RatingReview, Announcement
from app.models.arcade_content import ArcadeContentItem, ArcadeGameConfig

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
    total_arcade_items = ArcadeContentItem.query.count()

    today = date.today()
    current_daily = DailyChallenge.query.filter_by(target_date=today).first()
    recent_suspicious = TypingTest.query.filter_by(suspicious=True).order_by(TypingTest.completed_at.desc()).limit(8).all()

    return render_template(
        'admin/index.html',
        total_users=total_users,
        total_tests=total_tests,
        suspicious_count=suspicious_tests,
        unread_messages=unread_messages,
        pending_feedback=pending_feedback,
        total_arcade_items=total_arcade_items,
        current_daily=current_daily,
        recent_suspicious=recent_suspicious
    )

# ==========================================
# Arcade & Content Library CRUD
# ==========================================
@admin_bp.route('/arcade')
def manage_arcade():
    items = ArcadeContentItem.query.order_by(ArcadeContentItem.id.desc()).limit(60).all()
    return render_template('admin/arcade_manage.html', items=items)

@admin_bp.route('/arcade/add-word', methods=['POST'])
def add_arcade_word():
    game_mode = request.form.get('game_mode', 'falling_words')
    difficulty = request.form.get('difficulty', 'intermediate')
    target_text = request.form.get('target_text', '').strip()
    category = request.form.get('category', 'general')

    if target_text:
        item = ArcadeContentItem(
            game_mode=game_mode,
            difficulty=difficulty,
            target_text=target_text,
            category=category,
            word_length=len(target_text)
        )
        db.session.add(item)
        db.session.commit()
        flash(f"Word '{target_text}' added to {game_mode.title()}.", 'success')

    return redirect(url_for('admin.manage_arcade'))

@admin_bp.route('/arcade/delete-word/<int:item_id>', methods=['POST'])
def delete_arcade_word(item_id):
    item = ArcadeContentItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Arcade word removed successfully.', 'info')
    return redirect(url_for('admin.manage_arcade'))