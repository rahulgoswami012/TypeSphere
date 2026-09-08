import uuid
from functools import wraps
from datetime import datetime
from flask import request, abort, redirect, url_for, flash, session, g
from flask_login import current_user
from app import db
from app.models.admin import RolePermission, AdminAuditLog, VisitorTraffic, SecurityEvent, UserActivity

def log_admin_action(action, target_type, target_id=None, details=None):
    """Securely write an uneditable audit entry."""
    try:
        log = AdminAuditLog(
            admin_id=current_user.id if current_user.is_authenticated else None,
            admin_username=current_user.username if current_user.is_authenticated else "System",
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            details=str(details) if details else None,
            ip_address=request.headers.get('X-Forwarded-For', request.remote_addr)
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()

def log_security_incident(event_type, severity, description, identifier=None):
    """Store critical auth faults and anomalous requests."""
    try:
        ev = SecurityEvent(
            event_type=event_type,
            severity=severity,
            identifier=identifier,
            ip_address=request.headers.get('X-Forwarded-For', request.remote_addr),
            user_agent=request.user_agent.string[:250] if request.user_agent else "Unknown",
            description=description
        )
        db.session.add(ev)
        db.session.commit()
    except Exception:
        db.session.rollback()

def record_user_activity(user_id, action, feature="Platform", details=None):
    """Log individual user interaction."""
    try:
        act = UserActivity(
            user_id=user_id,
            action=action,
            feature=feature,
            details=details,
            ip_address=request.headers.get('X-Forwarded-For', request.remote_addr),
            user_agent=request.user_agent.string[:250] if request.user_agent else "Unknown"
        )
        db.session.add(act)
        db.session.commit()
    except Exception:
        db.session.rollback()

def capture_traffic(app):
    """Before/after request hooks for anonymous & user analytics."""
    @app.before_request
    def track_request():
        if 'visitor_uuid' not in session:
            session['visitor_uuid'] = str(uuid.uuid4())

        # Update last_active for logged-in accounts
        if current_user.is_authenticated:
            current_user.last_active = datetime.utcnow()

    @app.after_request
    def record_traffic(response):
        # Ignore static assets to preserve high I/O throughput
        if request.path.startswith('/static') or request.path.startswith('/socket.io'):
            return response

        try:
            ua = request.user_agent
            dev = 'mobile' if ua.platform in ['android', 'iphone'] else 'desktop'
            
            traffic = VisitorTraffic(
                session_id=session.get('visitor_uuid', 'anon'),
                user_id=current_user.id if current_user.is_authenticated else None,
                ip_address=request.headers.get('X-Forwarded-For', request.remote_addr),
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

def admin_permission_required(permission):
    """Strict decorator checking administrative capabilities."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                log_security_incident('UNAUTHENTICATED_ADMIN_ACCESS', 'HIGH', f"Anonymous access attempted at {request.path}")
                flash("Authentication required to enter admin control systems.", "warning")
                return redirect(url_for('auth.login', next=request.url))
            
            if not current_user.is_admin:
                log_security_incident('UNAUTHORIZED_ADMIN_ATTEMPT', 'CRITICAL', f"User @{current_user.username} tried accessing {request.path}", identifier=current_user.username)
                flash("Access denied: You lack administrative authority.", "danger")
                return redirect(url_for('typing.test_page'))

            if not RolePermission.has_permission(current_user.role, permission):
                log_admin_action('PERMISSION_DENIED', 'route', details=f"Attempted {permission} on {request.path}")
                flash(f"Insufficient privileges: Role '{current_user.role.upper()}' cannot execute this action.", "danger")
                return redirect(url_for('admin.dashboard'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator