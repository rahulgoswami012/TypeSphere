from datetime import datetime
from app import db

class RolePermission:
    """Explicit permission mappings for RBAC."""
    SUPER_ADMIN = 'super_admin'
    ADMIN = 'admin'
    MODERATOR = 'moderator'
    CONTENT_MANAGER = 'content_manager'
    ANALYST = 'analyst'

    ALL_ROLES = [SUPER_ADMIN, ADMIN, MODERATOR, CONTENT_MANAGER, ANALYST]

    HIERARCHY = {
        SUPER_ADMIN: ['*'],
        ADMIN: [
            'view_dashboard', 'manage_users', 'manage_content', 'manage_games', 
            'manage_leaderboard', 'manage_challenges', 'manage_feedback', 
            'manage_learning', 'view_analytics', 'view_security', 'view_audit_logs',
            'export_data', 'manage_settings'
        ],
        MODERATOR: [
            'view_dashboard', 'manage_users_basic', 'manage_leaderboard', 
            'manage_feedback', 'view_audit_logs'
        ],
        CONTENT_MANAGER: [
            'view_dashboard', 'manage_content', 'manage_challenges', 'manage_learning'
        ],
        ANALYST: [
            'view_dashboard', 'view_analytics', 'view_traffic', 'export_data'
        ]
    }

    @classmethod
    def has_permission(cls, role, permission):
        if role == cls.SUPER_ADMIN:
            return True
        allowed = cls.HIERARCHY.get(role, [])
        return permission in allowed or '*' in allowed

class AdminAuditLog(db.Model):
    __tablename__ = 'admin_audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    admin_username = db.Column(db.String(64), nullable=False)
    action = db.Column(db.String(128), nullable=False, index=True) # e.g. "USER_SUSPEND", "PASSAGE_DELETE"
    target_type = db.Column(db.String(64), nullable=False, index=True) # "user", "passage", "setting", etc.
    target_id = db.Column(db.String(64), nullable=True)
    details = db.Column(db.Text, nullable=True) # JSON or descriptive string of changes
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    admin = db.relationship('User', foreign_keys=[admin_id])

class UserActivity(db.Model):
    __tablename__ = 'user_activities'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    action = db.Column(db.String(64), nullable=False, index=True) # 'LOGIN', 'TEST_COMPLETE', etc.
    feature = db.Column(db.String(64), default='Platform')
    details = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref=db.backref('activities', lazy='dynamic', cascade='all, delete-orphan'))

class VisitorTraffic(db.Model):
    __tablename__ = 'visitor_traffic'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    ip_address = db.Column(db.String(45), nullable=True)
    path = db.Column(db.String(255), nullable=False, index=True)
    method = db.Column(db.String(10), default='GET')
    referrer = db.Column(db.String(255), nullable=True)
    browser = db.Column(db.String(64), nullable=True)
    os = db.Column(db.String(64), nullable=True)
    device_type = db.Column(db.String(32), default='desktop') # 'desktop', 'mobile', 'tablet'
    status_code = db.Column(db.Integer, default=200)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class SecurityEvent(db.Model):
    __tablename__ = 'security_events'

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(64), nullable=False, index=True) # 'FAILED_LOGIN', 'ABUSE_FLAG', 'IP_BLOCK'
    severity = db.Column(db.String(20), default='LOW', index=True) # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    identifier = db.Column(db.String(128), nullable=True) # email or username or token
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class PlatformConfig(db.Model):
    __tablename__ = 'platform_configs'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(32), default='general', index=True)
    description = db.Column(db.String(255), nullable=True)
    updated_by = db.Column(db.String(64), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)