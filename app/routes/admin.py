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
from app.models.typing import TypingTest, TypingText, TypingDNA
from app.models.challenge import DailyChallenge, Achievement
from app.models.curriculum import LessonStage
from app.models.feedback import ContactMessage, FeedbackItem, RatingReview, Announcement
from app.models.arcade_content import ArcadeGameConfig
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
# 2. LIVE ACTIVE SESSIONS & REAL-TIME STREAM WITH PINNED ADMINS
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
        role_priority = 4  # 1: super_admin, 2: admin, 3: pilot, 4: guest
        username = "Guest Flight"
        callsign = None

        if t.user_id:
            user = User.query.get(t.user_id)
            if user:
                username = f"@{user.username}"
                callsign = user.display_callsign
                if user.is_super_admin:
                    user_role = "super_admin"
                    role_priority = 1  # Super Admin strictly on top
                elif user.is_admin:
                    user_role = "admin"
                    role_priority = 2  # Delegated Admin next
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

    # Point 3 Fix: Sort sessions by role priority (Super Admin top, Admin 2nd), then recency
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
# 3. ROLE BUILDER & CUSTOM ROLE MANAGEMENT
# ==============================================================

@admin_bp.route('/roles')
@admin_permission_required('roles.view')
def roles_list():
    seed_default_roles_if_empty()
    roles = CustomRole.query.order_by(CustomRole.id.asc()).all()
    total_roles = len(roles)
    active_roles = sum(1 for r in roles if r.is_active)
    disabled_roles = total_roles - active_roles
    delegated_users_count = db.session.query(func.count(func.distinct(User.id))).join(User.custom_roles).count()

    return render_template(
        'admin/roles.html',
        roles=roles,
        total_roles=total_roles,
        active_roles=active_roles,
        disabled_roles=disabled_roles,
        delegated_users_count=delegated_users_count
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

        new_role = CustomRole(
            name=name,
            description=description,
            is_active=is_active,
            created_by=current_user.username
        )

        if selected_perm_ids:
            perms = Permission.query.filter(Permission.id.in_(selected_perm_ids)).all()
            new_role.permissions.extend(perms)

        db.session.add(new_role)
        db.session.commit()

        log_admin_action('ROLE_CREATED', 'role', new_role.id, f"Created custom role '{name}' with {len(new_role.permissions)} permissions")
        flash(f"Custom role '{name}' successfully established.", "success")
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

        if not name:
            flash("Role designation cannot be empty.", "danger")
            return render_template('admin/role_form.html', action='Edit', role=role, grouped_perms=grouped_perms)

        existing = CustomRole.query.filter_by(name=name).first()
        if existing and existing.id != role.id:
            flash(f"Another role with the designation '{name}' already exists.", "danger")
            return render_template('admin/role_form.html', action='Edit', role=role, grouped_perms=grouped_perms)

        role.name = name
        role.description = description
        role.is_active = is_active
        role.updated_by = current_user.username

        perms = Permission.query.filter(Permission.id.in_(selected_perm_ids)).all() if selected_perm_ids else []
        role.permissions = perms

        db.session.commit()
        log_admin_action('ROLE_UPDATED', 'role', role.id, f"Updated role '{name}' ({len(perms)} active permissions)")
        flash(f"Custom role '{name}' updated successfully.", "success")
        return redirect(url_for('admin.roles_list'))

    return render_template('admin/role_form.html', action='Edit', role=role, grouped_perms=grouped_perms)


@admin_bp.route('/roles/<int:role_id>/toggle', methods=['POST'])
@admin_permission_required('roles.manage')
def role_toggle(role_id):
    role = CustomRole.query.get_or_404(role_id)
    role.is_active = not role.is_active
    role.updated_by = current_user.username
    db.session.commit()
    log_admin_action('ROLE_TOGGLE', 'role', role.id, f"Role '{role.name}' active state: {role.is_active}")
    flash(f"Role '{role.name}' {'activated' if role.is_active else 'disabled'}.", "success")
    return redirect(url_for('admin.roles_list'))


@admin_bp.route('/roles/<int:role_id>/delete', methods=['POST'])
@admin_permission_required('roles.delete')
def role_delete(role_id):
    role = CustomRole.query.get_or_404(role_id)
    if role.is_system:
        flash("System operational roles cannot be deleted.", "danger")
        return redirect(url_for('admin.roles_list'))

    name = role.name
    db.session.delete(role)
    db.session.commit()
    log_admin_action('ROLE_DELETED', 'role', role_id, f"Deleted custom role '{name}'")
    flash(f"Custom role '{name}' deleted.", "info")
    return redirect(url_for('admin.roles_list'))


@admin_bp.route('/roles/<int:role_id>/duplicate', methods=['POST'])
@admin_permission_required('roles.manage')
def role_duplicate(role_id):
    original = CustomRole.query.get_or_404(role_id)
    copy_name = f"Copy of {original.name}"
    counter = 1
    while CustomRole.query.filter_by(name=copy_name).first():
        copy_name = f"Copy of {original.name} ({counter})"
        counter += 1

    duplicated = CustomRole(
        name=copy_name,
        description=f"Cloned from {original.name}. {original.description or ''}".strip(),
        is_active=original.is_active,
        created_by=current_user.username
    )
    duplicated.permissions = list(original.permissions)
    db.session.add(duplicated)
    db.session.commit()

    log_admin_action('ROLE_DUPLICATED', 'role', duplicated.id, f"Duplicated '{original.name}' into '{copy_name}'")
    flash(f"Duplicated role created: '{copy_name}'.", "success")
    return redirect(url_for('admin.role_edit', role_id=duplicated.id))


# ==============================================================
# 4. USER MANAGEMENT & MULTI-ROLE ASSIGNMENT
# ==============================================================

@admin_bp.route('/users')
@admin_permission_required('users.view')
def users_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')
    role_id_filter = request.args.get('role_id', '', type=str)

    query = User.query
    if search:
        query = query.filter(or_(
            User.username.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
            User.callsign.ilike(f"%{search}%")
        ))

    if status_filter == 'suspended':
        query = query.filter_by(is_suspended=True)
    elif status_filter == 'banned':
        query = query.filter_by(is_banned=True)
    elif status_filter == 'active':
        query = query.filter_by(is_suspended=False, is_banned=False)
    elif status_filter == 'super_admin':
        query = query.filter(or_(User.role == 'super_admin', User.role == 'admin'))

    if role_id_filter and role_id_filter.isdigit():
        query = query.join(User.custom_roles).filter(CustomRole.id == int(role_id_filter))

    users_page = query.order_by(User.id.desc()).paginate(page=page, per_page=20, error_out=False)
    all_roles = CustomRole.query.order_by(CustomRole.name.asc()).all()

    return render_template(
        'admin/users.html',
        users=users_page,
        search=search,
        status_filter=status_filter,
        role_id_filter=role_id_filter,
        roles=all_roles
    )


@admin_bp.route('/users/<int:user_id>/profile')
@admin_permission_required('users.profile')
def user_detail(user_id):
    seed_default_roles_if_empty()
    user = User.query.get_or_404(user_id)
    tests = TypingTest.query.filter_by(user_id=user.id).order_by(TypingTest.completed_at.desc()).limit(15).all()
    games = GameRecord.query.filter_by(user_id=user.id).order_by(GameRecord.created_at.desc()).limit(10).all()
    activities = UserActivity.query.filter_by(user_id=user.id).order_by(UserActivity.created_at.desc()).limit(20).all()
    all_roles = CustomRole.query.filter_by(is_active=True).order_by(CustomRole.name.asc()).all()

    recent_traffic = VisitorTraffic.query.filter_by(user_id=user.id).order_by(VisitorTraffic.created_at.desc()).first()

    all_perms = Permission.query.all()
    effective_codes = user.effective_permissions
    grouped_effective = {}
    for p in all_perms:
        is_granted = ('*' in effective_codes) or (p.code in effective_codes) or (p.category.lower() + '.*' in effective_codes)
        grouped_effective.setdefault(p.category, []).append((p, is_granted))

    return render_template(
        'admin/users_detail.html',
        user=user,
        tests=tests,
        games=games,
        activities=activities,
        all_roles=all_roles,
        recent_traffic=recent_traffic,
        grouped_effective=grouped_effective,
        to_ist=to_ist
    )


@admin_bp.route('/users/<int:user_id>/assign-role', methods=['POST'])
@admin_permission_required('roles.manage')
def assign_user_role(user_id):
    user = User.query.get_or_404(user_id)
    role_id = request.form.get('role_id', type=int)

    if not role_id:
        flash("Please select a valid custom role to assign.", "warning")
        return redirect(url_for('admin.user_detail', user_id=user.id))

    if user.is_super_admin:
        flash("The Super Admin possesses universal clearance; delegated roles do not apply.", "warning")
        return redirect(url_for('admin.user_detail', user_id=user.id))

    role = CustomRole.query.get_or_404(role_id)
    user_role_ids = [r.id for r in user.custom_roles]

    if role.id not in user_role_ids:
        user.custom_roles.append(role)
        db.session.commit()
        log_admin_action('ROLE_ASSIGNED', 'user', user.id, f"Assigned role '{role.name}' to @{user.username}")
        flash(f"Assigned role '{role.name}' to @{user.username}.", "success")
    else:
        flash(f"@{user.username} already holds role '{role.name}'.", "info")

    return redirect(url_for('admin.user_detail', user_id=user.id))


@admin_bp.route('/users/<int:user_id>/remove-role/<int:role_id>', methods=['POST'])
@admin_permission_required('roles.manage')
def remove_user_role(user_id, role_id):
    user = User.query.get_or_404(user_id)
    role = CustomRole.query.get_or_404(role_id)

    if role in user.custom_roles:
        user.custom_roles.remove(role)
        db.session.commit()
        log_admin_action('ROLE_REVOKED', 'user', user.id, f"Revoked role '{role.name}' from @{user.username}")
        flash(f"Role '{role.name}' removed from @{user.username}.", "info")

    return redirect(url_for('admin.user_detail', user_id=user.id))


@admin_bp.route('/users/<int:user_id>/moderate', methods=['POST'])
@admin_permission_required('users.moderate')
def moderate_user(user_id):
    user = User.query.get_or_404(user_id)
    action = request.form.get('action')
    reason = request.form.get('reason', 'Administrative decision').strip()

    if user.is_super_admin:
        flash("The Super Admin cannot be suspended, banned, or deleted.", "danger")
        return redirect(url_for('admin.user_detail', user_id=user.id))

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
        if not current_user.has_permission('users.ban'):
            flash("Permission denied: You lack authority to ban accounts permanently.", "danger")
            return redirect(url_for('admin.user_detail', user_id=user.id))
        user.is_banned = True
        user.status_reason = reason
        log_admin_action('USER_BAN', 'user', user.id, f"Banned permanently. Reason: {reason}")
        flash(f"User @{user.username} banned permanently.", "danger")
    elif action == 'unban':
        if not current_user.has_permission('users.ban'):
            flash("Permission denied: You lack authority to unban accounts.", "danger")
            return redirect(url_for('admin.user_detail', user_id=user.id))
        user.is_banned = False
        user.status_reason = None
        log_admin_action('USER_UNBAN', 'user', user.id, "Ban lifted")
        flash(f"User @{user.username} unbanned.", "success")
    elif action == 'delete':
        if not current_user.is_super_admin and not current_user.has_permission('users.delete'):
            flash("Only the Super Admin or authorized operators can permanently delete accounts.", "danger")
            return redirect(url_for('admin.user_detail', user_id=user.id))
        username = user.username
        db.session.delete(user)
        db.session.commit()
        log_admin_action('USER_DELETE', 'user', user_id, f"Permanently deleted @{username}")
        flash(f"User @{username} permanently deleted.", "info")
        return redirect(url_for('admin.users_list'))

    db.session.commit()
    return redirect(url_for('admin.user_detail', user_id=user.id))


@admin_bp.route('/users/bulk-action', methods=['POST'])
@admin_permission_required('users.moderate')
def users_bulk_action():
    action = request.form.get('action')
    user_ids = request.form.getlist('selected_user_ids', type=int)

    if not user_ids:
        flash("No users were selected.", "warning")
        return redirect(url_for('admin.users_list'))

    users = User.query.filter(User.id.in_(user_ids)).all()
    count = 0

    for u in users:
        if u.is_super_admin or u.id == current_user.id:
            continue
        if action == 'suspend':
            u.is_suspended = True
            u.status_reason = 'Bulk administrative suspension'
            count += 1
        elif action == 'unsuspend':
            u.is_suspended = False
            u.status_reason = None
            count += 1

    db.session.commit()
    log_admin_action('BULK_USER_ACTION', 'user', details=f"Action '{action}' applied to {count} users")
    flash(f"Bulk action '{action}' executed on {count} users.", "success")
    return redirect(url_for('admin.users_list'))


@admin_bp.route('/users/<int:user_id>/impersonate', methods=['POST'])
@admin_permission_required('users.impersonate')
def impersonate_user(user_id):
    target_user = User.query.get_or_404(user_id)
    if target_user.is_super_admin:
        flash("Cannot impersonate the Super Admin.", "danger")
        return redirect(url_for('admin.user_detail', user_id=target_user.id))

    session['admin_impersonator_id'] = current_user.id
    log_admin_action('IMPERSONATION_START', 'user', target_user.id, f"Impersonating @{target_user.username}")
    login_user(target_user)
    flash(f"Simulating session as @{target_user.username}. Use top bar to exit.", "warning")
    return redirect(url_for('typing.test_page'))


@admin_bp.route('/stop-impersonation')
@login_required
def stop_impersonation():
    admin_id = session.pop('admin_impersonator_id', None)
    if not admin_id:
        return redirect(url_for('typing.test_page'))
    admin_user = User.query.get(admin_id)
    if admin_user:
        log_admin_action('IMPERSONATION_END', 'user', current_user.id, "Concluded impersonation session")
        login_user(admin_user)
        flash("Returned to Super Administrator console.", "info")
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('auth.logout'))


# ==============================================================
# 5. GLOBAL COMMAND PALETTE SEARCH API (Ctrl + K)
# ==============================================================

@admin_bp.route('/api/search')
@login_required
def admin_global_search():
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify({'results': []})

    results = []

    if current_user.has_permission('users.view'):
        users = User.query.filter(or_(
            User.username.ilike(f"%{q}%"),
            User.email.ilike(f"%{q}%"),
            User.callsign.ilike(f"%{q}%")
        )).limit(5).all()
        for u in users:
            results.append({
                'category': 'Pilots & Users',
                'title': f"@{u.username} ({u.display_callsign})",
                'subtitle': f"{u.email} &bull; {u.rank_division}",
                'url': url_for('admin.user_detail', user_id=u.id)
            })

    if current_user.has_permission('roles.view'):
        roles = CustomRole.query.filter(CustomRole.name.ilike(f"%{q}%")).limit(4).all()
        for r in roles:
            results.append({
                'category': 'Roles & Permissions',
                'title': r.name,
                'subtitle': f"{len(r.permissions)} permissions &bull; {'Active' if r.is_active else 'Disabled'}",
                'url': url_for('admin.role_edit', role_id=r.id)
            })

    if current_user.has_permission('typing.view'):
        passages = TypingText.query.filter(or_(
            TypingText.title.ilike(f"%{q}%"),
            TypingText.content.ilike(f"%{q}%")
        )).limit(4).all()
        for p in passages:
            results.append({
                'category': 'Typing Passages',
                'title': p.title,
                'subtitle': f"{p.category} &bull; {p.difficulty} &bull; {p.word_count} words",
                'url': url_for('admin.passage_edit', passage_id=p.id)
            })

    if current_user.has_permission('games.view'):
        games = ArcadeGameConfig.query.filter(or_(
            ArcadeGameConfig.display_title.ilike(f"%{q}%"),
            ArcadeGameConfig.game_slug.ilike(f"%{q}%")
        )).limit(4).all()
        for g in games:
            results.append({
                'category': 'Arcade Games',
                'title': g.display_title,
                'subtitle': f"Slug: {g.game_slug} &bull; {'Enabled' if g.is_enabled else 'Disabled'}",
                'url': url_for('admin.game_edit', config_id=g.id)
            })

    shortcuts = [
        ('Dashboard', 'Command Center Overview', url_for('admin.dashboard')),
        ('Live Active Sessions', 'Monitor real-time guest & pilot telemetry', url_for('admin.live_sessions')),
        ('Arcade Hangar Manager', 'Configure arcade game rules & reorder disciplines', url_for('admin.games_list')),
        ('Tactical Challenges', 'Daily challenge & mission control', url_for('admin.challenges_manage')),
        ('Academy Curriculum', 'Manage curriculum tracks & stages', url_for('admin.academy_manage')),
        ('Certificates Hub', 'Verify & audit pilot flight certificates', url_for('admin.certificates_manage')),
        ('Community Operations', 'Reviews, feedback & system announcements', url_for('admin.community_manage')),
        ('Website Control CMS', 'Manage navigation, branding & maintenance mode', url_for('admin.website_control')),
        ('Feature Flags Engine', 'Runtime module toggles', url_for('admin.feature_flags_list')),
        ('System Health', 'Application runtime, DB ping & operational diagnostics', url_for('admin.system_health')),
        ('Data Management', 'Table statistics, data retention & storage cleanup', url_for('admin.data_management')),
        ('Traffic Analytics', 'Visitor & Session Telemetry', url_for('admin.traffic_analytics')),
        ('Security Center', 'Incident Log & Threat Watch', url_for('admin.security_center')),
        ('Action Audit Trail', 'Immutable Admin Ledger', url_for('admin.audit_logs')),
        ('System Parameters', 'Platform Runtime Flags & Settings', url_for('admin.system_settings')),
        ('Leaderboard Verifier', 'Anti-cheat score verification', url_for('admin.leaderboard_manage'))
    ]
    for title, sub, u in shortcuts:
        if q.lower() in title.lower() or q.lower() in sub.lower():
            results.append({
                'category': 'System Navigation',
                'title': title,
                'subtitle': sub,
                'url': u
            })

    return jsonify({'results': results})


# ==============================================================
# 6. TYPING PASSAGE CMS
# ==============================================================

@admin_bp.route('/passages')
@admin_permission_required('typing.view')
def passages_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    category = request.args.get('category', '')
    difficulty = request.args.get('difficulty', '')

    query = TypingText.query
    if search:
        query = query.filter(or_(TypingText.title.ilike(f"%{search}%"), TypingText.content.ilike(f"%{search}%")))
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
@admin_permission_required('typing.create')
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
@admin_permission_required('typing.edit')
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


@admin_bp.route('/passages/<int:passage_id>/duplicate', methods=['POST'])
@admin_permission_required('typing.create')
def passage_duplicate(passage_id):
    original = TypingText.query.get_or_404(passage_id)
    cloned = TypingText(
        title=f"Copy of {original.title}",
        category=original.category,
        difficulty=original.difficulty,
        content=original.content,
        source=original.source,
        is_code=original.is_code,
        code_lang=original.code_lang,
        is_active=original.is_active,
        created_by=current_user.username
    )
    cloned.calculate_stats()
    db.session.add(cloned)
    db.session.commit()
    log_admin_action('PASSAGE_DUPLICATE', 'passage', cloned.id, f"Cloned passage #{original.id} into #{cloned.id}")
    flash(f"Passage duplicated as #{cloned.id}.", "success")
    return redirect(url_for('admin.passage_edit', passage_id=cloned.id))


@admin_bp.route('/passages/<int:passage_id>/delete', methods=['POST'])
@admin_permission_required('typing.delete')
def passage_delete(passage_id):
    passage = TypingText.query.get_or_404(passage_id)
    title = passage.title
    db.session.delete(passage)
    db.session.commit()
    log_admin_action('PASSAGE_DELETE', 'passage', passage_id, f"Deleted '{title}'")
    flash("Passage deleted.", "info")
    return redirect(url_for('admin.passages_list'))


@admin_bp.route('/passages/<int:passage_id>/toggle-status', methods=['POST'])
@admin_permission_required('typing.publish')
def passage_toggle(passage_id):
    passage = TypingText.query.get_or_404(passage_id)
    passage.is_active = not passage.is_active
    db.session.commit()
    log_admin_action('PASSAGE_TOGGLE', 'passage', passage.id, f"Active state: {passage.is_active}")
    return redirect(url_for('admin.passages_list'))


# ==============================================================
# 7. ARCADE GAME MANAGER & DRAG-AND-DROP REORDER
# ==============================================================

@admin_bp.route('/games')
@admin_permission_required('games.view')
def games_list():
    purge_keyboard_quest_config()

    try:
        games = ArcadeGameConfig.query.filter(
            ArcadeGameConfig.game_slug != 'keyboard_quest'
        ).order_by(ArcadeGameConfig.display_order.asc(), ArcadeGameConfig.id.asc()).all()
    except Exception:
        games = ArcadeGameConfig.query.filter(
            ArcadeGameConfig.game_slug != 'keyboard_quest'
        ).order_by(ArcadeGameConfig.id.asc()).all()

    total_games = len(games)
    active_games = sum(1 for g in games if g.is_enabled)
    return render_template('admin/games.html', games=games, total_games=total_games, active_games=active_games)


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
        log_admin_action('GAME_CONFIG_UPDATE', 'arcade_game', game.id, f"Updated configuration for '{game.display_title}'")
        flash(f"Configuration for '{game.display_title}' updated successfully.", "success")
        return redirect(url_for('admin.games_list'))

    return render_template('admin/game_form.html', game=game)


@admin_bp.route('/games/<int:config_id>/toggle', methods=['POST'])
@admin_permission_required('games.toggle')
def game_toggle(config_id):
    game = ArcadeGameConfig.query.get_or_404(config_id)
    game.is_enabled = not game.is_enabled
    db.session.commit()
    log_admin_action('GAME_TOGGLE', 'arcade_game', game.id, f"Game '{game.display_title}' active state: {game.is_enabled}")
    flash(f"Game '{game.display_title}' {'enabled' if game.is_enabled else 'disabled'}.", "success")
    return redirect(url_for('admin.games_list'))


@admin_bp.route('/games/reorder', methods=['POST'])
@admin_permission_required('games.edit')
def reorder_games():
    payload = request.get_json(silent=True) or {}
    ordered_ids = payload.get('ordered_ids', [])

    if not ordered_ids:
        return jsonify({'success': False, 'message': 'No sequence array provided.'}), 400

    try:
        for idx, gid in enumerate(ordered_ids, start=1):
            g = ArcadeGameConfig.query.get(gid)
            if g:
                g.display_order = idx
        db.session.commit()
        log_admin_action('GAMES_REORDER', 'arcade_game', details=f"Reordered {len(ordered_ids)} disciplines")
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================
# 8. TACTICAL MISSIONS & DAILY CHALLENGE MANAGEMENT
# ==============================================================

@admin_bp.route('/challenges')
@admin_permission_required('challenges.view')
def challenges_manage():
    today = ist_today()
    current_daily = DailyChallenge.query.filter_by(target_date=today).first()
    past_dailies = DailyChallenge.query.order_by(DailyChallenge.target_date.desc()).limit(30).all()
    total_missions_completed = TypingTest.query.filter(TypingTest.mode.like('mission_%')).count()

    return render_template(
        'admin/challenges.html',
        current_daily=current_daily,
        past_dailies=past_dailies,
        today_date=today,
        total_missions_completed=total_missions_completed
    )


@admin_bp.route('/challenges/publish-daily', methods=['POST'])
@admin_permission_required('challenges.manage')
def publish_daily_challenge():
    target_date_str = request.form.get('target_date', '').strip()
    title = request.form.get('title', 'Daily Flight Mastery').strip()
    content = request.form.get('content', '').strip()

    if not content:
        flash("Challenge briefing passage cannot be empty.", "danger")
        return redirect(url_for('admin.challenges_manage'))

    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else ist_today()
    except ValueError:
        target_date = ist_today()

    existing = DailyChallenge.query.filter_by(target_date=target_date).first()
    if existing:
        existing.title = title
        existing.content = content
        log_admin_action('DAILY_CHALLENGE_UPDATE', 'challenge', existing.id, f"Updated Daily Challenge for {target_date}")
        flash(f"Daily Challenge for {target_date} updated successfully.", "success")
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


# ==============================================================
# 9. ACADEMY CURRICULUM CMS
# ==============================================================

@admin_bp.route('/academy')
@admin_permission_required('academy.view')
def academy_manage():
    stages = LessonStage.query.order_by(LessonStage.track.asc(), LessonStage.stage_number.asc()).all()
    grouped = {}
    for st in stages:
        grouped.setdefault(st.track, []).append(st)

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
        log_admin_action('STAGE_UPDATE', 'academy_stage', stage.id, f"Updated Stage {stage.stage_number} ({stage.track})")
        flash(f"Stage '{stage.title}' updated successfully.", "success")
        return redirect(url_for('admin.academy_manage'))

    return render_template('admin/stage_form.html', stage=stage)


# ==============================================================
# 10. CERTIFICATES VERIFIER & REVOCATION HUB
# ==============================================================

@admin_bp.route('/certificates')
@admin_permission_required('certificates.view')
def certificates_manage():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()

    query = TypingTest.query.filter(
        TypingTest.user_id.isnot(None),
        TypingTest.wpm >= 35.0,
        TypingTest.accuracy >= 90.0
    )

    if search:
        query = query.join(User).filter(or_(
            User.username.ilike(f"%{search}%"),
            User.callsign.ilike(f"%{search}%")
        ))

    tests = query.order_by(TypingTest.completed_at.desc()).paginate(page=page, per_page=20, error_out=False)

    return render_template('admin/certificates.html', tests=tests, search=search, to_ist=to_ist, hashlib=hashlib)


@admin_bp.route('/certificates/<int:test_id>/revoke', methods=['POST'])
@admin_permission_required('certificates.revoke')
def certificate_revoke(test_id):
    test = TypingTest.query.get_or_404(test_id)
    reason = request.form.get('reason', 'Administrative certificate revocation').strip()

    test.suspicious = True
    test.suspicion_reason = reason
    db.session.commit()

    log_admin_action('CERTIFICATE_REVOKED', 'typing_test', test.id, f"Revoked certificate. Reason: {reason}")
    flash(f"Certificate for Test #{test.id} revoked.", "warning")
    return redirect(url_for('admin.certificates_manage'))


@admin_bp.route('/certificates/<int:test_id>/restore', methods=['POST'])
@admin_permission_required('certificates.revoke')
def certificate_restore(test_id):
    test = TypingTest.query.get_or_404(test_id)
    test.suspicious = False
    test.suspicion_reason = None
    db.session.commit()

    log_admin_action('CERTIFICATE_RESTORED', 'typing_test', test.id, "Restored certificate validity")
    flash(f"Certificate for Test #{test.id} reinstated.", "success")
    return redirect(url_for('admin.certificates_manage'))


# ==============================================================
# 11. COMMUNITY REVIEWS, FEEDBACK & ANNOUNCEMENTS
# ==============================================================

@admin_bp.route('/community')
@admin_permission_required('reviews.view')
def community_manage():
    # Auto-seed exemplary reviews if completely empty so the admin can test moderation immediately
    try:
        if RatingReview.query.count() == 0 and User.query.first():
            first_user = User.query.first()
            sample_reviews = [
                (first_user.id, 5, "Best Aeronautical Cockpit Interface", "The tactile response and real-time cadence tracking completely changed my exam speed. Best typing platform ever.", True),
            ]
            for u_id, rating, title, text_c, apprv in sample_reviews:
                db.session.add(RatingReview(user_id=u_id, rating=rating, review_title=title, review_text=text_c, is_approved=apprv))
            db.session.commit()
    except Exception:
        db.session.rollback()

    reviews = RatingReview.query.order_by(RatingReview.created_at.desc()).all()
    feedbacks = FeedbackItem.query.order_by(FeedbackItem.created_at.desc()).all()
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    inquiries = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(25).all()

    return render_template(
        'admin/community.html',
        reviews=reviews,
        feedbacks=feedbacks,
        announcements=announcements,
        inquiries=inquiries,
        to_ist=to_ist
    )


@admin_bp.route('/community/reviews/create-official', methods=['POST'])
@admin_permission_required('reviews.moderate')
def create_official_review():
    """Allows Super Admin to seed and test reviews directly from Control Center."""
    title = request.form.get('review_title', '').strip()
    text_content = request.form.get('review_text', '').strip()
    rating = request.form.get('rating', 5, type=int)

    if not title or not text_content:
        flash("Title and review content are required.", "danger")
        return redirect(url_for('admin.community_manage'))

    new_rev = RatingReview(
        user_id=current_user.id,
        rating=max(1, min(5, rating)),
        review_title=title,
        review_text=text_content,
        is_approved=True
    )
    db.session.add(new_rev)
    db.session.commit()

    log_admin_action('REVIEW_OFFICIAL_CREATE', 'review', new_rev.id, f"Created official review: {title}")
    flash("Official community review published and approved.", "success")
    return redirect(url_for('admin.community_manage'))


@admin_bp.route('/announcements/create', methods=['POST'])
@admin_permission_required('announcements.manage')
def create_announcement():
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()

    if not title or not content:
        flash("Announcement title and message cannot be empty.", "danger")
        return redirect(url_for('admin.community_manage'))

    new_a = Announcement(title=title, content=content, is_active=True)
    db.session.add(new_a)
    db.session.commit()

    log_admin_action('ANNOUNCEMENT_CREATE', 'announcement', new_a.id, f"Published banner: {title}")
    flash(f"Announcement '{title}' published.", "success")
    return redirect(url_for('admin.community_manage'))


@admin_bp.route('/announcements/<int:announcement_id>/toggle', methods=['POST'])
@admin_permission_required('announcements.manage')
def toggle_announcement(announcement_id):
    a = Announcement.query.get_or_404(announcement_id)
    a.is_active = not a.is_active
    db.session.commit()
    log_admin_action('ANNOUNCEMENT_TOGGLE', 'announcement', a.id, f"Announcement active: {a.is_active}")
    flash(f"Announcement '{a.title}' {'activated' if a.is_active else 'archived'}.", "info")
    return redirect(url_for('admin.community_manage'))


@admin_bp.route('/announcements/<int:announcement_id>/delete', methods=['POST'])
@admin_permission_required('announcements.manage')
def delete_announcement(announcement_id):
    a = Announcement.query.get_or_404(announcement_id)
    title = a.title
    db.session.delete(a)
    db.session.commit()
    log_admin_action('ANNOUNCEMENT_DELETE', 'announcement', announcement_id, f"Deleted: {title}")
    flash("Announcement deleted.", "info")
    return redirect(url_for('admin.community_manage'))


@admin_bp.route('/reviews/<int:review_id>/toggle', methods=['POST'])
@admin_permission_required('reviews.moderate')
def toggle_review(review_id):
    r = RatingReview.query.get_or_404(review_id)
    r.is_approved = not r.is_approved
    db.session.commit()
    log_admin_action('REVIEW_TOGGLE', 'review', r.id, f"Review approved: {r.is_approved}")
    flash("Review visibility toggled.", "success")
    return redirect(url_for('admin.community_manage'))


@admin_bp.route('/reviews/<int:review_id>/delete', methods=['POST'])
@admin_permission_required('reviews.moderate')
def delete_review(review_id):
    r = RatingReview.query.get_or_404(review_id)
    db.session.delete(r)
    db.session.commit()
    log_admin_action('REVIEW_DELETE', 'review', review_id, "Deleted pilot review")
    flash("Review removed.", "info")
    return redirect(url_for('admin.community_manage'))


@admin_bp.route('/feedback/<int:feedback_id>/respond', methods=['POST'])
@admin_permission_required('feedback.manage')
def respond_feedback(feedback_id):
    fb = FeedbackItem.query.get_or_404(feedback_id)
    status = request.form.get('status', 'Resolved')
    response = request.form.get('admin_response', '').strip()

    fb.status = status
    if response:
        fb.admin_response = response
    db.session.commit()

    log_admin_action('FEEDBACK_RESPOND', 'feedback', fb.id, f"Status: {status}")
    flash("Feedback updated with operational response.", "success")
    return redirect(url_for('admin.community_manage'))


# ==============================================================
# 12. SECURITY & ACTIVE IP MANAGEMENT
# ==============================================================

@admin_bp.route('/security')
@admin_permission_required('security.events_view')
def security_center():
    page = request.args.get('page', 1, type=int)
    severity_filter = request.args.get('severity', '').strip()
    search = request.args.get('q', '').strip()

    query = SecurityEvent.query
    if severity_filter:
        query = query.filter_by(severity=severity_filter.upper())
    if search:
        query = query.filter(or_(
            SecurityEvent.identifier.ilike(f"%{search}%"),
            SecurityEvent.description.ilike(f"%{search}%"),
            SecurityEvent.ip_address.ilike(f"%{search}%")
        ))

    events = query.order_by(SecurityEvent.created_at.desc()).paginate(page=page, per_page=25, error_out=False)
    failed_logins = SecurityEvent.query.filter_by(event_type='FAILED_LOGIN').count()
    critical_events = SecurityEvent.query.filter_by(severity='CRITICAL').count()
    blocked_ips = BlockedIP.query.order_by(BlockedIP.created_at.desc()).all()

    return render_template(
        'admin/security.html',
        events=events,
        failed_logins=failed_logins,
        critical_events=critical_events,
        blocked_ips=blocked_ips,
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
    duration_hours = request.form.get('duration_hours', 24, type=int)

    if not ip:
        flash("IP address cannot be blank.", "danger")
        return redirect(url_for('admin.security_center'))

    block_ip(ip, reason, is_permanent=is_perm, duration_hours=duration_hours, blocked_by=current_user.username)
    flash(f"IP address {ip} restricted successfully.", "success")
    return redirect(url_for('admin.security_center'))


@admin_bp.route('/security/unblock-ip/<int:block_id>', methods=['POST'])
@admin_permission_required('security.ip_manage')
def handle_unblock_ip(block_id):
    b = BlockedIP.query.get_or_404(block_id)
    ip = b.ip_address
    unblock_ip(ip, unblocked_by=current_user.username)
    flash(f"Restriction lifted for IP {ip}.", "success")
    return redirect(url_for('admin.security_center'))


# ==============================================================
# 13. WEBSITE CONTROL, MAINTENANCE & PRESERVED SCROLL CMS
# ==============================================================

@admin_bp.route('/website')
@admin_permission_required('website.settings')
def website_control():
    nav_items = SiteNavigationItem.query.order_by(SiteNavigationItem.nav_order.asc()).all()
    maintenance_cfg = PlatformConfig.query.filter_by(key='maintenance_mode').first()
    maintenance_msg_cfg = PlatformConfig.query.filter_by(key='maintenance_message').first()
    brand_cfg = PlatformConfig.query.filter_by(key='site_tagline').first()

    return render_template(
        'admin/website.html',
        nav_items=nav_items,
        is_maintenance=bool(maintenance_cfg and maintenance_cfg.value.lower() == 'true'),
        maintenance_msg=maintenance_msg_cfg.value if maintenance_msg_cfg else "Scheduled flight calibration underway.",
        tagline=brand_cfg.value if brand_cfg else "Next-Generation Flight Intelligence & Biometric Telemetry Engine."
    )


@admin_bp.route('/website/maintenance/toggle', methods=['POST'])
@admin_permission_required('website.settings')
def toggle_maintenance():
    cfg = PlatformConfig.query.filter_by(key='maintenance_mode').first()
    msg_val = request.form.get('maintenance_message', '').strip()

    if not cfg:
        cfg = PlatformConfig(key='maintenance_mode', value='true', updated_by=current_user.username)
        db.session.add(cfg)
    else:
        cfg.value = 'false' if cfg.value.lower() == 'true' else 'true'
        cfg.updated_by = current_user.username

    if msg_val:
        msg_cfg = PlatformConfig.query.filter_by(key='maintenance_message').first()
        if not msg_cfg:
            msg_cfg = PlatformConfig(key='maintenance_message', value=msg_val, updated_by=current_user.username)
            db.session.add(msg_cfg)
        else:
            msg_cfg.value = msg_val
            msg_cfg.updated_by = current_user.username

    db.session.commit()
    log_admin_action('MAINTENANCE_TOGGLE', 'system', details=f"Maintenance mode set to {cfg.value}")
    flash(f"Maintenance protocol {'engaged (Public blocked)' if cfg.value == 'true' else 'disengaged (Normal operations)'}.", "warning" if cfg.value == 'true' else "success")
    return redirect(url_for('admin.website_control'))


@admin_bp.route('/website/navigation/add', methods=['POST'])
@admin_permission_required('website.settings')
def add_navigation_item():
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
    if request.is_json:
        data = request.get_json(silent=True) or {}
        label = data.get('label', '').strip()
        url = data.get('url', '').strip()
        color = data.get('highlight_color', '').strip() or None
        for_guests = bool(data.get('for_guests', True))
        for_pilots = bool(data.get('for_pilots', True))
    else:
        label = request.form.get('label', '').strip()
        url = request.form.get('url', '').strip()
        color = request.form.get('highlight_color', '').strip() or None
        for_guests = request.form.get('for_guests') == 'on'
        for_pilots = request.form.get('for_pilots') == 'on'

    if not label or not url:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Link label and URL cannot be blank.'}), 400
        flash("Link label and target URL cannot be empty.", "danger")
        return redirect(url_for('admin.website_control'))

    max_order = db.session.query(func.max(SiteNavigationItem.nav_order)).scalar() or 0
    new_nav = SiteNavigationItem(
        label=label,
        url=url,
        nav_order=max_order + 1,
        is_visible=True,
        for_guests=for_guests,
        for_pilots=for_pilots,
        highlight_color=color
    )
    db.session.add(new_nav)
    db.session.commit()

    log_admin_action('NAV_ITEM_CREATE', 'website', new_nav.id, f"Added navigation link: '{label}' -> {url}")

    if is_ajax:
        return jsonify({'success': True, 'message': f"Navigation link '{label}' added successfully."})

    flash(f"Navigation item '{label}' added.", "success")
    return redirect(url_for('admin.website_control') + '#nav-section')


@admin_bp.route('/website/navigation/<int:item_id>/edit', methods=['POST'])
@admin_permission_required('website.settings')
def edit_navigation_item(item_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
    item = SiteNavigationItem.query.get_or_404(item_id)

    if request.is_json:
        data = request.get_json(silent=True) or {}
        item.label = data.get('label', item.label).strip()
        item.url = data.get('url', item.url).strip()
        item.nav_order = int(data.get('nav_order', item.nav_order))
        item.is_visible = bool(data.get('is_visible', True))
        item.for_guests = bool(data.get('for_guests', True))
        item.for_pilots = bool(data.get('for_pilots', True))
    else:
        item.label = request.form.get('label', item.label).strip()
        item.url = request.form.get('url', item.url).strip()
        item.nav_order = request.form.get('nav_order', item.nav_order, type=int)
        item.is_visible = request.form.get('is_visible') == 'on'
        item.for_guests = request.form.get('for_guests') == 'on'
        item.for_pilots = request.form.get('for_pilots') == 'on'

    db.session.commit()
    log_admin_action('NAV_ITEM_UPDATE', 'website', item.id, f"Updated link '{item.label}'")

    if is_ajax:
        return jsonify({'success': True, 'message': f"Updated link '{item.label}' in place."})

    flash(f"Navigation item '{item.label}' updated.", "success")
    return redirect(url_for('admin.website_control') + f'#nav-row-{item.id}')


@admin_bp.route('/website/navigation/<int:item_id>/delete', methods=['POST'])
@admin_permission_required('website.settings')
def delete_navigation_item(item_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
    item = SiteNavigationItem.query.get_or_404(item_id)
    label = item.label
    db.session.delete(item)
    db.session.commit()
    log_admin_action('NAV_ITEM_DELETE', 'website', item_id, f"Deleted link '{label}'")

    if is_ajax:
        return jsonify({'success': True, 'message': f"Deleted link '{label}'."})

    flash(f"Navigation item '{label}' deleted.", "info")
    return redirect(url_for('admin.website_control') + '#nav-section')


# ==============================================================
# 14. RUNTIME FEATURE FLAGS ENGINE
# ==============================================================

@admin_bp.route('/flags')
@admin_permission_required('website.flags')
def feature_flags_list():
    flags = FeatureFlag.query.order_by(FeatureFlag.id.asc()).all()
    return render_template('admin/flags.html', flags=flags)


@admin_bp.route('/flags/create', methods=['POST'])
@admin_permission_required('website.flags')
def create_feature_flag():
    key = request.form.get('key', '').strip().lower().replace(' ', '_')
    label = request.form.get('label', '').strip()
    desc = request.form.get('description', '').strip()
    is_enabled = request.form.get('is_enabled') == 'on'

    if not key or not label:
        flash("Flag key and display label are mandatory.", "danger")
        return redirect(url_for('admin.feature_flags_list'))

    if FeatureFlag.query.filter_by(key=key).first():
        flash(f"Feature flag with key '{key}' already exists.", "danger")
        return redirect(url_for('admin.feature_flags_list'))

    new_flag = FeatureFlag(
        key=key,
        label=label,
        description=desc,
        is_enabled=is_enabled,
        updated_by=current_user.username
    )
    db.session.add(new_flag)
    db.session.commit()

    log_admin_action('FLAG_CREATE', 'feature_flag', new_flag.id, f"Created flag '{key}': {is_enabled}")
    flash(f"Feature flag '{key}' created.", "success")
    return redirect(url_for('admin.feature_flags_list'))


@admin_bp.route('/flags/<int:flag_id>/toggle', methods=['POST'])
@admin_permission_required('website.flags')
def toggle_feature_flag(flag_id):
    flag = FeatureFlag.query.get_or_404(flag_id)
    flag.is_enabled = not flag.is_enabled
    flag.updated_by = current_user.username
    db.session.commit()

    log_admin_action('FLAG_TOGGLE', 'feature_flag', flag.id, f"Flag '{flag.key}' set to {flag.is_enabled}")
    flash(f"Flag '{flag.key}' {'enabled' if flag.is_enabled else 'disabled'}.", "success")
    return redirect(url_for('admin.feature_flags_list'))


# ==============================================================
# 15. 5-DIMENSION ANALYTICS HUB
# ==============================================================

@admin_bp.route('/analytics')
@admin_permission_required('analytics.traffic')
def traffic_analytics():
    days = request.args.get('days', 30, type=int)
    cutoff = datetime.utcnow() - timedelta(days=days)

    total_views = VisitorTraffic.query.filter(VisitorTraffic.created_at >= cutoff).count()
    unique_sessions = db.session.query(func.count(func.distinct(VisitorTraffic.session_id))).filter(VisitorTraffic.created_at >= cutoff).scalar() or 0
    registered_views = VisitorTraffic.query.filter(VisitorTraffic.created_at >= cutoff, VisitorTraffic.user_id.isnot(None)).count()
    guest_views = total_views - registered_views

    popular_pages = db.session.query(
        VisitorTraffic.path, func.count(VisitorTraffic.id).label('views')
    ).filter(VisitorTraffic.created_at >= cutoff).group_by(VisitorTraffic.path).order_by(desc('views')).limit(8).all()

    browsers = db.session.query(
        VisitorTraffic.browser, func.count(VisitorTraffic.id).label('count')
    ).filter(VisitorTraffic.created_at >= cutoff).group_by(VisitorTraffic.browser).order_by(desc('count')).limit(5).all()

    devices = db.session.query(
        VisitorTraffic.device_type, func.count(VisitorTraffic.id).label('count')
    ).filter(VisitorTraffic.created_at >= cutoff).group_by(VisitorTraffic.device_type).all()

    tests_count = TypingTest.query.filter(TypingTest.completed_at >= cutoff).count()
    avg_speed = db.session.query(func.avg(TypingTest.wpm)).filter(TypingTest.completed_at >= cutoff).scalar() or 0
    avg_acc = db.session.query(func.avg(TypingTest.accuracy)).filter(TypingTest.completed_at >= cutoff).scalar() or 0

    mode_distribution = db.session.query(
        TypingTest.mode, func.count(TypingTest.id).label('count')
    ).filter(TypingTest.completed_at >= cutoff).group_by(TypingTest.mode).order_by(desc('count')).limit(5).all()

    arcade_plays = db.session.query(
        GameRecord.game_mode, func.count(GameRecord.id).label('plays')
    ).filter(GameRecord.created_at >= cutoff).group_by(GameRecord.game_mode).order_by(desc('plays')).limit(5).all()

    user_signups = User.query.filter(User.created_at >= cutoff).count()

    return render_template(
        'admin/analytics.html',
        days=days,
        total_views=total_views,
        unique_sessions=unique_sessions,
        guest_views=guest_views,
        registered_views=registered_views,
        popular_pages=popular_pages,
        browsers=browsers,
        devices=devices,
        tests_count=tests_count,
        avg_speed=round(avg_speed, 1),
        avg_acc=round(avg_acc, 1),
        mode_distribution=mode_distribution,
        arcade_plays=arcade_plays,
        user_signups=user_signups
    )


# ==============================================================
# 16. SYSTEM HEALTH & DATA RETENTION MANAGEMENT (WITH UNIQUE VISITS)
# ==============================================================

@admin_bp.route('/system/health')
@admin_permission_required('website.health')
def system_health():
    t0 = time.perf_counter()
    try:
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ping_ms = round((time.perf_counter() - t0) * 1000, 2)
        db_status = "Nominal"
    except Exception as e:
        db_ping_ms = None
        db_status = f"Warning: {str(e)[:40]}"

    db_engine = getattr(db.engine, 'name', 'sqlite').upper()

    db_size_mb = None
    if "SQLITE" in db_engine:
        try:
            db_path = getattr(db.engine.url, 'database', None)
            if db_path and os.path.exists(db_path):
                db_size_mb = round(os.path.getsize(db_path) / (1024 * 1024), 2)
        except Exception:
            pass

    def safe_count(model):
        try:
            return model.query.count()
        except Exception:
            db.session.rollback()
            return 0

    # Point 6 Fix: Unique Visits & IP Counts
    try:
        unique_visitor_sessions = db.session.query(func.count(func.distinct(VisitorTraffic.session_id))).scalar() or 0
        unique_ip_visitors = db.session.query(func.count(func.distinct(VisitorTraffic.ip_address))).scalar() or 0
    except Exception:
        unique_visitor_sessions = 0
        unique_ip_visitors = 0

    table_stats = {
        'Users': safe_count(User),
        'Unique Visitor Sessions': unique_visitor_sessions,
        'Unique IP Visitors': unique_ip_visitors,
        'Visitor Traffic Records': safe_count(VisitorTraffic),
        'Typing Tests': safe_count(TypingTest),
        'Typing Passages': safe_count(TypingText),
        'Game Records': safe_count(GameRecord),
        'Audit Entries': safe_count(AdminAuditLog),
        'Security Incidents': safe_count(SecurityEvent),
        'Custom Roles': safe_count(CustomRole),
        'Restricted IPs': safe_count(BlockedIP)
    }

    mail_configured = bool(os.environ.get('MAIL_USERNAME') and 'your_' not in os.environ.get('MAIL_USERNAME', ''))
    cutoff_cfg = PlatformConfig.query.filter_by(key='min_wpm_cutoff').first()
    cutoff_val = cutoff_cfg.value if cutoff_cfg and cutoff_cfg.value else '250'

    security_checks = [
        ('Session Cookie HTTPOnly', True),
        ('Session Cookie SameSite', 'Lax'),
        ('Centralized Timezone', 'IST (UTC+05:30)'),
        ('SMTP Dispatch Gateway', 'Configured' if mail_configured else 'Standby / Local'),
        ('Anti-Cheat Human Ceiling', f"{cutoff_val} Net WPM")
    ]

    return render_template(
        'admin/system_health.html',
        python_version=sys.version.split()[0],
        db_status=db_status,
        db_engine=db_engine,
        db_ping_ms=db_ping_ms,
        db_size_mb=db_size_mb,
        unique_visitor_sessions=unique_visitor_sessions,
        table_stats=table_stats,
        security_checks=security_checks,
        now_ist=now_ist()
    )


@admin_bp.route('/system/data')
@admin_permission_required('website.settings')
def data_management():
    def safe_count(model):
        try:
            return model.query.count()
        except Exception:
            db.session.rollback()
            return 0

    counts = {
        'traffic': safe_count(VisitorTraffic),
        'security': safe_count(SecurityEvent),
        'audits': safe_count(AdminAuditLog),
        'tests': safe_count(TypingTest),
        'guests_tests': TypingTest.query.filter(TypingTest.user_id.is_(None)).count() if hasattr(TypingTest, 'user_id') else 0,
        'blocked_ips': safe_count(BlockedIP)
    }
    return render_template('admin/data_management.html', counts=counts)


@admin_bp.route('/system/data/cleanup', methods=['POST'])
@admin_permission_required('website.settings')
def data_cleanup():
    target = request.form.get('target')
    retention_days = request.form.get('retention_days', 30, type=int)
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    deleted_count = 0

    try:
        if target == 'traffic':
            deleted_count = VisitorTraffic.query.filter(VisitorTraffic.created_at < cutoff).delete()
        elif target == 'security':
            deleted_count = SecurityEvent.query.filter(SecurityEvent.created_at < cutoff, SecurityEvent.severity != 'CRITICAL').delete()
        elif target == 'expired_ips':
            deleted_count = BlockedIP.query.filter(BlockedIP.is_permanent == False, BlockedIP.expires_at < datetime.utcnow()).delete()
        elif target == 'guest_tests':
            deleted_count = TypingTest.query.filter(TypingTest.user_id.is_(None), TypingTest.completed_at < cutoff).delete()
        else:
            flash("Invalid data retention target.", "danger")
            return redirect(url_for('admin.data_management'))

        db.session.commit()
        log_admin_action('DATA_RETENTION_CLEANUP', 'system', details=f"Pruned {deleted_count} records from '{target}' (older than {retention_days} days)")
        flash(f"Data retention cleanup executed: {deleted_count} records safely pruned from '{target}'.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Data cleanup encountered an error: {str(e)}", "danger")

    return redirect(url_for('admin.data_management'))


# ==============================================================
# 17. AUDIT LOGS, LEADERBOARD, SETTINGS (EXPANDED) & EXPORTS
# ==============================================================

@admin_bp.route('/audit-logs')
@admin_permission_required('security.audit_logs')
def audit_logs():
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '').strip()

    query = AdminAuditLog.query
    if action_filter:
        query = query.filter(AdminAuditLog.action.ilike(f"%{action_filter}%"))
    logs_page = query.order_by(AdminAuditLog.created_at.desc()).paginate(page=page, per_page=30, error_out=False)
    return render_template('admin/audit_logs.html', logs=logs_page, action_filter=action_filter, to_ist=to_ist)


@admin_bp.route('/leaderboard')
@admin_permission_required('challenges.moderate')
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
@admin_permission_required('challenges.moderate')
def test_toggle_flag(test_id):
    test = TypingTest.query.get_or_404(test_id)
    test.suspicious = not test.suspicious
    test.suspicion_reason = "Flagged manually by Administrator" if test.suspicious else None
    db.session.commit()
    log_admin_action('TEST_FLAG_TOGGLE', 'typing_test', test.id, f"Suspicious set to {test.suspicious}")
    flash(f"Test #{test.id} verification state toggled.", "success")
    return redirect(url_for('admin.leaderboard_manage'))


@admin_bp.route('/leaderboard/test/<int:test_id>/delete', methods=['POST'])
@admin_permission_required('challenges.moderate')
def test_delete(test_id):
    test = TypingTest.query.get_or_404(test_id)
    db.session.delete(test)
    db.session.commit()
    log_admin_action('TEST_RECORD_DELETE', 'typing_test', test_id, "Record deleted from leaderboards")
    flash("Typing score record removed.", "info")
    return redirect(url_for('admin.leaderboard_manage'))


@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_permission_required('website.settings')
def system_settings():
    """Point 7 Fix: Comprehensive Platform Runtime Parameters."""
    runtime_keys = [
        'maintenance_mode',
        'allow_registrations',
        'default_test_duration',
        'min_wpm_cutoff',
        'enable_guest_flights',
        'anti_cheat_enforcement',
        'max_active_race_duration',
        'enable_public_leaderboards',
        'daily_challenge_passing_accuracy',
        'session_inactivity_timeout_minutes'
    ]

    if request.method == 'POST':
        for key in runtime_keys:
            val = request.form.get(key, '').strip()
            cfg = PlatformConfig.query.filter_by(key=key).first()
            if not cfg:
                cfg = PlatformConfig(key=key, value=val, updated_by=current_user.username)
                db.session.add(cfg)
            else:
                cfg.value = val
                cfg.updated_by = current_user.username

        db.session.commit()
        log_admin_action('PLATFORM_CONFIG_UPDATE', 'settings', details="Updated runtime parameters in Control Center")
        flash("Platform parameters committed and active live.", "success")
        return redirect(url_for('admin.system_settings'))

    configs = {c.key: c.value for c in PlatformConfig.query.all()}
    return render_template('admin/settings.html', configs=configs)


@admin_bp.route('/export/<data_type>')
@admin_permission_required('website.exports')
def export_csv(data_type):
    log_admin_action('EXPORT_DATA', 'system', details=f"Exported {data_type}.csv")
    output = io.StringIO()
    writer = csv.writer(output)
    if data_type == 'users':
        writer.writerow(['ID', 'Username', 'Email', 'Callsign', 'Role', 'Suspended', 'Banned', 'Elo', 'Created_At'])
        for u in User.query.all():
            writer.writerow([u.id, u.username, u.email, u.display_callsign, u.role, u.is_suspended, u.is_banned, u.elo_rating, u.created_at])
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