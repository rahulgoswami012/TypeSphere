import io
import csv
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response, session
from flask_login import login_required, current_user, login_user
from sqlalchemy import func, desc
from app import db
from app.models.user import User
from app.models.typing import TypingTest, TypingText
from app.models.challenge import DailyChallenge, Achievement
from app.models.feedback import ContactMessage, FeedbackItem, RatingReview, Announcement
from app.models.arcade_content import ArcadeContentItem, ArcadeGameConfig
from app.models.game import GameRecord
from app.models.admin import (
    RolePermission, AdminAuditLog, VisitorTraffic, 
    SecurityEvent, UserActivity, PlatformConfig
)
from app.services.admin_security import admin_permission_required, log_admin_action

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
@login_required
def enforce_admin_global():
    if not current_user.is_admin:
        flash("Unauthorized area. Access denied.", "danger")
        return redirect(url_for('typing.test_page'))

# ==========================================
# 1. Admin Dashboard Overview
# ==========================================
@admin_bp.route('')
@admin_bp.route('/')
@admin_bp.route('/index', endpoint='index')
@admin_permission_required('view_dashboard')
def dashboard():
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    # User Metrics
    total_users = User.query.count()
    new_today = User.query.filter(User.created_at >= today_start).count()
    new_week = User.query.filter(User.created_at >= week_start).count()
    new_month = User.query.filter(User.created_at >= month_start).count()
    suspended_users = User.query.filter((User.is_suspended == True) | (User.is_banned == True)).count()
    active_now = User.query.filter(User.last_active >= (now - timedelta(minutes=15))).count()

    # Typing Test Metrics
    total_tests = TypingTest.query.count()
    tests_today = TypingTest.query.filter(TypingTest.completed_at >= today_start).count()
    avg_wpm = db.session.query(func.avg(TypingTest.wpm)).scalar() or 0
    avg_acc = db.session.query(func.avg(TypingTest.accuracy)).scalar() or 0
    max_wpm = db.session.query(func.max(TypingTest.wpm)).scalar() or 0
    suspicious_tests = TypingTest.query.filter_by(suspicious=True).count()

    # Engagement Metrics
    games_played = GameRecord.query.count()
    daily_challenges = DailyChallenge.query.count()
    reviews_count = RatingReview.query.count()
    unread_contacts = ContactMessage.query.filter_by(is_read=False).count()

    # Traffic Metrics
    total_pageviews = VisitorTraffic.query.count()
    unique_visitors = db.session.query(func.count(func.distinct(VisitorTraffic.session_id))).scalar() or 0

    # Recent Audit Log for Super Admin preview
    recent_audits = AdminAuditLog.query.order_by(AdminAuditLog.created_at.desc()).limit(8).all()
    recent_security = SecurityEvent.query.order_by(SecurityEvent.created_at.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        stats={
            'total_users': total_users,
            'new_today': new_today,
            'new_week': new_week,
            'new_month': new_month,
            'suspended_users': suspended_users,
            'active_now': active_now,
            'total_tests': total_tests,
            'tests_today': tests_today,
            'avg_wpm': round(avg_wpm, 1),
            'avg_acc': round(avg_acc, 1),
            'max_wpm': round(max_wpm, 1),
            'suspicious_tests': suspicious_tests,
            'games_played': games_played,
            'reviews_count': reviews_count,
            'unread_contacts': unread_contacts,
            'total_pageviews': total_pageviews,
            'unique_visitors': unique_visitors
        },
        recent_audits=recent_audits,
        recent_security=recent_security
    )

# ==========================================
# 2. User Management & Impersonation
# ==========================================
@admin_bp.route('/users')
@admin_permission_required('manage_users')
def users_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')

    query = User.query
    if search:
        query = query.filter((User.username.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%")))
    if role_filter:
        query = query.filter_by(role=role_filter)
    if status_filter == 'suspended':
        query = query.filter_by(is_suspended=True)
    elif status_filter == 'banned':
        query = query.filter_by(is_banned=True)
    elif status_filter == 'active':
        query = query.filter_by(is_suspended=False, is_banned=False)

    users_page = query.order_by(User.id.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template(
        'admin/users.html',
        users=users_page,
        search=search,
        role_filter=role_filter,
        status_filter=status_filter,
        roles=RolePermission.ALL_ROLES
    )

@admin_bp.route('/users/<int:user_id>/profile')
@admin_permission_required('manage_users')
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    tests = TypingTest.query.filter_by(user_id=user.id).order_by(TypingTest.completed_at.desc()).limit(15).all()
    games = GameRecord.query.filter_by(user_id=user.id).order_by(GameRecord.created_at.desc()).limit(10).all()
    activities = UserActivity.query.filter_by(user_id=user.id).order_by(UserActivity.created_at.desc()).limit(20).all()
    return render_template(
        'admin/users_detail.html',
        user=user,
        tests=tests,
        games=games,
        activities=activities,
        roles=RolePermission.ALL_ROLES
    )

@admin_bp.route('/users/<int:user_id>/update-role', methods=['POST'])
@admin_permission_required('manage_users')
def update_user_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')

    if user.id == current_user.id:
        flash("Modifying your own role is restricted.", "danger")
        return redirect(url_for('admin.user_detail', user_id=user.id))

    if current_user.role != RolePermission.SUPER_ADMIN and new_role == RolePermission.SUPER_ADMIN:
        flash("Only Super Administrators can promote to Super Admin.", "danger")
        return redirect(url_for('admin.user_detail', user_id=user.id))

    old_role = user.role
    user.role = new_role
    db.session.commit()
    log_admin_action('ROLE_CHANGE', 'user', user.id, f"Role changed from {old_role} to {new_role}")
    flash(f"User @{user.username} updated to role: {new_role.upper()}", "success")
    return redirect(url_for('admin.user_detail', user_id=user.id))

@admin_bp.route('/users/<int:user_id>/moderate', methods=['POST'])
@admin_permission_required('manage_users')
def moderate_user(user_id):
    user = User.query.get_or_404(user_id)
    action = request.form.get('action')  # 'suspend', 'unsuspend', 'ban', 'unban', 'delete'
    reason = request.form.get('reason', 'Administrative moderation decision')

    if user.id == current_user.id:
        flash("You cannot perform moderation actions on your own profile.", "danger")
        return redirect(url_for('admin.user_detail', user_id=user.id))

    if action == 'suspend':
        user.is_suspended = True
        user.status_reason = reason
        log_admin_action('USER_SUSPEND', 'user', user.id, f"Suspended. Reason: {reason}")
        flash(f"User @{user.username} suspended.", "warning")
    elif action == 'unsuspend':
        user.is_suspended = False
        user.status_reason = None
        log_admin_action('USER_UNSUSPEND', 'user', user.id, "Suspension lifted")
        flash(f"User @{user.username} suspension lifted.", "success")
    elif action == 'ban':
        user.is_banned = True
        user.status_reason = reason
        log_admin_action('USER_BAN', 'user', user.id, f"Banned. Reason: {reason}")
        flash(f"User @{user.username} banned permanently.", "danger")
    elif action == 'unban':
        user.is_banned = False
        user.status_reason = None
        log_admin_action('USER_UNBAN', 'user', user.id, "Ban lifted")
        flash(f"User @{user.username} unbanned.", "success")
    elif action == 'delete':
        if current_user.role != RolePermission.SUPER_ADMIN:
            flash("Only Super Administrators can permanently delete user accounts.", "danger")
            return redirect(url_for('admin.user_detail', user_id=user.id))
        username = user.username
        db.session.delete(user)
        log_admin_action('USER_DELETE', 'user', user_id, f"Permanently deleted @{username}")
        db.session.commit()
        flash(f"User @{username} permanently deleted.", "info")
        return redirect(url_for('admin.users_list'))

    db.session.commit()
    return redirect(url_for('admin.user_detail', user_id=user.id))

@admin_bp.route('/users/<int:user_id>/impersonate', methods=['POST'])
@admin_permission_required('super_admin')
def impersonate_user(user_id):
    """Super Admin secure user simulation."""
    target_user = User.query.get_or_404(user_id)
    session['admin_impersonator_id'] = current_user.id
    log_admin_action('IMPERSONATION_START', 'user', target_user.id, f"SuperAdmin impersonated {target_user.username}")
    login_user(target_user)
    flash(f"Impersonating @{target_user.username}. Use top bar to exit.", "warning")
    return redirect(url_for('typing.test_page'))

@admin_bp.route('/stop-impersonation')
@login_required
def stop_impersonation():
    admin_id = session.pop('admin_impersonator_id', None)
    if not admin_id:
        return redirect(url_for('typing.test_page'))
    admin_user = User.query.get(admin_id)
    if admin_user:
        log_admin_action('IMPERSONATION_END', 'user', current_user.id, "Impersonation session concluded")
        login_user(admin_user)
        flash("Returned to Super Administrator console.", "info")
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('auth.logout'))

# ==========================================
# 3. Content & Passage Library Management
# ==========================================
@admin_bp.route('/passages')
@admin_permission_required('manage_content')
def passages_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    category = request.args.get('category', '')
    difficulty = request.args.get('difficulty', '')

    query = TypingText.query
    if search:
        query = query.filter((TypingText.title.ilike(f"%{search}%")) | (TypingText.content.ilike(f"%{search}%")))
    if category:
        query = query.filter_by(category=category)
    if difficulty:
        query = query.filter_by(difficulty=difficulty)

    passages_page = query.order_by(TypingText.id.desc()).paginate(page=page, per_page=15, error_out=False)
    categories = [c[0] for c in db.session.query(TypingText.category).distinct().all()]
    return render_template(
        'admin/passages.html',
        passages=passages_page,
        search=search,
        category=category,
        difficulty=difficulty,
        categories=categories
    )

@admin_bp.route('/passages/create', methods=['GET', 'POST'])
@admin_permission_required('manage_content')
def passage_create():
    if request.method == 'POST':
        title = request.form.get('title', 'Untitled Passage').strip()
        category = request.form.get('category', 'General').strip()
        difficulty = request.form.get('difficulty', 'Medium').strip()
        content = request.form.get('content', '').strip()
        source = request.form.get('source', 'Administrator').strip()
        is_code = request.form.get('is_code') == 'on'
        code_lang = request.form.get('code_lang') if is_code else None

        if not content:
            flash("Passage text content cannot be blank.", "danger")
            return render_template('admin/passage_form.html', action="Create", passage=None)

        passage = TypingText(
            title=title,
            category=category,
            difficulty=difficulty,
            content=content,
            source=source,
            is_code=is_code,
            code_lang=code_lang,
            created_by=current_user.username
        )
        passage.calculate_stats()
        db.session.add(passage)
        db.session.commit()
        log_admin_action('PASSAGE_CREATE', 'passage', passage.id, f"Added passage '{title}'")
        flash(f"Passage #{passage.id} ('{title}') added successfully.", "success")
        return redirect(url_for('admin.passages_list'))

    return render_template('admin/passage_form.html', action="Create", passage=None)

@admin_bp.route('/passages/<int:passage_id>/edit', methods=['GET', 'POST'])
@admin_permission_required('manage_content')
def passage_edit(passage_id):
    passage = TypingText.query.get_or_404(passage_id)
    if request.method == 'POST':
        passage.title = request.form.get('title', passage.title).strip()
        passage.category = request.form.get('category', passage.category).strip()
        passage.difficulty = request.form.get('difficulty', passage.difficulty).strip()
        passage.content = request.form.get('content', passage.content).strip()
        passage.source = request.form.get('source', passage.source).strip()
        passage.is_code = request.form.get('is_code') == 'on'
        passage.code_lang = request.form.get('code_lang') if passage.is_code else None
        passage.is_active = request.form.get('is_active') == 'on'
        passage.updated_by = current_user.username
        passage.calculate_stats()
        db.session.commit()
        log_admin_action('PASSAGE_UPDATE', 'passage', passage.id, f"Modified passage '{passage.title}'")
        flash("Passage updated successfully.", "success")
        return redirect(url_for('admin.passages_list'))

    return render_template('admin/passage_form.html', action="Edit", passage=passage)

@admin_bp.route('/passages/<int:passage_id>/delete', methods=['POST'])
@admin_permission_required('manage_content')
def passage_delete(passage_id):
    passage = TypingText.query.get_or_404(passage_id)
    title = passage.title
    db.session.delete(passage)
    db.session.commit()
    log_admin_action('PASSAGE_DELETE', 'passage', passage_id, f"Deleted '{title}'")
    flash("Passage deleted.", "info")
    return redirect(url_for('admin.passages_list'))

@admin_bp.route('/passages/<int:passage_id>/toggle-status', methods=['POST'])
@admin_permission_required('manage_content')
def passage_toggle(passage_id):
    passage = TypingText.query.get_or_404(passage_id)
    passage.is_active = not passage.is_active
    db.session.commit()
    log_admin_action('PASSAGE_TOGGLE', 'passage', passage.id, f"Active state: {passage.is_active}")
    return redirect(url_for('admin.passages_list'))

# ==========================================
# 4. Traffic & Visitor Analytics
# ==========================================
@admin_bp.route('/analytics')
@admin_permission_required('view_analytics')
def traffic_analytics():
    days = request.args.get('days', 30, type=int)
    cutoff = datetime.utcnow() - timedelta(days=days)

    total_views = VisitorTraffic.query.filter(VisitorTraffic.created_at >= cutoff).count()
    unique_sessions = db.session.query(func.count(func.distinct(VisitorTraffic.session_id))).filter(VisitorTraffic.created_at >= cutoff).scalar() or 0
    registered_views = VisitorTraffic.query.filter(VisitorTraffic.created_at >= cutoff, VisitorTraffic.user_id.isnot(None)).count()
    guest_views = total_views - registered_views

    # Popular Pages
    popular_pages = db.session.query(
        VisitorTraffic.path, func.count(VisitorTraffic.id).label('views')
    ).filter(VisitorTraffic.created_at >= cutoff).group_by(VisitorTraffic.path).order_by(desc('views')).limit(10).all()

    # Browser Breakdown
    browsers = db.session.query(
        VisitorTraffic.browser, func.count(VisitorTraffic.id).label('count')
    ).filter(VisitorTraffic.created_at >= cutoff).group_by(VisitorTraffic.browser).order_by(desc('count')).limit(6).all()

    # Device Breakdown
    devices = db.session.query(
        VisitorTraffic.device_type, func.count(VisitorTraffic.id).label('count')
    ).filter(VisitorTraffic.created_at >= cutoff).group_by(VisitorTraffic.device_type).all()

    return render_template(
        'admin/analytics.html',
        days=days,
        total_views=total_views,
        unique_sessions=unique_sessions,
        guest_views=guest_views,
        registered_views=registered_views,
        popular_pages=popular_pages,
        browsers=browsers,
        devices=devices
    )

# ==========================================
# 5. Leaderboard Moderation
# ==========================================
@admin_bp.route('/leaderboard')
@admin_permission_required('manage_leaderboard')
def leaderboard_manage():
    page = request.args.get('page', 1, type=int)
    filter_suspicious = request.args.get('suspicious', 'all')

    query = TypingTest.query.filter(TypingTest.user_id.isnot(None))
    if filter_suspicious == 'flagged':
        query = query.filter_by(suspicious=True)
    elif filter_suspicious == 'verified':
        query = query.filter_by(suspicious=False)

    tests_page = query.order_by(TypingTest.wpm.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/leaderboard.html', tests=tests_page, filter_suspicious=filter_suspicious)

@admin_bp.route('/leaderboard/test/<int:test_id>/toggle-flag', methods=['POST'])
@admin_permission_required('manage_leaderboard')
def test_toggle_flag(test_id):
    test = TypingTest.query.get_or_404(test_id)
    test.suspicious = not test.suspicious
    test.suspicion_reason = "Flagged manually by Administrator" if test.suspicious else None
    db.session.commit()
    log_admin_action('TEST_FLAG_TOGGLE', 'typing_test', test.id, f"Suspicious set to {test.suspicious}")
    flash(f"Test #{test.id} verification state toggled.", "success")
    return redirect(url_for('admin.leaderboard_manage'))

@admin_bp.route('/leaderboard/test/<int:test_id>/delete', methods=['POST'])
@admin_permission_required('manage_leaderboard')
def test_delete(test_id):
    test = TypingTest.query.get_or_404(test_id)
    db.session.delete(test)
    db.session.commit()
    log_admin_action('TEST_RECORD_DELETE', 'typing_test', test_id, "Record deleted from leaderboards")
    flash("Typing score record removed.", "info")
    return redirect(url_for('admin.leaderboard_manage'))

# ==========================================
# 6. Security Center & Uneditable Audit Logs
# ==========================================
@admin_bp.route('/security')
@admin_permission_required('view_security')
def security_center():
    page = request.args.get('page', 1, type=int)
    events = SecurityEvent.query.order_by(SecurityEvent.created_at.desc()).paginate(page=page, per_page=25, error_out=False)
    failed_logins = SecurityEvent.query.filter_by(event_type='FAILED_LOGIN').count()
    critical_events = SecurityEvent.query.filter_by(severity='CRITICAL').count()
    return render_template(
        'admin/security.html',
        events=events,
        failed_logins=failed_logins,
        critical_events=critical_events
    )

@admin_bp.route('/audit-logs')
@admin_permission_required('view_audit_logs')
def audit_logs():
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '').strip()

    query = AdminAuditLog.query
    if action_filter:
        query = query.filter(AdminAuditLog.action.ilike(f"%{action_filter}%"))
    logs_page = query.order_by(AdminAuditLog.created_at.desc()).paginate(page=page, per_page=30, error_out=False)
    return render_template('admin/audit_logs.html', logs=logs_page, action_filter=action_filter)

# ==========================================
# 7. Platform Settings & Data Export
# ==========================================
@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_permission_required('manage_settings')
def system_settings():
    if request.method == 'POST':
        for key in ['maintenance_mode', 'allow_registrations', 'default_test_duration', 'min_wpm_cutoff']:
            val = request.form.get(key, '').strip()
            cfg = PlatformConfig.query.filter_by(key=key).first()
            if not cfg:
                cfg = PlatformConfig(key=key, value=val, updated_by=current_user.username)
                db.session.add(cfg)
            else:
                cfg.value = val
                cfg.updated_by = current_user.username
        db.session.commit()
        log_admin_action('PLATFORM_CONFIG_UPDATE', 'settings', details="Updated platform runtime configs")
        flash("Platform parameters updated.", "success")
        return redirect(url_for('admin.system_settings'))

    configs = {c.key: c.value for c in PlatformConfig.query.all()}
    return render_template('admin/settings.html', configs=configs)

@admin_bp.route('/export/<data_type>')
@admin_permission_required('export_data')
def export_csv(data_type):
    """Clean CSV data export for Super Admins and Analysts."""
    log_admin_action('EXPORT_DATA', 'system', details=f"Exported {data_type}.csv")
    output = io.StringIO()
    writer = csv.writer(output)
    if data_type == 'users':
        writer.writerow(['ID', 'Username', 'Email', 'Role', 'Suspended', 'Banned', 'Elo', 'Created_At'])
        for u in User.query.all():
            writer.writerow([u.id, u.username, u.email, u.role, u.is_suspended, u.is_banned, u.elo_rating, u.created_at])
    elif data_type == 'tests':
        writer.writerow(['ID', 'User_ID', 'Mode', 'WPM', 'Accuracy', 'Consistency', 'Duration', 'Suspicious', 'Date'])
        for t in TypingTest.query.limit(2000).all():
            writer.writerow([t.id, t.user_id, t.mode, t.wpm, t.accuracy, t.consistency, t.duration, t.suspicious, t.completed_at])
    elif data_type == 'audit':
        writer.writerow(['ID', 'Admin', 'Action', 'Target_Type', 'Target_ID', 'IP', 'Date'])
        for a in AdminAuditLog.query.order_by(AdminAuditLog.id.desc()).limit(2000).all():
            writer.writerow([a.id, a.admin_username, a.action, a.target_type, a.target_id, a.ip_address, a.created_at])
    else:
        return "Unknown dataset", 400

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=typesphere_{data_type}_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )