"""
TypeSphere - Administrative Security, Audit & Request Telemetry Engine
Enforces server-side authorization checks, uneditable audit logging,
active IP interception, maintenance mode guards, and dynamic context injection.
"""

import uuid
from functools import wraps
from datetime import datetime, timedelta
from flask import request, abort, redirect, url_for, flash, session, render_template
from flask_login import current_user
from app import db
from app.models.admin import (
    AdminAuditLog, VisitorTraffic, SecurityEvent, UserActivity,
    BlockedIP, SYSTEM_PERMISSIONS, Permission, FeatureFlag,
    PlatformConfig, SiteNavigationItem
)
from app.models.feedback import Announcement


def log_admin_action(action: str, target_type: str, target_id=None, details=None):
    """Securely writes an uneditable administrative audit entry."""
    try:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()

        log = AdminAuditLog(
            admin_id=current_user.id if current_user.is_authenticated else None,
            admin_username=current_user.username if current_user.is_authenticated else "System",
            action=action.upper(),
            target_type=target_type.lower(),
            target_id=str(target_id) if target_id is not None else None,
            details=str(details) if details else None,
            ip_address=ip
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()


def log_security_incident(event_type: str, severity: str, description: str, identifier: str = None):
    """Stores critical authentication faults and anomalous requests."""
    try:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()

        ev = SecurityEvent(
            event_type=event_type.upper(),
            severity=severity.upper(),
            identifier=identifier,
            ip_address=ip,
            user_agent=request.user_agent.string[:250] if request.user_agent else "Unknown",
            description=description
        )
        db.session.add(ev)
        db.session.commit()
    except Exception:
        db.session.rollback()


def record_user_activity(user_id: int, action: str, feature: str = "Platform", details: str = None):
    """Logs individual user interactions in chronological activity stream."""
    try:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()

        act = UserActivity(
            user_id=user_id,
            action=action.upper(),
            feature=feature,
            details=details,
            ip_address=ip,
            user_agent=request.user_agent.string[:250] if request.user_agent else "Unknown"
        )
        db.session.add(act)
        db.session.commit()
    except Exception:
        db.session.rollback()


# ==============================================================
# ACTIVE IP CONTROLS
# ==============================================================

def is_ip_blocked(ip: str) -> bool:
    """Checks whether the client IP address is currently restricted."""
    if not ip:
        return False
    clean_ip = ip.split(',')[0].strip()
    blocked = BlockedIP.query.filter_by(ip_address=clean_ip).first()
    if not blocked:
        return False
    return blocked.is_currently_blocked


def block_ip(ip: str, reason: str, is_permanent: bool = False, duration_hours: int = 24, blocked_by: str = 'SuperAdmin') -> bool:
    """Restricts an IP from platform access."""
    clean_ip = ip.split(',')[0].strip()
    expires_at = None if is_permanent else datetime.utcnow() + timedelta(hours=duration_hours)
    
    existing = BlockedIP.query.filter_by(ip_address=clean_ip).first()
    if existing:
        existing.reason = reason
        existing.is_permanent = is_permanent
        existing.expires_at = expires_at
        existing.blocked_by = blocked_by
    else:
        new_block = BlockedIP(
            ip_address=clean_ip,
            reason=reason,
            is_permanent=is_permanent,
            expires_at=expires_at,
            blocked_by=blocked_by
        )
        db.session.add(new_block)

    db.session.commit()
    log_admin_action('IP_BLOCKED', 'security', details=f"Blocked {clean_ip}. Reason: {reason}")
    return True


def unblock_ip(ip: str, unblocked_by: str = 'SuperAdmin') -> bool:
    """Lifts restriction on an IP."""
    clean_ip = ip.split(',')[0].strip()
    existing = BlockedIP.query.filter_by(ip_address=clean_ip).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        log_admin_action('IP_UNBLOCKED', 'security', details=f"Unblocked {clean_ip} by {unblocked_by}")
        return True
    return False


# ==============================================================
# FEATURE FLAGS & MAINTENANCE INTERCEPTION
# ==============================================================

def is_feature_enabled(flag_key: str, default: bool = False) -> bool:
    """Evaluates whether a runtime feature flag is active."""
    try:
        flag = FeatureFlag.query.filter_by(key=flag_key).first()
        if flag:
            return flag.is_enabled
    except Exception:
        pass
    return default


def is_maintenance_active() -> bool:
    """Checks whether the platform is in maintenance lockdown."""
    try:
        cfg = PlatformConfig.query.filter_by(key='maintenance_mode').first()
        return bool(cfg and cfg.value.lower() == 'true')
    except Exception:
        return False


def capture_traffic(app):
    """Before/after request hooks for analytics, last_active, IP interception, and maintenance."""
    @app.before_request
    def intercept_and_track():
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()

        # 1. Enforce active IP blocks
        if is_ip_blocked(client_ip):
            log_security_incident('BLOCKED_IP_CONNECTION_ATTEMPT', 'MEDIUM', f"Blocked IP {client_ip} tried accessing {request.path}", identifier=client_ip)
            abort(403)

        # 2. Enforce platform maintenance mode
        if is_maintenance_active():
            # Allow admins, static files, auth login, and maintenance toggle through
            is_admin_user = current_user.is_authenticated and current_user.is_admin
            exempt_prefixes = ['/static', '/auth', '/admin', '/socket.io']
            is_exempt_path = any(request.path.startswith(prefix) for prefix in exempt_prefixes)

            if not is_admin_user and not is_exempt_path:
                cfg_msg = PlatformConfig.query.filter_by(key='maintenance_message').first()
                msg = cfg_msg.value if cfg_msg else "Flight control systems are undergoing scheduled calibration. Normal flights will resume shortly."
                return render_template('errors/maintenance.html', message=msg), 503

        # 3. Maintain anonymous visitor session token
        if 'visitor_uuid' not in session:
            session['visitor_uuid'] = str(uuid.uuid4())

        # 4. Update last_active timestamp on authenticated accounts
        if current_user.is_authenticated:
            try:
                current_user.last_active = datetime.utcnow()
            except Exception:
                pass

    @app.after_request
    def record_traffic(response):
        if request.path.startswith('/static') or request.path.startswith('/socket.io'):
            return response

        try:
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if client_ip and ',' in client_ip:
                client_ip = client_ip.split(',')[0].strip()

            ua = request.user_agent
            dev = 'mobile' if ua.platform in ['android', 'iphone'] else 'desktop'

            traffic = VisitorTraffic(
                session_id=session.get('visitor_uuid', 'anon'),
                user_id=current_user.id if current_user.is_authenticated else None,
                ip_address=client_ip,
                path=request.path[:254],
                method=request.method,
                referrer=request.referrer[:254] if request.referrer else None,
                browser=ua.browser[:60] if ua.browser else "Other",
                os=ua.platform[:60] if ua.platform else "Other",
                device_type=dev,
                status_code=response.status_code
            )
            db.session.add(traffic)
            db.session.commit()
        except Exception:
            db.session.rollback()

        return response

    @app.context_processor
    def inject_platform_globals():
        """Injects dynamic navigation, announcements, and feature flags into templates."""
        try:
            active_announcement = Announcement.query.filter_by(is_active=True).order_by(Announcement.id.desc()).first()
        except Exception:
            active_announcement = None

        try:
            nav_items = SiteNavigationItem.query.filter_by(is_visible=True).order_by(SiteNavigationItem.nav_order.asc()).all()
        except Exception:
            nav_items = []

        return {
            'is_feature_enabled': is_feature_enabled,
            'is_maintenance_mode': is_maintenance_active(),
            'platform_announcement': active_announcement,
            'dynamic_nav_items': nav_items
        }


# ==============================================================
# AUTHORITATIVE SERVER-SIDE PERMISSION DECORATOR
# ==============================================================

def admin_permission_required(permission: str):
    """
    Authoritative server-side decorator checking granular permissions.
    The Super Admin inherently bypasses all restrictions.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                log_security_incident('UNAUTHENTICATED_ADMIN_ACCESS', 'HIGH', f"Anonymous access attempted at {request.path}")
                flash("Authentication required to access the TypeSphere Control Center.", "warning")
                return redirect(url_for('auth.login', next=request.url))

            if not current_user.is_admin:
                log_security_incident(
                    'UNAUTHORIZED_ADMIN_ATTEMPT',
                    'CRITICAL',
                    f"User @{current_user.username} tried accessing {request.path}",
                    identifier=current_user.username
                )
                flash("Access denied: You lack administrative clearance.", "danger")
                return redirect(url_for('typing.test_page'))

            if not current_user.has_permission(permission):
                log_admin_action('PERMISSION_DENIED', 'security', details=f"Attempted '{permission}' on {request.path}")
                flash(f"Insufficient privileges: Missing required permission [{permission}].", "danger")
                return redirect(url_for('admin.dashboard'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def ensure_permissions_seeded():
    """Seeds the canonical system permissions registry in the database."""
    try:
        existing_codes = {p.code for p in Permission.query.all()}
        added = False
        for code, name, category, desc in SYSTEM_PERMISSIONS:
            if code not in existing_codes:
                db.session.add(Permission(
                    code=code,
                    name=name,
                    category=category,
                    description=desc
                ))
                added = True
        if added:
            db.session.commit()
    except Exception:
        db.session.rollback()


def ensure_navigation_seeded():
    """Seeds the canonical default navigation items in the database if empty."""
    try:
        if SiteNavigationItem.query.count() == 0:
            default_links = [
                ('⚡ Benchmark', '/typing/test', 1, True, True, None),
                ('🎓 Flight School', '/learn/', 2, True, True, 'var(--accent)'),
                ('🕹️ Arcade', '/games/', 3, True, True, 'var(--warning)'),
                ('🎯 AI Coach', '/typing/practice', 4, True, True, None),
                ('🔥 Missions', '/challenges/', 5, True, True, None),
                ('🏆 Standings', '/leaderboard/', 6, True, True, None),
                ('🏎️ 1v1 Grid', '/multiplayer/', 7, True, True, None),
                ('📖 Manual', '/typing/help', 8, True, True, None),
                ('⚙️ Cockpit', '/settings/', 9, True, True, None)
            ]
            for label, url, order, for_g, for_p, color in default_links:
                db.session.add(SiteNavigationItem(
                    label=label,
                    url=url,
                    nav_order=order,
                    is_visible=True,
                    for_guests=for_g,
                    for_pilots=for_p,
                    highlight_color=color
                ))
            db.session.commit()
    except Exception:
        db.session.rollback()