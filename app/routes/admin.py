"""
TypeSphere Control Center - Centralized Operational Controller
Manages users, custom roles, permissions, passage CMS, arcade games,
tactical challenges, curriculum, certificates, community, website control,
feature flags, security, analytics, active sessions, and data retention.
"""

import io
import os
import csv
import json
import hashlib
import time
import sys
import re
from datetime import datetime, timedelta, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response, session
from flask_login import login_required, current_user, login_user
from sqlalchemy import func, desc, or_, text
from app import db
from app.models.user import User
from app.models.typing import (
    TypingTest, TypingText, TypingDNA,
    PassageTag, PassageCollection, PassageReport
)
from app.models.challenge import DailyChallenge, Achievement
from app.models.curriculum import LessonStage
from app.models.feedback import ContactMessage, FeedbackItem, RatingReview, Announcement
from app.models.arcade_content import ArcadeGameConfig, ArcadeContentItem
from app.models.game import GameRecord
from app.models.admin import (
    RolePermission, AdminAuditLog, VisitorTraffic, 
    SecurityEvent, UserActivity, PlatformConfig,
    Permission, CustomRole, BlockedIP, FeatureFlag,
    SiteNavigationItem, SYSTEM_PERMISSIONS
)
from app.services.admin_security import (
    admin_permission_required, log_admin_action, 
    log_security_incident, block_ip, unblock_ip,
    get_ip_location, parse_device_os
)
from app.services.passage_service import PassageService
from app.utils.timezone import to_ist, now_ist, ist_today

admin_bp = Blueprint('admin', __name__)


@admin_bp.before_request
@login_required
def enforce_admin_global():
    if not current_user.is_admin:
        flash("Unauthorized flight sector. Access denied.", "danger")
        return redirect(url_for('typing.test_page'))


def seed_default_roles_if_empty():
    try:
        if CustomRole.query.count() == 0:
            defaults = [
                ("Content Manager", "Manages typing passages, daily challenges, and curriculum.", ["typing.*", "challenges.*", "academy.*"]),
                ("Flight Moderator", "Moderates user accounts, leaderboards, and community reviews.", ["users.view", "users.profile", "users.moderate", "reviews.*", "challenges.moderate"]),
                ("Telemetry Analyst", "Access to traffic, device analytics, and performance curves.", ["analytics.*"]),
                ("Support Dispatch", "Handles user inquiries, feedback messages, and basic profile inspection.", ["users.view", "users.profile", "feedback.*"])
            ]
            all_perms = {p.code: p for p in Permission.query.all()}
            for r_name, r_desc, p_patterns in defaults:
                r = CustomRole(name=r_name, description=r_desc, is_active=True, created_by="System")
                matched = []
                for pat in p_patterns:
                    if pat.endswith(".*"):
                        prefix = pat.split(".*")[0]
                        matched.extend([p for code, p in all_perms.items() if code.startswith(prefix + ".")])
                    elif pat in all_perms:
                        matched.append(all_perms[pat])
                r.permissions = list(set(matched))
                db.session.add(r)
            db.session.commit()
    except Exception:
        db.session.rollback()


def purge_keyboard_quest_config():
    try:
        kq = ArcadeGameConfig.query.filter_by(game_slug='keyboard_quest').first()
        if kq:
            db.session.delete(kq)
            db.session.commit()
    except Exception:
        db.session.rollback()


# ==============================================================
# 1. COMMAND CENTER DASHBOARD & LIVE OPERATIONS
# ==============================================================

@admin_bp.route('')
@admin_bp.route('/')
@admin_bp.route('/index', endpoint='index')
@admin_permission_required('analytics.dashboard')
def dashboard():
    seed_default_roles_if_empty()
    purge_keyboard_quest_config()

    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    total_users = User.query.count()
    new_today = User.query.filter(User.created_at >= today_start).count()
    new_week = User.query.filter(User.created_at >= week_start).count()
    new_month = User.query.filter(User.created_at >= month_start).count()
    suspended_users = User.query.filter((User.is_suspended == True) | (User.is_banned == True)).count()
    active_now = User.query.filter(User.last_active >= (now - timedelta(minutes=30))).count()

    total_tests = TypingTest.query.count()
    tests_today = TypingTest.query.filter(TypingTest.completed_at >= today_start).count()
    avg_wpm = db.session.query(func.avg(TypingTest.wpm)).scalar() or 0
    avg_acc = db.session.query(func.avg(TypingTest.accuracy)).scalar() or 0
    max_wpm = db.session.query(func.max(TypingTest.wpm)).scalar() or 0
    suspicious_tests = TypingTest.query.filter_by(suspicious=True).count()

    games_played = GameRecord.query.count()
    roles_count = CustomRole.query.count()
    blocked_ips_count = BlockedIP.query.count()
    unread_contacts = ContactMessage.query.filter_by(is_read=False).count()

    total_pageviews = VisitorTraffic.query.count()
    unique_visitors = db.session.query(func.count(func.distinct(VisitorTraffic.session_id))).scalar() or 0

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
            'roles_count': roles_count,
            'blocked_ips_count': blocked_ips_count,
            'unread_contacts': unread_contacts,
            'total_pageviews': total_pageviews,
            'unique_visitors': unique_visitors
        },
        recent_audits=recent_audits,
        recent_security=recent_security
    )


# ==============================================================
# 2. LIVE ACTIVE SESSIONS MONITOR
# ==============================================================

def get_live_active_sessions_data():
    cutoff = datetime.utcnow() - timedelta(minutes=30)
    recent_traffic = db.session.query(VisitorTraffic).filter(
        VisitorTraffic.created_at >= cutoff
    ).order_by(VisitorTraffic.created_at.desc()).limit(80).all()

    seen_sessions = set()
    active_sessions = []
    registered_active = 0
    guest_active = 0

    for t in recent_traffic:
        identifier = f"{t.ip_address}-{t.session_id}"
        if identifier in seen_sessions:
            continue
        seen_sessions.add(identifier)

        user_role = "guest"
        role_priority = 4
        username = "Guest Flight"
        callsign = None

        if t.user_id:
            user = User.query.get(t.user_id)
            if user:
                username = f"@{user.username}"
                callsign = user.display_callsign
                if user.is_super_admin:
                    user_role = "super_admin"
                    role_priority = 1
                elif user.is_admin:
                    user_role = "admin"
                    role_priority = 2
                else:
                    user_role = "pilot"
                    role_priority = 3
                registered_active += 1
        else:
            guest_active += 1

        loc_str = get_ip_location(t.ip_address)

        active_sessions.append({
            'username': username,
            'callsign': callsign,
            'user_role': user_role,
            'role_priority': role_priority,
            'ip_address': t.ip_address,
            'location_approx': loc_str,
            'device_type': t.device_type,
            'os': t.os,
            'browser': t.browser,
            'created_at_raw': t.created_at,
            'last_seen': to_ist(t.created_at).strftime('%H:%M:%S')
        })

    active_sessions.sort(key=lambda s: (s['role_priority'], -s['created_at_raw'].timestamp()))

    return {
        'sessions': active_sessions,
        'active_count': len(active_sessions),
        'registered_active': registered_active,
        'guest_active': guest_active
    }


@admin_bp.route('/sessions')
@admin_permission_required('users.view')
def live_sessions():
    data = get_live_active_sessions_data()
    return render_template(
        'admin/sessions.html',
        sessions=data['sessions'],
        active_count=data['active_count'],
        registered_active=data['registered_active'],
        guest_active=data['guest_active']
    )


@admin_bp.route('/api/sessions')
@admin_permission_required('users.view')
def api_live_sessions():
    data = get_live_active_sessions_data()
    return jsonify({
        'success': True,
        'sessions': data['sessions'],
        'active_count': data['active_count'],
        'registered_active': data['registered_active'],
        'guest_active': data['guest_active']
    })


# ==============================================================
# 3. ROLE BUILDER & CUSTOM ROLES
# ==============================================================

@admin_bp.route('/roles')
@admin_permission_required('roles.view')
def roles_list():
    seed_default_roles_if_empty()
    roles = CustomRole.query.order_by(CustomRole.id.asc()).all()
    return render_template(
        'admin/roles.html',
        roles=roles,
        total_roles=len(roles),
        active_roles=sum(1 for r in roles if r.is_active),
        disabled_roles=len(roles) - sum(1 for r in roles if r.is_active),
        delegated_users_count=db.session.query(func.count(func.distinct(User.id))).join(User.custom_roles).count()
    )


@admin_bp.route('/roles/create', methods=['GET', 'POST'])
@admin_permission_required('roles.manage')
def role_create():
    all_permissions = Permission.query.order_by(Permission.category.asc(), Permission.name.asc()).all()
    grouped_perms = {}
    for p in all_permissions:
        grouped_perms.setdefault(p.category, []).append(p)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        is_active = request.form.get('is_active') == 'on'
        selected_perm_ids = request.form.getlist('permissions')

        if not name:
            flash("Role designation cannot be empty.", "danger")
            return render_template('admin/role_form.html', action='Create', role=None, grouped_perms=grouped_perms)

        if CustomRole.query.filter_by(name=name).first():
            flash(f"A role with the designation '{name}' already exists.", "danger")
            return render_template('admin/role_form.html', action='Create', role=None, grouped_perms=grouped_perms)

        new_role = CustomRole(name=name, description=description, is_active=is_active, created_by=current_user.username)
        if selected_perm_ids:
            perms = Permission.query.filter(Permission.id.in_(selected_perm_ids)).all()
            new_role.permissions.extend(perms)

        db.session.add(new_role)
        db.session.commit()
        log_admin_action('ROLE_CREATED', 'role', new_role.id, f"Created role '{name}'")
        flash(f"Custom role '{name}' established.", "success")
        return redirect(url_for('admin.roles_list'))

    return render_template('admin/role_form.html', action='Create', role=None, grouped_perms=grouped_perms)


@admin_bp.route('/roles/<int:role_id>/edit', methods=['GET', 'POST'])
@admin_permission_required('roles.manage')
def role_edit(role_id):
    role = CustomRole.query.get_or_404(role_id)
    all_permissions = Permission.query.order_by(Permission.category.asc(), Permission.name.asc()).all()
    grouped_perms = {}
    for p in all_permissions:
        grouped_perms.setdefault(p.category, []).append(p)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        is_active = request.form.get('is_active') == 'on'
        selected_perm_ids = request.form.getlist('permissions')

        role.name = name
        role.description = description
        role.is_active = is_active
        role.updated_by = current_user.username
        role.permissions = Permission.query.filter(Permission.id.in_(selected_perm_ids)).all() if selected_perm_ids else []

        db.session.commit()
        log_admin_action('ROLE_UPDATED', 'role', role.id, f"Updated role '{name}'")
        flash(f"Custom role '{name}' updated.", "success")
        return redirect(url_for('admin.roles_list'))

    return render_template('admin/role_form.html', action='Edit', role=role, grouped_perms=grouped_perms)


@admin_bp.route('/roles/<int:role_id>/toggle', methods=['POST'])
@admin_permission_required('roles.manage')
def role_toggle(role_id):
    role = CustomRole.query.get_or_404(role_id)
    role.is_active = not role.is_active
    db.session.commit()
    flash(f"Role '{role.name}' {'activated' if role.is_active else 'disabled'}.", "success")
    return redirect(url_for('admin.roles_list'))


@admin_bp.route('/roles/<int:role_id>/delete', methods=['POST'])
@admin_permission_required('roles.delete')
def role_delete(role_id):
    role = CustomRole.query.get_or_404(role_id)
    if role.is_system:
        flash("System roles cannot be deleted.", "danger")
        return redirect(url_for('admin.roles_list'))
    db.session.delete(role)
    db.session.commit()
    flash("Role deleted.", "info")
    return redirect(url_for('admin.roles_list'))


@admin_bp.route('/roles/<int:role_id>/duplicate', methods=['POST'])
@admin_permission_required('roles.manage')
def role_duplicate(role_id):
    original = CustomRole.query.get_or_404(role_id)
    copy_name = f"Copy of {original.name}"
    cloned = CustomRole(name=copy_name, description=original.description, is_active=original.is_active, created_by=current_user.username)
    cloned.permissions = list(original.permissions)
    db.session.add(cloned)
    db.session.commit()
    flash(f"Cloned role '{copy_name}'.", "success")
    return redirect(url_for('admin.role_edit', role_id=cloned.id))


# ==============================================================
# 4. USER DIRECTORY & MODERATION
# ==============================================================

@admin_bp.route('/users')
@admin_permission_required('users.view')
def users_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')

    query = User.query
    if search:
        query = query.filter(or_(User.username.ilike(f"%{search}%"), User.email.ilike(f"%{search}%"), User.callsign.ilike(f"%{search}%")))
    if status_filter == 'suspended': query = query.filter_by(is_suspended=True)
    elif status_filter == 'banned': query = query.filter_by(is_banned=True)
    elif status_filter == 'active': query = query.filter_by(is_suspended=False, is_banned=False)

    users_page = query.order_by(User.id.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/users.html', users=users_page, search=search, status_filter=status_filter, roles=CustomRole.query.all())


@admin_bp.route('/users/<int:user_id>/profile')
@admin_permission_required('users.profile')
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    all_perms = Permission.query.all()
    effective_codes = user.effective_permissions
    grouped_effective = {}
    for p in all_perms:
        is_granted = ('*' in effective_codes) or (p.code in effective_codes)
        grouped_effective.setdefault(p.category, []).append((p, is_granted))

    return render_template(
        'admin/users_detail.html',
        user=user,
        tests=TypingTest.query.filter_by(user_id=user.id).order_by(TypingTest.completed_at.desc()).limit(15).all(),
        games=GameRecord.query.filter_by(user_id=user.id).order_by(GameRecord.created_at.desc()).limit(10).all(),
        activities=UserActivity.query.filter_by(user_id=user.id).order_by(UserActivity.created_at.desc()).limit(20).all(),
        all_roles=CustomRole.query.filter_by(is_active=True).all(),
        recent_traffic=VisitorTraffic.query.filter_by(user_id=user.id).order_by(VisitorTraffic.created_at.desc()).first(),
        grouped_effective=grouped_effective,
        to_ist=to_ist
    )


@admin_bp.route('/users/<int:user_id>/assign-role', methods=['POST'])
@admin_permission_required('roles.manage')
def assign_user_role(user_id):
    user = User.query.get_or_404(user_id)
    role_id = request.form.get('role_id', type=int)
    role = CustomRole.query.get_or_404(role_id)
    if role not in user.custom_roles:
        user.custom_roles.append(role)
        db.session.commit()
        flash(f"Assigned role '{role.name}' to @{user.username}.", "success")
    return redirect(url_for('admin.user_detail', user_id=user.id))


@admin_bp.route('/users/<int:user_id>/remove-role/<int:role_id>', methods=['POST'])
@admin_permission_required('roles.manage')
def remove_user_role(user_id, role_id):
    user = User.query.get_or_404(user_id)
    role = CustomRole.query.get_or_404(role_id)
    if role in user.custom_roles:
        user.custom_roles.remove(role)
        db.session.commit()
        flash(f"Removed role '{role.name}' from @{user.username}.", "info")
    return redirect(url_for('admin.user_detail', user_id=user.id))


@admin_bp.route('/users/<int:user_id>/moderate', methods=['POST'])
@admin_permission_required('users.moderate')
def moderate_user(user_id):
    user = User.query.get_or_404(user_id)
    action = request.form.get('action')
    reason = request.form.get('reason', 'Administrative decision').strip()

    if user.is_super_admin:
        flash("Super Admin cannot be moderated.", "danger")
        return redirect(url_for('admin.user_detail', user_id=user.id))

    if action == 'suspend': user.is_suspended = True; user.status_reason = reason
    elif action == 'unsuspend': user.is_suspended = False; user.status_reason = None
    elif action == 'ban': user.is_banned = True; user.status_reason = reason
    elif action == 'unban': user.is_banned = False; user.status_reason = None
    elif action == 'delete':
        db.session.delete(user)
        db.session.commit()
        flash(f"User @{user.username} deleted.", "info")
        return redirect(url_for('admin.users_list'))

    db.session.commit()
    flash(f"Updated user @{user.username}.", "success")
    return redirect(url_for('admin.user_detail', user_id=user.id))


@admin_bp.route('/users/bulk-action', methods=['POST'])
@admin_permission_required('users.moderate')
def users_bulk_action():
    action = request.form.get('action')
    user_ids = request.form.getlist('selected_user_ids', type=int)
    users = User.query.filter(User.id.in_(user_ids)).all()
    count = 0
    for u in users:
        if not u.is_super_admin and u.id != current_user.id:
            if action == 'suspend': u.is_suspended = True; count += 1
            elif action == 'unsuspend': u.is_suspended = False; count += 1
    db.session.commit()
    flash(f"Bulk action applied to {count} users.", "success")
    return redirect(url_for('admin.users_list'))


@admin_bp.route('/users/<int:user_id>/impersonate', methods=['POST'])
@admin_permission_required('users.impersonate')
def impersonate_user(user_id):
    target_user = User.query.get_or_404(user_id)
    if target_user.is_super_admin:
        flash("Cannot impersonate Super Admin.", "danger")
        return redirect(url_for('admin.user_detail', user_id=target_user.id))
    session['admin_impersonator_id'] = current_user.id
    login_user(target_user)
    flash(f"Simulating session as @{target_user.username}.", "warning")
    return redirect(url_for('typing.test_page'))


@admin_bp.route('/stop-impersonation')
@login_required
def stop_impersonation():
    admin_id = session.pop('admin_impersonator_id', None)
    admin_user = User.query.get(admin_id) if admin_id else None
    if admin_user:
        login_user(admin_user)
        flash("Returned to Super Admin console.", "info")
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('auth.logout'))


# ==============================================================
# 5. GLOBAL COMMAND PALETTE SEARCH (Ctrl + K)
# ==============================================================

@admin_bp.route('/api/search')
@login_required
def admin_global_search():
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2: return jsonify({'results': []})
    results = []

    for u in User.query.filter(or_(User.username.ilike(f"%{q}%"), User.callsign.ilike(f"%{q}%"))).limit(4).all():
        results.append({'category': 'Pilots', 'title': f"@{u.username}", 'subtitle': u.email, 'url': url_for('admin.user_detail', user_id=u.id)})
    for p in TypingText.query.filter(or_(TypingText.title.ilike(f"%{q}%"), TypingText.content.ilike(f"%{q}%"))).limit(4).all():
        results.append({'category': 'Benchmark Texts', 'title': p.title, 'subtitle': f"{p.category} • {p.word_count} wds", 'url': url_for('admin.benchmark_passage_edit', passage_id=p.id)})

    return jsonify({'results': results})


# ==============================================================
# 6. SECTOR PASSAGE CMS: BENCHMARK PASSAGES
# ==============================================================

@admin_bp.route('/content/benchmark', endpoint='benchmark_passages')
@admin_bp.route('/passages', endpoint='passages_list')
@admin_permission_required('typing.view')
def benchmark_passages():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    discipline_filter = request.args.get('discipline', '').strip()
    difficulty_filter = request.args.get('difficulty', '').strip()

    query = TypingText.query

    if search:
        query = query.filter(or_(
            TypingText.title.ilike(f"%{search}%"),
            TypingText.content.ilike(f"%{search}%"),
            TypingText.source.ilike(f"%{search}%")
        ))

    if discipline_filter:
        if discipline_filter == 'code':
            query = query.filter(or_(TypingText.is_code == True, TypingText.category.ilike('%code%')))
        else:
            query = query.filter(TypingText.category.ilike(f"%{discipline_filter}%"))

    if difficulty_filter:
        query = query.filter_by(difficulty=difficulty_filter.lower())

    passages_page = query.order_by(TypingText.id.desc()).paginate(page=page, per_page=15, error_out=False)

    total_cnt = TypingText.query.count()
    code_cnt = TypingText.query.filter(or_(TypingText.is_code == True, TypingText.category.ilike('%code%'))).count()
    exam_cnt = TypingText.query.filter(or_(TypingText.category.ilike('%exam%'), TypingText.category.ilike('%professional%'))).count()
    prose_cnt = total_cnt - code_cnt - exam_cnt

    stats = {
        'total': total_cnt,
        'code': code_cnt,
        'exam': exam_cnt,
        'prose': max(0, prose_cnt)
    }

    return render_template(
        'admin/benchmark_passages.html',
        passages=passages_page,
        stats=stats,
        search=search,
        discipline_filter=discipline_filter,
        difficulty_filter=difficulty_filter
    )


@admin_bp.route('/content/benchmark/create', endpoint='benchmark_passage_create')
@admin_bp.route('/passages/create', endpoint='passage_create')
@admin_permission_required('typing.create')
def benchmark_passage_create():
    if request.method == 'POST':
        title = request.form.get('title', 'Untitled Benchmark Passage').strip()
        category = request.form.get('category', 'words').strip()
        difficulty = request.form.get('difficulty', 'moderate').strip().lower()
        content = request.form.get('content', '').strip()
        source = request.form.get('source', 'System').strip()
        is_active = request.form.get('is_active') == 'on'

        is_code = (category == 'code')
        code_lang = request.form.get('code_lang', 'python').strip().lower() if is_code else None

        if not content:
            flash("Passage text body cannot be empty.", "danger")
            return render_template('admin/benchmark_passage_form.html', action="Create", passage=None)

        passage = TypingText(
            title=title,
            category=category,
            difficulty=difficulty,
            content=content,
            source=source,
            is_code=is_code,
            code_lang=code_lang,
            is_active=is_active,
            status='published' if is_active else 'draft',
            created_by=current_user.username
        )
        passage.calculate_stats()
        db.session.add(passage)
        db.session.commit()

        log_admin_action('BENCHMARK_PASSAGE_CREATE', 'typing_text', passage.id, f"Created benchmark text '{title}'")
        flash(f"Benchmark text '{title}' added successfully.", "success")
        return redirect(url_for('admin.benchmark_passages'))

    return render_template('admin/benchmark_passage_form.html', action="Create", passage=None)


@admin_bp.route('/content/benchmark/<int:passage_id>/edit', endpoint='benchmark_passage_edit')
@admin_bp.route('/passages/<int:passage_id>/edit', endpoint='passage_edit')
@admin_permission_required('typing.edit')
def benchmark_passage_edit(passage_id):
    passage = TypingText.query.get_or_404(passage_id)
    if request.method == 'POST':
        passage.title = request.form.get('title', passage.title).strip()
        category = request.form.get('category', passage.category).strip()
        passage.category = category
        passage.difficulty = request.form.get('difficulty', passage.difficulty).strip().lower()
        passage.content = request.form.get('content', passage.content).strip()
        passage.source = request.form.get('source', passage.source).strip()
        passage.is_active = request.form.get('is_active') == 'on'
        passage.status = 'published' if passage.is_active else 'draft'

        passage.is_code = (category == 'code')
        passage.code_lang = request.form.get('code_lang', 'python').strip().lower() if passage.is_code else None
        passage.updated_by = current_user.username

        passage.calculate_stats()
        db.session.commit()

        log_admin_action('BENCHMARK_PASSAGE_EDIT', 'typing_text', passage.id, f"Updated benchmark text '{passage.title}'")
        flash(f"Benchmark text '{passage.title}' updated successfully.", "success")
        return redirect(url_for('admin.benchmark_passages'))

    return render_template('admin/benchmark_passage_form.html', action="Edit", passage=passage)


@admin_bp.route('/content/benchmark/<int:passage_id>/delete', methods=['POST'], endpoint='benchmark_passage_delete')
@admin_bp.route('/passages/<int:passage_id>/delete', methods=['POST'], endpoint='passage_delete')
@admin_permission_required('typing.delete')
def benchmark_passage_delete(passage_id):
    passage = TypingText.query.get_or_404(passage_id)
    title = passage.title
    db.session.delete(passage)
    db.session.commit()
    log_admin_action('BENCHMARK_PASSAGE_DELETE', 'typing_text', passage_id, f"Deleted '{title}'")
    flash(f"Benchmark text '{title}' deleted.", "info")
    return redirect(url_for('admin.benchmark_passages'))


@admin_bp.route('/content/benchmark/bulk-import', methods=['GET', 'POST'], endpoint='benchmark_bulk_import')
@admin_bp.route('/passages/bulk-import', methods=['GET', 'POST'], endpoint='passage_bulk_import')
@admin_permission_required('typing.create')
def benchmark_bulk_import():
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file or not file.filename.endswith('.csv'):
            flash("Please upload a valid .csv file.", "danger")
            return redirect(url_for('admin.benchmark_bulk_import'))

        try:
            stream = io.StringIO(file.stream.read().decode('utf-8', errors='ignore'))
            reader = csv.DictReader(stream)
            imported = 0
            duplicates = 0

            for row in reader:
                norm = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                title = norm.get('title', 'Untitled Benchmark Text')
                content = norm.get('content') or norm.get('text') or ''
                if len(content) < 15: continue

                existing = TypingText.query.filter_by(content=content).first()
                if existing:
                    duplicates += 1
                    continue

                discipline = norm.get('discipline') or norm.get('category') or 'words'
                difficulty = norm.get('difficulty', 'moderate').lower()
                is_code = (discipline == 'code')
                code_lang = norm.get('code_lang', 'python').lower() if is_code else None

                t_item = TypingText(
                    title=title,
                    category=discipline,
                    difficulty=difficulty,
                    content=content,
                    is_code=is_code,
                    code_lang=code_lang,
                    is_active=True,
                    status='published',
                    created_by=current_user.username
                )
                t_item.calculate_stats()
                db.session.add(t_item)
                imported += 1

            db.session.commit()
            log_admin_action('BENCHMARK_BULK_IMPORT', 'typing_text', details=f"Imported {imported} benchmark texts ({duplicates} duplicates skipped)")
            flash(f"Successfully imported {imported} benchmark texts ({duplicates} duplicates skipped).", "success")
            return redirect(url_for('admin.benchmark_passages'))
        except Exception as e:
            db.session.rollback()
            flash(f"Import failed: {str(e)}", "danger")

    return render_template('admin/benchmark_bulk_import.html')


@admin_bp.route('/content/benchmark/sample-csv', endpoint='benchmark_sample_csv')
@admin_bp.route('/passages/sample-csv', endpoint='passage_sample_csv')
@admin_permission_required('typing.view')
def benchmark_sample_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['title', 'discipline', 'difficulty', 'content', 'code_lang'])
    writer.writerow([
        'Supersonic Aerodynamics',
        'paragraphs',
        'moderate',
        'When an aircraft accelerates through the transonic boundary toward Mach 1, shockwaves form along the leading edges of the wings.',
        ''
    ])
    writer.writerow([
        'Staff Selection Commission Clerical Memo',
        'exam',
        'hard',
        'GOVERNMENT OF INDIA. Pursuant to Rule 149 of the General Financial Rules, drawing officers must adhere strictly to procurement thresholds.',
        ''
    ])
    writer.writerow([
        'Python Binary Search',
        'code',
        'moderate',
        'def binary_search(arr, target):\n    low, high = 0, len(arr) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == target: return mid\n    return -1',
        'python'
    ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=typesphere_benchmark_sample.csv"}
    )


# ==============================================================
# 7. SECTOR: 24H DAILY RECON & TACTICAL MISSIONS
# ==============================================================

@admin_bp.route('/content/missions', endpoint='challenges_manage')
@admin_bp.route('/challenges')
@admin_permission_required('challenges.view')
def challenges_manage():
    today = ist_today()
    status_filter = request.args.get('status', 'all').strip().lower()
    search = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)

    query = DailyChallenge.query

    if search:
        query = query.filter(or_(
            DailyChallenge.title.ilike(f"%{search}%"),
            DailyChallenge.content.ilike(f"%{search}%")
        ))

    if status_filter == 'live':
        query = query.filter(DailyChallenge.target_date == today)
    elif status_filter == 'scheduled':
        query = query.filter(DailyChallenge.target_date > today)
    elif status_filter == 'expired':
        query = query.filter(DailyChallenge.target_date < today)

    challenges_page = query.order_by(DailyChallenge.target_date.desc()).paginate(page=page, per_page=12, error_out=False)

    current_daily = DailyChallenge.query.filter_by(target_date=today).first()
    scheduled_count = DailyChallenge.query.filter(DailyChallenge.target_date > today).count()
    expired_count = DailyChallenge.query.filter(DailyChallenge.target_date < today).count()
    total_count = DailyChallenge.query.count()
    total_missions_completed = TypingTest.query.filter(TypingTest.mode.like('mission_%')).count()

    return render_template(
        'admin/missions_management.html',
        challenges_page=challenges_page,
        current_daily=current_daily,
        today_date=today,
        scheduled_count=scheduled_count,
        expired_count=expired_count,
        total_count=total_count,
        total_missions_completed=total_missions_completed,
        status_filter=status_filter,
        search=search
    )


@admin_bp.route('/challenges/publish-daily', methods=['POST'])
@admin_permission_required('challenges.manage')
def publish_daily_challenge():
    challenge_id = request.form.get('challenge_id', type=int)
    target_date_str = request.form.get('target_date', '').strip()
    title = request.form.get('title', 'Daily Flight Mastery').strip()
    content = request.form.get('content', '').strip()

    if not content:
        flash("Briefing passage text cannot be empty.", "danger")
        return redirect(url_for('admin.challenges_manage'))

    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else ist_today()
    except ValueError:
        target_date = ist_today()

    existing = DailyChallenge.query.filter_by(target_date=target_date).first()

    if challenge_id:
        c = DailyChallenge.query.get(challenge_id)
        if c:
            c.target_date = target_date
            c.title = title
            c.content = content
            db.session.commit()
            log_admin_action('DAILY_CHALLENGE_UPDATE', 'challenge', c.id, f"Updated challenge for {target_date}")
            flash(f"Daily Challenge for {target_date} updated successfully.", "success")
            return redirect(url_for('admin.challenges_manage'))

    if existing:
        existing.title = title
        existing.content = content
        log_admin_action('DAILY_CHALLENGE_UPDATE', 'challenge', existing.id, f"Updated Daily Challenge for {target_date}")
        flash(f"Daily Challenge for {target_date} updated.", "success")
    else:
        new_c = DailyChallenge(target_date=target_date, title=title, content=content)
        db.session.add(new_c)
        log_admin_action('DAILY_CHALLENGE_CREATE', 'challenge', details=f"Published Daily Challenge for {target_date}")
        flash(f"Daily Challenge for {target_date} published.", "success")

    db.session.commit()
    return redirect(url_for('admin.challenges_manage'))


@admin_bp.route('/challenges/<int:challenge_id>/delete', methods=['POST'])
@admin_permission_required('challenges.manage')
def delete_daily_challenge(challenge_id):
    c = DailyChallenge.query.get_or_404(challenge_id)
    c_date = c.target_date
    db.session.delete(c)
    db.session.commit()
    log_admin_action('DAILY_CHALLENGE_DELETE', 'challenge', challenge_id, f"Deleted Daily Challenge for {c_date}")
    flash(f"Daily Challenge for {c_date} removed.", "info")
    return redirect(url_for('admin.challenges_manage'))


@admin_bp.route('/content/missions/bulk-import', methods=['GET', 'POST'])
@admin_permission_required('challenges.manage')
def missions_bulk_import():
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file or not file.filename.endswith('.csv'):
            flash("Please upload a valid .csv calendar file.", "danger")
            return redirect(url_for('admin.missions_bulk_import'))

        try:
            stream = io.StringIO(file.stream.read().decode('utf-8', errors='ignore'))
            reader = csv.DictReader(stream)
            imported = 0
            updated = 0

            for row in reader:
                norm = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                date_str = norm.get('target_date') or norm.get('date') or ''
                title = norm.get('title', 'Daily Flight Briefing')
                content = norm.get('content') or norm.get('text') or ''

                if not date_str or not content:
                    continue

                try:
                    c_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    continue

                existing = DailyChallenge.query.filter_by(target_date=c_date).first()
                if existing:
                    existing.title = title
                    existing.content = content
                    updated += 1
                else:
                    new_item = DailyChallenge(target_date=c_date, title=title, content=content)
                    db.session.add(new_item)
                    imported += 1

            db.session.commit()
            log_admin_action('MISSIONS_BULK_IMPORT', 'daily_challenge', details=f"Scheduled {imported} new days, updated {updated} existing")
            flash(f"Successfully processed calendar batch: {imported} scheduled, {updated} updated.", "success")
            return redirect(url_for('admin.challenges_manage'))
        except Exception as e:
            db.session.rollback()
            flash(f"Import error: {str(e)}", "danger")

    return render_template('admin/missions_bulk_import.html')


@admin_bp.route('/content/missions/sample-csv')
@admin_permission_required('challenges.view')
def missions_sample_csv():
    today = ist_today()
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['target_date', 'title', 'content'])
    writer.writerow([
        today.isoformat(),
        'Supersonic Aerodynamics Intercept',
        'When an aircraft accelerates through the transonic boundary toward Mach 1, compressibility effects dominate the airflow across the airframe.'
    ])
    writer.writerow([
        tomorrow.isoformat(),
        'Cognitive Cadence & Hand Ergonomics',
        'True velocity is not rushed chaos; it is calm, deliberate movement free of hesitation and unnecessary recoil. Keep your palms anchored.'
    ])
    writer.writerow([
        day_after.isoformat(),
        'Distributed Systems Consensus Flow',
        'Decoupled event-driven architectures achieve high availability and fault tolerance by routing immutable commit logs across partitioned worker nodes.'
    ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=typesphere_missions_calendar_sample.csv"}
    )


# ==============================================================
# 8. SECTOR: 1V1 MULTIPLAYER GRID PASSAGES
# ==============================================================

@admin_bp.route('/content/multiplayer', endpoint='multiplayer_passages')
@admin_permission_required('typing.view')
def multiplayer_passages():
    page = request.args.get('page', 1, type=int)
    duration_filter = request.args.get('duration', '').strip()

    query = TypingText.query.filter_by(allow_multiplayer=True)

    if duration_filter and duration_filter.isdigit():
        query = query.filter_by(recommended_duration=int(duration_filter))

    passages_page = query.order_by(TypingText.recommended_duration.asc(), TypingText.id.desc()).paginate(page=page, per_page=15, error_out=False)

    stats = {
        'total': TypingText.query.filter_by(allow_multiplayer=True).count(),
        'sprint': TypingText.query.filter_by(allow_multiplayer=True).filter(TypingText.recommended_duration.in_([30, 60])).count(),
        'five_min': TypingText.query.filter_by(allow_multiplayer=True, recommended_duration=300).count(),
        'ten_min': TypingText.query.filter_by(allow_multiplayer=True, recommended_duration=600).count()
    }

    return render_template(
        'admin/multiplayer_passages.html',
        passages=passages_page,
        stats=stats,
        duration_filter=duration_filter
    )


@admin_bp.route('/content/multiplayer/create', methods=['POST'])
@admin_permission_required('typing.create')
def multiplayer_passage_create():
    title = request.form.get('title', 'Grid Match Passage').strip()
    duration = request.form.get('duration', 60, type=int)
    content = request.form.get('content', '').strip()

    if not content:
        flash("Passage content cannot be empty.", "danger")
        return redirect(url_for('admin.multiplayer_passages'))

    new_p = TypingText(
        title=title,
        category='multiplayer',
        content=content,
        recommended_duration=duration,
        min_duration=duration,
        max_duration=duration,
        allow_multiplayer=True,
        is_active=True,
        status='published',
        created_by=current_user.username
    )
    new_p.calculate_stats()
    db.session.add(new_p)
    db.session.commit()

    log_admin_action('MULTIPLAYER_PASSAGE_CREATE', 'typing_text', new_p.id, f"Created {duration}s grid text '{title}'")
    flash(f"Multiplayer passage '{title}' ({duration}s bracket) successfully added.", "success")
    return redirect(url_for('admin.multiplayer_passages'))


@admin_bp.route('/content/multiplayer/<int:passage_id>/delete', methods=['POST'])
@admin_permission_required('typing.delete')
def multiplayer_passage_delete(passage_id):
    p = TypingText.query.get_or_404(passage_id)
    title = p.title
    db.session.delete(p)
    db.session.commit()
    log_admin_action('MULTIPLAYER_PASSAGE_DELETE', 'typing_text', passage_id, f"Removed '{title}' from multiplayer")
    flash(f"Removed '{title}' from multiplayer grid.", "info")
    return redirect(url_for('admin.multiplayer_passages'))


@admin_bp.route('/content/multiplayer/bulk-import', methods=['GET', 'POST'])
@admin_permission_required('typing.create')
def multiplayer_bulk_import():
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file or not file.filename.endswith('.csv'):
            flash("Please upload a valid .csv file.", "danger")
            return redirect(url_for('admin.multiplayer_bulk_import'))

        try:
            stream = io.StringIO(file.stream.read().decode('utf-8', errors='ignore'))
            reader = csv.DictReader(stream)
            imported = 0

            for row in reader:
                norm = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                title = norm.get('title', 'Grid Match Passage')
                content = norm.get('content') or norm.get('text') or ''
                duration = int(norm.get('duration', 60))

                if len(content) < 20: continue

                new_p = TypingText(
                    title=title,
                    category='multiplayer',
                    content=content,
                    recommended_duration=duration,
                    allow_multiplayer=True,
                    is_active=True,
                    status='published',
                    created_by=current_user.username
                )
                new_p.calculate_stats()
                db.session.add(new_p)
                imported += 1

            db.session.commit()
            log_admin_action('MULTIPLAYER_BULK_IMPORT', 'typing_text', details=f"Imported {imported} grid passages")
            flash(f"Successfully imported {imported} multiplayer passages.", "success")
            return redirect(url_for('admin.multiplayer_passages'))
        except Exception as e:
            db.session.rollback()
            flash(f"Import failed: {str(e)}", "danger")

    return render_template('admin/multiplayer_bulk_import.html')


@admin_bp.route('/content/multiplayer/sample-csv')
@admin_permission_required('typing.view')
def multiplayer_sample_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['title', 'duration', 'content'])
    writer.writerow([
        'Velocity Sprint Cadence',
        '30',
        'Speed is born from economy of movement. Eliminate tension from your fingers and allow rhythm to carry every keystroke.'
    ])
    writer.writerow([
        'Distributed Systems Commit Pipeline',
        '60',
        'Distributed computing architectures enable modern web applications to dynamically scale compute resources based on incoming request volume across partitioned clusters.'
    ])
    writer.writerow([
        'Atmospheric Transonic Marathon',
        '300',
        'Modern computational infrastructure increasingly depends on distributed event streaming pipelines to process real-time information at planetary scale. Decoupling producers from consumers preserves system integrity under load.'
    ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=typesphere_multiplayer_sample.csv"}
    )


# ==============================================================
# 9. SECTOR: ARCADE WORDBANKS & CONTENT MANAGEMENT
# ==============================================================

@admin_bp.route('/content/arcade', endpoint='arcade_content_manage')
@admin_permission_required('games.view')
def arcade_content_manage():
    page = request.args.get('page', 1, type=int)
    game_filter = request.args.get('game', '').strip()

    query = ArcadeContentItem.query
    if game_filter:
        query = query.filter_by(game_mode=game_filter)

    items_page = query.order_by(ArcadeContentItem.id.desc()).paginate(page=page, per_page=20, error_out=False)
    total_items = ArcadeContentItem.query.count()

    return render_template(
        'admin/arcade_content_manager.html',
        items=items_page,
        total_items=total_items,
        game_filter=game_filter
    )


@admin_bp.route('/content/arcade/add-item', methods=['POST'])
@admin_permission_required('games.edit')
def arcade_add_item():
    game_mode = request.form.get('game_mode', 'falling_words').strip()
    difficulty = request.form.get('difficulty', 'moderate').strip()
    target_text = request.form.get('target_text', '').strip()

    if not target_text:
        flash("Target text cannot be empty.", "danger")
        return redirect(url_for('admin.arcade_content_manage'))

    new_item = ArcadeContentItem(
        game_mode=game_mode,
        difficulty=difficulty,
        target_text=target_text,
        word_length=len(target_text),
        is_active=True
    )
    db.session.add(new_item)
    db.session.commit()

    log_admin_action('ARCADE_CONTENT_ADD', 'arcade_content_item', new_item.id, f"Added item to {game_mode}")
    flash(f"Item added to {game_mode.replace('_', ' ').title()} wordbank.", "success")
    return redirect(url_for('admin.arcade_content_manage', game=game_mode))


@admin_bp.route('/content/arcade/delete-item/<int:item_id>', methods=['POST'])
@admin_permission_required('games.edit')
def arcade_delete_item(item_id):
    item = ArcadeContentItem.query.get_or_404(item_id)
    g_mode = item.game_mode
    db.session.delete(item)
    db.session.commit()
    flash("Wordbank item removed.", "info")
    return redirect(url_for('admin.arcade_content_manage', game=g_mode))


@admin_bp.route('/content/arcade/bulk-import', methods=['GET', 'POST'])
@admin_permission_required('games.edit')
def arcade_bulk_import():
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file or not file.filename.endswith('.csv'):
            flash("Please upload a valid .csv file.", "danger")
            return redirect(url_for('admin.arcade_bulk_import'))

        try:
            stream = io.StringIO(file.stream.read().decode('utf-8', errors='ignore'))
            reader = csv.DictReader(stream)
            imported = 0

            for row in reader:
                norm = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                g_mode = norm.get('game_mode') or norm.get('mode') or 'falling_words'
                diff = norm.get('difficulty', 'moderate')
                text_val = norm.get('target_text') or norm.get('text') or ''

                if not text_val: continue

                new_i = ArcadeContentItem(
                    game_mode=g_mode,
                    difficulty=diff,
                    target_text=text_val,
                    word_length=len(text_val),
                    is_active=True
                )
                db.session.add(new_i)
                imported += 1

            db.session.commit()
            log_admin_action('ARCADE_BULK_IMPORT', 'arcade_content_item', details=f"Imported {imported} arcade items")
            flash(f"Successfully imported {imported} arcade wordbank items.", "success")
            return redirect(url_for('admin.arcade_content_manage'))
        except Exception as e:
            db.session.rollback()
            flash(f"Import failed: {str(e)}", "danger")

    return render_template('admin/arcade_bulk_import.html')


@admin_bp.route('/content/arcade/sample-csv')
@admin_permission_required('games.view')
def arcade_sample_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['game_mode', 'difficulty', 'target_text'])
    writer.writerow(['falling_words', 'moderate', 'velocity'])
    writer.writerow(['speed_racer', 'moderate', 'The open highway stretched across the desert floor under a wide expanse of pale morning sky.'])
    writer.writerow(['cipher_hacker', 'hard', '0xDEADBEEF'])
    writer.writerow(['bomb_defuse', 'hard', 'ALPHA78'])
    writer.writerow(['bubble_pop', 'easy', 'k'])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=typesphere_arcade_wordbank_sample.csv"}
    )


# ==============================================================
# 10. ARCADE GAME CONFIGURATION & REORDERING
# ==============================================================

@admin_bp.route('/games')
@admin_permission_required('games.view')
def games_list():
    purge_keyboard_quest_config()
    games = ArcadeGameConfig.query.filter(
        ArcadeGameConfig.game_slug != 'keyboard_quest'
    ).order_by(ArcadeGameConfig.display_order.asc(), ArcadeGameConfig.id.asc()).all()
    return render_template('admin/games.html', games=games, total_games=len(games), active_games=sum(1 for g in games if g.is_enabled))


@admin_bp.route('/games/<int:config_id>/edit', methods=['GET', 'POST'])
@admin_permission_required('games.edit')
def game_edit(config_id):
    game = ArcadeGameConfig.query.get_or_404(config_id)
    if request.method == 'POST':
        game.display_title = request.form.get('display_title', game.display_title).strip()
        game.description = request.form.get('description', game.description).strip()
        game.durations = request.form.get('durations', game.durations).strip()
        game.default_ai_level = request.form.get('default_ai_level', game.default_ai_level).strip()
        game.is_enabled = request.form.get('is_enabled') == 'on'
        game.allows_solo_ai = request.form.get('allows_solo_ai') == 'on'
        game.allows_1v1 = request.form.get('allows_1v1') == 'on'

        db.session.commit()
        log_admin_action('GAME_CONFIG_UPDATE', 'arcade_game', game.id, f"Updated config for '{game.display_title}'")
        flash(f"Configuration for '{game.display_title}' updated.", "success")
        return redirect(url_for('admin.games_list'))

    return render_template('admin/game_form.html', game=game)


@admin_bp.route('/games/<int:config_id>/toggle', methods=['POST'])
@admin_permission_required('games.toggle')
def game_toggle(config_id):
    game = ArcadeGameConfig.query.get_or_404(config_id)
    game.is_enabled = not game.is_enabled
    db.session.commit()
    flash(f"Game '{game.display_title}' {'enabled' if game.is_enabled else 'disabled'}.", "success")
    return redirect(url_for('admin.games_list'))


@admin_bp.route('/games/reorder', methods=['POST'])
@admin_permission_required('games.edit')
def reorder_games():
    payload = request.get_json(silent=True) or {}
    ordered_ids = payload.get('ordered_ids', [])
    for idx, gid in enumerate(ordered_ids, start=1):
        g = ArcadeGameConfig.query.get(gid)
        if g: g.display_order = idx
    db.session.commit()
    return jsonify({'success': True})


# ==============================================================
# 11. SECTOR: FLIGHT SCHOOL ACADEMY STAGES
# ==============================================================

@admin_bp.route('/content/academy', endpoint='academy_manage')
@admin_bp.route('/academy')
@admin_permission_required('academy.view')
def academy_manage():
    stages = LessonStage.query.order_by(LessonStage.track.asc(), LessonStage.stage_number.asc()).all()
    grouped = {}
    for st in stages: grouped.setdefault(st.track, []).append(st)
    return render_template('admin/academy.html', grouped_stages=grouped, total_stages=len(stages))


@admin_bp.route('/academy/stage/<int:stage_id>/edit', methods=['GET', 'POST'])
@admin_permission_required('academy.manage')
def stage_edit(stage_id):
    stage = LessonStage.query.get_or_404(stage_id)
    if request.method == 'POST':
        stage.title = request.form.get('title', stage.title).strip()
        stage.description = request.form.get('description', stage.description).strip()
        stage.focus_keys = request.form.get('focus_keys', stage.focus_keys).strip()
        stage.practice_material = request.form.get('practice_material', stage.practice_material).strip()
        stage.min_wpm_to_pass = float(request.form.get('min_wpm_to_pass', stage.min_wpm_to_pass))
        stage.min_accuracy_to_pass = float(request.form.get('min_accuracy_to_pass', stage.min_accuracy_to_pass))
        stage.required_attempts = int(request.form.get('required_attempts', stage.required_attempts))

        db.session.commit()
        log_admin_action('STAGE_UPDATE', 'academy_stage', stage.id, f"Updated Stage {stage.stage_number}")
        flash(f"Stage '{stage.title}' updated.", "success")
        return redirect(url_for('admin.academy_manage'))

    return render_template('admin/stage_form.html', stage=stage)


# ==============================================================
# 12. SECTOR: PASSAGE COLLECTIONS / PACKS
# ==============================================================

@admin_bp.route('/content/collections', endpoint='passage_collections')
@admin_bp.route('/passages/collections')
@admin_permission_required('typing.view')
def passage_collections():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        is_active = request.form.get('is_active') == 'on'

        if not title:
            flash("Collection title is required.", "danger")
            return redirect(url_for('admin.passage_collections'))

        clean_slug = re.sub(r'[^a-zA-Z0-9]+', '-', title.lower()).strip('-')[:120] or "pack"
        unique_slug = clean_slug
        counter = 1
        while PassageCollection.query.filter_by(slug=unique_slug).first():
            unique_slug = f"{clean_slug}-{counter}"
            counter += 1

        new_col = PassageCollection(title=title, slug=unique_slug, description=description, is_active=is_active, created_by=current_user.username)
        db.session.add(new_col)
        db.session.commit()
        flash(f"Passage collection '{title}' created.", "success")
        return redirect(url_for('admin.passage_collections'))

    collections = PassageCollection.query.order_by(PassageCollection.id.desc()).all()
    return render_template('admin/passage_collections.html', collections=collections)


@admin_bp.route('/content/collections/<int:collection_id>/toggle', methods=['POST'], endpoint='toggle_collection')
@admin_bp.route('/passages/collections/<int:collection_id>/toggle', methods=['POST'])
@admin_permission_required('typing.edit')
def toggle_collection(collection_id):
    col = PassageCollection.query.get_or_404(collection_id)
    col.is_active = not col.is_active
    db.session.commit()
    flash(f"Collection '{col.title}' toggled.", "success")
    return redirect(url_for('admin.passage_collections'))


@admin_bp.route('/content/collections/<int:collection_id>/delete', methods=['POST'], endpoint='delete_collection')
@admin_bp.route('/passages/collections/<int:collection_id>/delete', methods=['POST'])
@admin_permission_required('typing.delete')
def delete_collection(collection_id):
    col = PassageCollection.query.get_or_404(collection_id)
    db.session.delete(col)
    db.session.commit()
    flash(f"Collection '{col.title}' deleted.", "info")
    return redirect(url_for('admin.passage_collections'))


# ==============================================================
# 13. SECTOR: TAXONOMY & CATEGORIES MANAGER
# ==============================================================

@admin_bp.route('/content/categories', endpoint='passage_categories')
@admin_bp.route('/passages/categories')
@admin_permission_required('typing.view')
def passage_categories():
    categories_data = db.session.query(
        TypingText.category, func.count(TypingText.id).label('count')
    ).group_by(TypingText.category).order_by(desc('count')).all()

    exam_profiles_data = db.session.query(
        TypingText.exam_profile, func.count(TypingText.id).label('count')
    ).filter(TypingText.exam_profile.isnot(None), TypingText.exam_profile != '').group_by(TypingText.exam_profile).order_by(desc('count')).all()

    passage_types_data = db.session.query(
        TypingText.passage_type, func.count(TypingText.id).label('count')
    ).group_by(TypingText.passage_type).order_by(desc('count')).all()

    tags = PassageTag.query.order_by(PassageTag.name.asc()).all()

    return render_template(
        'admin/passage_categories.html',
        categories_data=categories_data,
        exam_profiles_data=exam_profiles_data,
        passage_types_data=passage_types_data,
        tags=tags
    )


@admin_bp.route('/passages/categories/rename', methods=['POST'])
@admin_permission_required('typing.edit')
def rename_category():
    old_cat = request.form.get('old_category', '').strip()
    new_cat = request.form.get('new_category', '').strip()
    if old_cat and new_cat:
        cnt = TypingText.query.filter_by(category=old_cat).update({'category': new_cat})
        db.session.commit()
        flash(f"Updated {cnt} passage(s) from '{old_cat}' to '{new_cat}'.", "success")
    return redirect(url_for('admin.passage_categories'))


@admin_bp.route('/passages/tags/<int:tag_id>/delete', methods=['POST'])
@admin_permission_required('typing.edit')
def delete_tag(tag_id):
    tag = PassageTag.query.get_or_404(tag_id)
    db.session.delete(tag)
    db.session.commit()
    flash(f"Tag #{tag.name} deleted.", "info")
    return redirect(url_for('admin.passage_categories'))


@admin_bp.route('/passages/tags/prune-unused', methods=['POST'])
@admin_permission_required('typing.edit')
def prune_unused_tags():
    tags = PassageTag.query.all()
    pruned = sum(1 for t in tags if t.passages.count() == 0 and not db.session.delete(t))
    db.session.commit()
    flash(f"Pruned {pruned} unused tags.", "success")
    return redirect(url_for('admin.passage_categories'))


# ==============================================================
# 14. CERTIFICATES, LEADERBOARDS & COMMUNITY
# ==============================================================

@admin_bp.route('/certificates')
@admin_permission_required('certificates.view')
def certificates_manage():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    query = TypingTest.query.filter(TypingTest.user_id.isnot(None), TypingTest.wpm >= 35.0, TypingTest.accuracy >= 90.0)
    if search:
        query = query.join(User).filter(or_(User.username.ilike(f"%{search}%"), User.callsign.ilike(f"%{search}%")))
    tests = query.order_by(TypingTest.completed_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/certificates.html', tests=tests, search=search, to_ist=to_ist, hashlib=hashlib)


@admin_bp.route('/certificates/<int:test_id>/revoke', methods=['POST'])
@admin_permission_required('certificates.revoke')
def certificate_revoke(test_id):
    test = TypingTest.query.get_or_404(test_id)
    test.suspicious = True
    test.suspicion_reason = request.form.get('reason', 'Administrative revocation')
    db.session.commit()
    flash(f"Certificate #{test.id} revoked.", "warning")
    return redirect(url_for('admin.certificates_manage'))


@admin_bp.route('/certificates/<int:test_id>/restore', methods=['POST'])
@admin_permission_required('certificates.revoke')
def certificate_restore(test_id):
    test = TypingTest.query.get_or_404(test_id)
    test.suspicious = False
    test.suspicion_reason = None
    db.session.commit()
    flash(f"Certificate #{test.id} reinstated.", "success")
    return redirect(url_for('admin.certificates_manage'))


@admin_bp.route('/community')
@admin_permission_required('reviews.view')
def community_manage():
    reviews = RatingReview.query.order_by(RatingReview.created_at.desc()).all()
    feedbacks = FeedbackItem.query.order_by(FeedbackItem.created_at.desc()).all()
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    inquiries = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(25).all()
    return render_template('admin/community.html', reviews=reviews, feedbacks=feedbacks, announcements=announcements, inquiries=inquiries, to_ist=to_ist)


@admin_bp.route('/community/reviews/create-official', methods=['POST'])
@admin_permission_required('reviews.moderate')
def create_official_review():
    title = request.form.get('review_title', '').strip()
    text_content = request.form.get('review_text', '').strip()
    rating = request.form.get('rating', 5, type=int)
    if title and text_content:
        new_rev = RatingReview(user_id=current_user.id, rating=max(1, min(5, rating)), review_title=title, review_text=text_content, is_approved=True)
        db.session.add(new_rev)
        db.session.commit()
        flash("Official review published.", "success")
    return redirect(url_for('admin.community_manage'))


@admin_bp.route('/announcements/create', methods=['POST'])
@admin_permission_required('announcements.manage')
def create_announcement():
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    if title and content:
        new_a = Announcement(title=title, content=content, is_active=True)
        db.session.add(new_a)
        db.session.commit()
        flash("Announcement published.", "success")
    return redirect(url_for('admin.community_manage'))


@admin_bp.route('/announcements/<int:announcement_id>/toggle', methods=['POST'])
@admin_permission_required('announcements.manage')
def toggle_announcement(announcement_id):
    a = Announcement.query.get_or_404(announcement_id)
    a.is_active = not a.is_active
    db.session.commit()
    flash(f"Announcement '{a.title}' toggled.", "info")
    return redirect(url_for('admin.community_manage'))


@admin_bp.route('/announcements/<int:announcement_id>/delete', methods=['POST'])
@admin_permission_required('announcements.manage')
def delete_announcement(announcement_id):
    a = Announcement.query.get_or_404(announcement_id)
    db.session.delete(a)
    db.session.commit()
    flash("Announcement deleted.", "info")
    return redirect(url_for('admin.community_manage'))


@admin_bp.route('/reviews/<int:review_id>/toggle', methods=['POST'])
@admin_permission_required('reviews.moderate')
def toggle_review(review_id):
    r = RatingReview.query.get_or_404(review_id)
    r.is_approved = not r.is_approved
    db.session.commit()
    flash("Review visibility toggled.", "success")
    return redirect(url_for('admin.community_manage'))


@admin_bp.route('/reviews/<int:review_id>/delete', methods=['POST'])
@admin_permission_required('reviews.moderate')
def delete_review(review_id):
    r = RatingReview.query.get_or_404(review_id)
    db.session.delete(r)
    db.session.commit()
    flash("Review deleted.", "info")
    return redirect(url_for('admin.community_manage'))


@admin_bp.route('/feedback/<int:feedback_id>/respond', methods=['POST'])
@admin_permission_required('feedback.manage')
def respond_feedback(feedback_id):
    fb = FeedbackItem.query.get_or_404(feedback_id)
    fb.status = request.form.get('status', 'Resolved')
    fb.admin_response = request.form.get('admin_response', '').strip()
    db.session.commit()
    flash("Feedback updated.", "success")
    return redirect(url_for('admin.community_manage'))


# ==============================================================
# 15. SECURITY & ACTIVE IP MANAGEMENT
# ==============================================================

@admin_bp.route('/security')
@admin_permission_required('security.events_view')
def security_center():
    page = request.args.get('page', 1, type=int)
    severity_filter = request.args.get('severity', '').strip()
    search = request.args.get('q', '').strip()

    query = SecurityEvent.query
    if severity_filter: query = query.filter_by(severity=severity_filter.upper())
    if search:
        query = query.filter(or_(SecurityEvent.identifier.ilike(f"%{search}%"), SecurityEvent.ip_address.ilike(f"%{search}%")))

    events = query.order_by(SecurityEvent.created_at.desc()).paginate(page=page, per_page=25, error_out=False)
    return render_template(
        'admin/security.html',
        events=events,
        failed_logins=SecurityEvent.query.filter_by(event_type='FAILED_LOGIN').count(),
        critical_events=SecurityEvent.query.filter_by(severity='CRITICAL').count(),
        blocked_ips=BlockedIP.query.order_by(BlockedIP.created_at.desc()).all(),
        severity_filter=severity_filter,
        search=search,
        to_ist=to_ist
    )


@admin_bp.route('/security/block-ip', methods=['POST'])
@admin_permission_required('security.ip_manage')
def handle_block_ip():
    ip = request.form.get('ip_address', '').strip()
    reason = request.form.get('reason', 'Suspicious activity').strip()
    is_perm = request.form.get('is_permanent') == 'on'
    duration = request.form.get('duration_hours', 24, type=int)
    if ip: block_ip(ip, reason, is_permanent=is_perm, duration_hours=duration, blocked_by=current_user.username)
    flash(f"IP {ip} restricted.", "success")
    return redirect(url_for('admin.security_center'))


@admin_bp.route('/security/unblock-ip/<int:block_id>', methods=['POST'])
@admin_permission_required('security.ip_manage')
def handle_unblock_ip(block_id):
    b = BlockedIP.query.get_or_404(block_id)
    unblock_ip(b.ip_address, unblocked_by=current_user.username)
    flash(f"Lifted restriction on {b.ip_address}.", "success")
    return redirect(url_for('admin.security_center'))


# ==============================================================
# 16. WEBSITE CONTROL & NAVIGATION CMS
# ==============================================================

@admin_bp.route('/website')
@admin_permission_required('website.settings')
def website_control():
    nav_items = SiteNavigationItem.query.order_by(SiteNavigationItem.nav_order.asc()).all()
    maintenance_cfg = PlatformConfig.query.filter_by(key='maintenance_mode').first()
    maintenance_msg = PlatformConfig.query.filter_by(key='maintenance_message').first()
    brand_cfg = PlatformConfig.query.filter_by(key='site_tagline').first()

    return render_template(
        'admin/website.html',
        nav_items=nav_items,
        is_maintenance=bool(maintenance_cfg and maintenance_cfg.value.lower() == 'true'),
        maintenance_msg=maintenance_msg.value if maintenance_msg else "Scheduled flight calibration underway.",
        tagline=brand_cfg.value if brand_cfg else "Next-Generation Flight Intelligence & Biometric Telemetry Engine."
    )


@admin_bp.route('/website/maintenance/toggle', methods=['POST'])
@admin_permission_required('website.settings')
def toggle_maintenance():
    cfg = PlatformConfig.query.filter_by(key='maintenance_mode').first()
    msg = request.form.get('maintenance_message', '').strip()

    if not cfg:
        cfg = PlatformConfig(key='maintenance_mode', value='true', updated_by=current_user.username)
        db.session.add(cfg)
    else:
        cfg.value = 'false' if cfg.value.lower() == 'true' else 'true'
        cfg.updated_by = current_user.username

    if msg:
        m_cfg = PlatformConfig.query.filter_by(key='maintenance_message').first()
        if not m_cfg:
            m_cfg = PlatformConfig(key='maintenance_message', value=msg, updated_by=current_user.username)
            db.session.add(m_cfg)
        else:
            m_cfg.value = msg
            m_cfg.updated_by = current_user.username

    db.session.commit()
    flash(f"Maintenance mode set to {cfg.value}.", "warning" if cfg.value == 'true' else "success")
    return redirect(url_for('admin.website_control'))


@admin_bp.route('/website/navigation/add', methods=['POST'])
@admin_permission_required('website.settings')
def add_navigation_item():
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
    label = request.form.get('label', '').strip() if not request.is_json else request.json.get('label', '').strip()
    url = request.form.get('url', '').strip() if not request.is_json else request.json.get('url', '').strip()

    if label and url:
        max_order = db.session.query(func.max(SiteNavigationItem.nav_order)).scalar() or 0
        new_nav = SiteNavigationItem(label=label, url=url, nav_order=max_order + 1, is_visible=True)
        db.session.add(new_nav)
        db.session.commit()
        if is_ajax: return jsonify({'success': True})
    return redirect(url_for('admin.website_control'))


@admin_bp.route('/website/navigation/<int:item_id>/edit', methods=['POST'])
@admin_permission_required('website.settings')
def edit_navigation_item(item_id):
    item = SiteNavigationItem.query.get_or_404(item_id)
    if request.is_json:
        data = request.json
        item.label = data.get('label', item.label)
        item.url = data.get('url', item.url)
        item.nav_order = int(data.get('nav_order', item.nav_order))
        item.is_visible = bool(data.get('is_visible', True))
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/website/navigation/<int:item_id>/delete', methods=['POST'])
@admin_permission_required('website.settings')
def delete_navigation_item(item_id):
    item = SiteNavigationItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})


# ==============================================================
# 17. RUNTIME FLAGS, ANALYTICS & HEALTH
# ==============================================================

@admin_bp.route('/flags')
@admin_permission_required('website.flags')
def feature_flags_list():
    return render_template('admin/flags.html', flags=FeatureFlag.query.all())


@admin_bp.route('/flags/create', methods=['POST'])
@admin_permission_required('website.flags')
def create_feature_flag():
    key = request.form.get('key', '').strip().lower().replace(' ', '_')
    label = request.form.get('label', '').strip()
    desc = request.form.get('description', '').strip()
    if key and label and not FeatureFlag.query.filter_by(key=key).first():
        new_flag = FeatureFlag(key=key, label=label, description=desc, is_enabled=True, updated_by=current_user.username)
        db.session.add(new_flag)
        db.session.commit()
        flash(f"Flag '{key}' registered.", "success")
    return redirect(url_for('admin.feature_flags_list'))


@admin_bp.route('/flags/<int:flag_id>/toggle', methods=['POST'])
@admin_permission_required('website.flags')
def toggle_feature_flag(flag_id):
    flag = FeatureFlag.query.get_or_404(flag_id)
    flag.is_enabled = not flag.is_enabled
    db.session.commit()
    flash(f"Flag '{flag.key}' toggled.", "success")
    return redirect(url_for('admin.feature_flags_list'))


@admin_bp.route('/analytics')
@admin_permission_required('analytics.traffic')
def traffic_analytics():
    days = request.args.get('days', 30, type=int)
    cutoff = datetime.utcnow() - timedelta(days=days)

    total_views = VisitorTraffic.query.filter(VisitorTraffic.created_at >= cutoff).count()
    unique_sessions = db.session.query(func.count(func.distinct(VisitorTraffic.session_id))).filter(VisitorTraffic.created_at >= cutoff).scalar() or 0

    popular_pages = db.session.query(
        VisitorTraffic.path, func.count(VisitorTraffic.id).label('views')
    ).filter(VisitorTraffic.created_at >= cutoff).group_by(VisitorTraffic.path).order_by(desc('views')).limit(8).all()

    browsers = db.session.query(
        VisitorTraffic.browser, func.count(VisitorTraffic.id).label('count')
    ).filter(VisitorTraffic.created_at >= cutoff).group_by(VisitorTraffic.browser).order_by(desc('count')).limit(5).all()

    devices = db.session.query(
        VisitorTraffic.device_type, func.count(VisitorTraffic.id).label('count')
    ).filter(VisitorTraffic.created_at >= cutoff).group_by(VisitorTraffic.device_type).all()

    return render_template(
        'admin/analytics.html',
        days=days,
        total_views=total_views,
        unique_sessions=unique_sessions,
        guest_views=total_views,
        registered_views=0,
        popular_pages=popular_pages,
        browsers=browsers,
        devices=devices,
        tests_count=TypingTest.query.filter(TypingTest.completed_at >= cutoff).count(),
        avg_speed=round(db.session.query(func.avg(TypingTest.wpm)).filter(TypingTest.completed_at >= cutoff).scalar() or 0, 1),
        avg_acc=round(db.session.query(func.avg(TypingTest.accuracy)).filter(TypingTest.completed_at >= cutoff).scalar() or 0, 1),
        mode_distribution=[],
        arcade_plays=[],
        user_signups=User.query.filter(User.created_at >= cutoff).count()
    )


@admin_bp.route('/system/health')
@admin_permission_required('website.health')
def system_health():
    t0 = time.perf_counter()
    try:
        with db.engine.connect() as conn: conn.execute(text("SELECT 1"))
        db_ping_ms = round((time.perf_counter() - t0) * 1000, 2)
        db_status = "Nominal"
    except Exception as e:
        db_ping_ms = None
        db_status = f"Warning: {str(e)[:40]}"

    unique_sessions = db.session.query(func.count(func.distinct(VisitorTraffic.session_id))).scalar() or 0

    table_stats = {
        'Users': User.query.count(),
        'Unique Visitor Sessions': unique_sessions,
        'Visitor Traffic Logs': VisitorTraffic.query.count(),
        'Typing Tests': TypingTest.query.count(),
        'Benchmark Texts': TypingText.query.count(),
        'Arcade Games': ArcadeGameConfig.query.count(),
        'Daily Challenges': DailyChallenge.query.count(),
        'Audit Entries': AdminAuditLog.query.count(),
        'Restricted IPs': BlockedIP.query.count()
    }

    security_checks = [
        ('Centralized Timezone', 'IST (UTC+05:30)'),
        ('Session Cookies', 'Secure & HttpOnly'),
        ('Human Ceiling Cutoff', '250 Net WPM')
    ]

    return render_template(
        'admin/system_health.html',
        python_version=sys.version.split()[0],
        db_status=db_status,
        db_engine=getattr(db.engine, 'name', 'sqlite').upper(),
        db_ping_ms=db_ping_ms,
        db_size_mb=None,
        unique_visitor_sessions=unique_sessions,
        table_stats=table_stats,
        security_checks=security_checks,
        now_ist=now_ist()
    )


@admin_bp.route('/system/data')
@admin_permission_required('website.settings')
def data_management():
    counts = {
        'traffic': VisitorTraffic.query.count(),
        'security': SecurityEvent.query.count(),
        'audits': AdminAuditLog.query.count(),
        'tests': TypingTest.query.count(),
        'guests_tests': TypingTest.query.filter(TypingTest.user_id.is_(None)).count(),
        'blocked_ips': BlockedIP.query.count()
    }
    return render_template('admin/data_management.html', counts=counts)


@admin_bp.route('/system/data/cleanup', methods=['POST'])
@admin_permission_required('website.settings')
def data_cleanup():
    target = request.form.get('target')
    retention_days = request.form.get('retention_days', 30, type=int)
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    del_count = 0

    if target == 'traffic': del_count = VisitorTraffic.query.filter(VisitorTraffic.created_at < cutoff).delete()
    elif target == 'security': del_count = SecurityEvent.query.filter(SecurityEvent.created_at < cutoff, SecurityEvent.severity != 'CRITICAL').delete()
    elif target == 'expired_ips': del_count = BlockedIP.query.filter(BlockedIP.is_permanent == False, BlockedIP.expires_at < datetime.utcnow()).delete()
    elif target == 'guest_tests': del_count = TypingTest.query.filter(TypingTest.user_id.is_(None), TypingTest.completed_at < cutoff).delete()

    db.session.commit()
    flash(f"Pruned {del_count} stale records from '{target}'.", "success")
    return redirect(url_for('admin.data_management'))


@admin_bp.route('/audit-logs')
@admin_permission_required('security.audit_logs')
def audit_logs():
    page = request.args.get('page', 1, type=int)
    logs_page = AdminAuditLog.query.order_by(AdminAuditLog.created_at.desc()).paginate(page=page, per_page=30, error_out=False)
    return render_template('admin/audit_logs.html', logs=logs_page, action_filter='', to_ist=to_ist)


@admin_bp.route('/leaderboard')
@admin_permission_required('challenges.moderate')
def leaderboard_manage():
    page = request.args.get('page', 1, type=int)
    tests_page = TypingTest.query.filter(TypingTest.user_id.isnot(None)).order_by(TypingTest.wpm.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/leaderboard.html', tests=tests_page, filter_suspicious='all')


@admin_bp.route('/leaderboard/test/<int:test_id>/toggle-flag', methods=['POST'])
@admin_permission_required('challenges.moderate')
def test_toggle_flag(test_id):
    test = TypingTest.query.get_or_404(test_id)
    test.suspicious = not test.suspicious
    db.session.commit()
    flash(f"Toggled flag for test #{test.id}.", "success")
    return redirect(url_for('admin.leaderboard_manage'))


@admin_bp.route('/leaderboard/test/<int:test_id>/delete', methods=['POST'])
@admin_permission_required('challenges.moderate')
def test_delete(test_id):
    test = TypingTest.query.get_or_404(test_id)
    db.session.delete(test)
    db.session.commit()
    flash(f"Test #{test_id} deleted.", "info")
    return redirect(url_for('admin.leaderboard_manage'))


@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_permission_required('website.settings')
def system_settings():
    keys = ['maintenance_mode', 'allow_registrations', 'default_test_duration', 'min_wpm_cutoff']
    if request.method == 'POST':
        for k in keys:
            val = request.form.get(k, '').strip()
            cfg = PlatformConfig.query.filter_by(key=k).first()
            if not cfg:
                cfg = PlatformConfig(key=k, value=val, updated_by=current_user.username)
                db.session.add(cfg)
            else:
                cfg.value = val
                cfg.updated_by = current_user.username
        db.session.commit()
        flash("Platform parameters saved.", "success")
        return redirect(url_for('admin.system_settings'))

    configs = {c.key: c.value for c in PlatformConfig.query.all()}
    return render_template('admin/settings.html', configs=configs)


@admin_bp.route('/export/<data_type>')
@admin_permission_required('website.exports')
def export_csv(data_type):
    output = io.StringIO()
    writer = csv.writer(output)
    if data_type == 'users':
        writer.writerow(['ID', 'Username', 'Email', 'Callsign', 'Role', 'Elo'])
        for u in User.query.all(): writer.writerow([u.id, u.username, u.email, u.display_callsign, u.role, u.elo_rating])
    elif data_type == 'passages':
        writer.writerow(['ID', 'Title', 'Discipline', 'Difficulty', 'Words', 'Content'])
        for p in TypingText.query.all(): writer.writerow([p.id, p.title, p.category, p.difficulty, p.word_count, p.content])
    else: return "Unknown type", 400

    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=typesphere_{data_type}.csv"})