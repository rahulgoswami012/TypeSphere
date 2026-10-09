"""
TypeSphere - Administrative Security, Audit & Request Telemetry Engine
Enforces server-side authorization checks, active IP interception with operator
safeguards, accurate Windows 11 / Android OS version extraction, and cached geolocation.
"""

import uuid
import re
import urllib.request
import json
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

IP_GEO_CACHE = {}


def detect_device_category(user_agent_str: str) -> str:
    """Robust device classification (mobile, tablet, desktop) from raw User-Agent."""
    ua = (user_agent_str or "").lower()
    if 'ipad' in ua or 'tablet' in ua:
        return 'tablet'
    if 'mobile' in ua or 'android' in ua or 'iphone' in ua or 'ipod' in ua:
        return 'mobile'
    return 'desktop'


def parse_device_os(user_agent_str: str) -> str:
    """Extracts exact operating system and Android/iOS/Windows 11 versions."""
    ua = user_agent_str or ""

    ch_platform = request.headers.get('Sec-CH-UA-Platform', '').replace('"', '').strip()
    ch_version = request.headers.get('Sec-CH-UA-Platform-Version', '').replace('"', '').strip()

    if ch_platform == 'Windows' and ch_version:
        try:
            major = int(ch_version.split('.')[0])
            if major >= 13:
                return "Windows 11"
            return "Windows 10"
        except Exception:
            pass

    if "Android" in ua:
        match = re.search(r'Android\s+([0-9\.]+)', ua)
        return f"Android {match.group(1)}" if match else "Android"

    if "iPhone" in ua or "iPad" in ua:
        match = re.search(r'OS\s+([0-9_]+)', ua)
        ver = match.group(1).replace('_', '.') if match else ""
        return f"iOS {ver}" if ver else "iOS"

    if "Windows NT 10.0" in ua:
        return "Windows 11 / 10"
    if "Windows NT 6.3" in ua:
        return "Windows 8.1"
    if "Windows NT 6.1" in ua:
        return "Windows 7"

    if "Mac OS X" in ua:
        match = re.search(r'Mac OS X\s+([0-9_]+)', ua)
        ver = match.group(1).replace('_', '.') if match else ""
        return f"macOS {ver}" if ver else "macOS"
    if "Linux" in ua:
        return "Linux"

    return "Standard OS"


def get_ip_location(ip: str) -> str:
    """Resolves City, State/Region, and Country from client IP with in-memory caching."""
    if not ip or ip in ['127.0.0.1', '::1', 'localhost']:
        if 'local_dev_city' in IP_GEO_CACHE:
            return IP_GEO_CACHE['local_dev_city']
        try:
            req = urllib.request.Request("http://ip-api.com/json/?fields=status,city,regionName,country", headers={'User-Agent': 'TypeSphere-Dev/2.0'})
            with urllib.request.urlopen(req, timeout=1.0) as res:
                d = json.loads(res.read().decode('utf-8'))
                if d.get('status') == 'success':
                    city = d.get('city') or ""
                    reg = d.get('regionName') or ""
                    cnt = d.get('country') or ""
                    parts = [p for p in [city, reg, cnt] if p]
                    loc_str = ", ".join(parts) if parts else "India"
                    IP_GEO_CACHE['local_dev_city'] = loc_str
                    return loc_str
        except Exception:
            pass
        return "Local Network (India)"

    clean_ip = ip.split(',')[0].strip()
    if clean_ip in IP_GEO_CACHE:
        return IP_GEO_CACHE[clean_ip]

    try:
        req_url = f"http://ip-api.com/json/{clean_ip}?fields=status,city,regionName,country"
        req = urllib.request.Request(req_url, headers={'User-Agent': 'TypeSphere-Telemetry/2.0'})
        with urllib.request.urlopen(req, timeout=1.2) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('status') == 'success':
                city = data.get('city') or ""
                region = data.get('regionName') or ""
                country = data.get('country') or ""
                parts = [p for p in [city, region, country] if p]
                loc_str = ", ".join(parts) if parts else "India"
                IP_GEO_CACHE[clean_ip] = loc_str
                return loc_str
    except Exception:
        pass

    fallback = "India"
    IP_GEO_CACHE[clean_ip] = fallback
    return fallback


def log_admin_action(action: str, target_type: str, target_id=None, details=None):
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


def is_ip_blocked(ip: str) -> bool:
    """
    Safely checks if an IP is blocked.
    Loopback addresses, private networks, and invalid addresses are always exempted.
    """
    if not ip:
        return False

    clean_ip = ip.split(',')[0].strip()

    # Exempt loopback & localhost
    if clean_ip in ['127.0.0.1', '::1', 'localhost', '', 'None']:
        return False

    # Exempt private network subnets
    if clean_ip.startswith(('10.', '192.168.', '172.16.', '172.17.', '172.18.', '172.19.',
                            '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.',
                            '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.')):
        return False

    try:
        blocked = BlockedIP.query.filter_by(ip_address=clean_ip).first()
        return bool(blocked and blocked.is_currently_blocked)
    except Exception:
        db.session.rollback()
        return False


def block_ip(ip: str, reason: str, is_permanent: bool = False, duration_hours: int = 24, blocked_by: str = 'SuperAdmin') -> bool:
    clean_ip = ip.split(',')[0].strip()
    if clean_ip in ['127.0.0.1', '::1', 'localhost', '']:
        return False

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
    clean_ip = ip.split(',')[0].strip()
    existing = BlockedIP.query.filter_by(ip_address=clean_ip).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        log_admin_action('IP_UNBLOCKED', 'security', details=f"Unblocked {clean_ip} by {unblocked_by}")
        return True
    return False


def is_feature_enabled(flag_key: str, default: bool = False) -> bool:
    try:
        flag = FeatureFlag.query.filter_by(key=flag_key).first()
        if flag:
            return flag.is_enabled
    except Exception:
        pass
    return default


def is_maintenance_active() -> bool:
    try:
        cfg = PlatformConfig.query.filter_by(key='maintenance_mode').first()
        return bool(cfg and cfg.value.lower() == 'true')
    except Exception:
        return False


def capture_traffic(app):
    @app.before_request
    def intercept_and_track():
        # 1. Immediate exemption for static assets and WebSocket handshakes
        if request.path.startswith(('/static', '/socket.io', '/favicon.ico')):
            return

        # 2. Immediate exemption for authentication (prevents operator lockout)
        if request.path.startswith('/auth'):
            return

        # 3. Immediate exemption for authenticated administrators
        if current_user.is_authenticated and current_user.is_admin:
            return

        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()

        # Enforce IP restriction with safety boundaries
        if is_ip_blocked(client_ip):
            log_security_incident('BLOCKED_IP_CONNECTION_ATTEMPT', 'MEDIUM', f"Blocked IP {client_ip} tried accessing {request.path}", identifier=client_ip)
            abort(403)

        # Maintenance mode check
        if is_maintenance_active():
            is_admin_user = current_user.is_authenticated and current_user.is_admin
            exempt_prefixes = ['/static', '/auth', '/admin', '/socket.io']
            is_exempt_path = any(request.path.startswith(prefix) for prefix in exempt_prefixes)

            if not is_admin_user and not is_exempt_path:
                cfg_msg = PlatformConfig.query.filter_by(key='maintenance_message').first()
                msg = cfg_msg.value if cfg_msg else "Flight control systems are undergoing scheduled calibration. Normal flights will resume shortly."
                return render_template('errors/maintenance.html', message=msg), 503

        if 'visitor_uuid' not in session:
            session['visitor_uuid'] = str(uuid.uuid4())

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

            ua_str = request.headers.get('User-Agent', '')
            dev = detect_device_category(ua_str)
            os_detected = parse_device_os(ua_str)

            ua = request.user_agent
            browser_name = ua.browser[:60] if ua and ua.browser else "Browser"

            traffic = VisitorTraffic(
                session_id=session.get('visitor_uuid', 'anon'),
                user_id=current_user.id if current_user.is_authenticated else None,
                ip_address=client_ip,
                path=request.path[:254],
                method=request.method,
                referrer=request.referrer[:254] if request.referrer else None,
                browser=browser_name,
                os=os_detected,
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


def admin_permission_required(permission: str):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Authentication required to access the TypeSphere Control Center.", "warning")
                return redirect(url_for('auth.login', next=request.url))

            if not current_user.is_admin:
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