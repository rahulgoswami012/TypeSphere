"""
TypeSphere - Administrative Models & Dynamic RBAC Schema
Defines Custom Roles, Granular Permissions, Active IP Controls, Feature Flags,
Navigation CMS, and Audit Logs.
"""

from datetime import datetime, timedelta
from app import db

# Association Table: CustomRole <-> Permission (Many-to-Many)
role_permissions = db.Table(
    'role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('custom_roles.id', ondelete='CASCADE'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)
)

# Association Table: User <-> CustomRole (Many-to-Many)
user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('custom_roles.id', ondelete='CASCADE'), primary_key=True),
    db.Column('assigned_at', db.DateTime, default=datetime.utcnow),
    db.Column('assigned_by', db.String(64), default='SuperAdmin')
)


class Permission(db.Model):
    """
    Granular permission entity representing an atomic action in TypeSphere.
    """
    __tablename__ = 'permissions'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    category = db.Column(db.String(64), nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'category': self.category,
            'description': self.description
        }


class CustomRole(db.Model):
    """
    Super Admin-defined custom role grouping multiple granular permissions.
    """
    __tablename__ = 'custom_roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(64), default='SuperAdmin')
    updated_by = db.Column(db.String(64), nullable=True)

    permissions = db.relationship(
        'Permission',
        secondary=role_permissions,
        lazy='joined',
        backref=db.backref('roles', lazy='dynamic')
    )

    users = db.relationship(
        'User',
        secondary=user_roles,
        back_populates='custom_roles',
        lazy='dynamic'
    )

    def has_permission(self, perm_code: str) -> bool:
        if not self.is_active:
            return False
        return any(p.code == perm_code or p.code == '*' for p in self.permissions)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'is_system': self.is_system,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'user_count': self.users.count(),
            'permission_codes': [p.code for p in self.permissions]
        }


class BlockedIP(db.Model):
    """
    Active operational IP blocking ledger enforced in request middleware.
    """
    __tablename__ = 'blocked_ips'

    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), unique=True, nullable=False, index=True)
    reason = db.Column(db.String(255), default='Suspicious automated traffic or rate violation')
    is_permanent = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)
    blocked_by = db.Column(db.String(64), default='System')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    @property
    def is_currently_blocked(self) -> bool:
        if self.is_permanent:
            return True
        if self.expires_at and self.expires_at > datetime.utcnow():
            return True
        return False


class FeatureFlag(db.Model):
    """
    Runtime feature flag configuration driving website toggles without code deploys.
    """
    __tablename__ = 'feature_flags'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    label = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    is_enabled = db.Column(db.Boolean, default=False, index=True)
    environment = db.Column(db.String(32), default='all')
    updated_by = db.Column(db.String(64), default='SuperAdmin')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SiteNavigationItem(db.Model):
    """
    Database-backed public navigation item configured from the Control Center.
    """
    __tablename__ = 'site_navigation_items'

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64), nullable=False)
    url = db.Column(db.String(128), nullable=False)
    icon = db.Column(db.String(16), default='⚡')
    nav_order = db.Column(db.Integer, default=1, index=True)
    is_visible = db.Column(db.Boolean, default=True, index=True)
    for_guests = db.Column(db.Boolean, default=True)
    for_pilots = db.Column(db.Boolean, default=True)
    highlight_color = db.Column(db.String(32), nullable=True) # e.g. 'var(--accent)', 'var(--warning)'


# ==============================================================
# CANONICAL SYSTEM PERMISSIONS REGISTRY (10 OPERATIONAL SECTORS)
# ==============================================================

SYSTEM_PERMISSIONS = [
    # 1. User Management
    ('users.view', 'View User Directory', 'User Management', 'View user accounts, registration dates, and search directory'),
    ('users.profile', 'View Detailed User Profiles', 'User Management', 'Inspect user telemetry, stats, and personal dossiers'),
    ('users.activity', 'View User Activity Stream', 'User Management', 'Inspect action logs and user event history'),
    ('users.network_view', 'View User Network & IP Details', 'User Management', 'Inspect IP, ISP, ASN, and estimated network location'),
    ('users.edit', 'Edit Permitted User Details', 'User Management', 'Update username, callsign, and account metadata'),
    ('users.moderate', 'Moderate User Accounts', 'User Management', 'Suspend or lift suspension on accounts'),
    ('users.ban', 'Permanent Account Ban', 'User Management', 'Permanently ban or unban accounts from platform access'),
    ('users.delete', 'Delete User Accounts', 'User Management', 'Permanently erase a user account and associated tests'),
    ('users.export', 'Export User Information', 'User Management', 'Download CSV data exports of user directory records'),
    ('users.impersonate', 'Impersonate User', 'User Management', 'Simulate account experience for troubleshooting'),

    # 2. Roles & Delegated Permissions
    ('roles.view', 'View Roles & Permissions', 'Administration', 'Inspect delegated roles and active permission mappings'),
    ('roles.manage', 'Create & Edit Custom Roles', 'Administration', 'Create custom roles, edit permissions, and assign to users'),
    ('roles.delete', 'Delete Custom Roles', 'Administration', 'Remove custom roles and reassign affected users'),

    # 3. Typing Content CMS
    ('typing.view', 'View Passage Library', 'Typing Content', 'Browse database passages and content prompts'),
    ('typing.create', 'Create Typing Passages', 'Typing Content', 'Formulate and add new typing passages'),
    ('typing.edit', 'Edit Typing Passages', 'Typing Content', 'Update text, categories, difficulty tiers, and language tags'),
    ('typing.delete', 'Delete Typing Passages', 'Typing Content', 'Remove passages from active flight bank'),
    ('typing.publish', 'Toggle Passage Status', 'Typing Content', 'Enable or disable passages from test rotation'),

    # 4. Games & Arcade Hangar
    ('games.view', 'View Arcade Disciplines', 'Arcade Hangar', 'Inspect arcade game configurations and high scores'),
    ('games.edit', 'Edit Game Configurations', 'Arcade Hangar', 'Update titles, descriptions, and duration presets'),
    ('games.toggle', 'Enable / Disable Games', 'Arcade Hangar', 'Toggle game disciplines in and out of the active hangar'),
    ('games.leaderboards', 'Moderate Game Scores', 'Arcade Hangar', 'Inspect and moderate arcade high scores and records'),

    # 5. Tactical Challenges & Daily Recon
    ('challenges.view', 'View Mission Operations', 'Missions & Challenges', 'Inspect tactical disciplines and daily challenge logs'),
    ('challenges.manage', 'Manage Daily Challenge', 'Missions & Challenges', 'Publish, calibrate, or schedule daily briefings'),
    ('challenges.moderate', 'Moderate Mission Leaderboards', 'Missions & Challenges', 'Audit and moderate daily challenge leaderboards'),

    # 6. Academy Curriculum
    ('academy.view', 'View Academy Tracks', 'Flight School', 'Inspect curriculum stages, focus keys, and practice materials'),
    ('academy.manage', 'Edit Curriculum Stages', 'Flight School', 'Update stage content, WPM thresholds, and attempt requirements'),

    # 7. Certificates & Verification
    ('certificates.view', 'View Issued Certificates', 'Certification', 'Inspect official flight wings and certificates'),
    ('certificates.revoke', 'Revoke Certificates', 'Certification', 'Revoke falsified or non-compliant certificates'),
    ('certificates.manage', 'Manage Standards & Templates', 'Certification', 'Update qualification thresholds and certification tiers'),

    # 8. Community, Reviews & Feedback
    ('reviews.view', 'View Community Reviews', 'Community & Feedback', 'Inspect pilot reviews, ratings, and inquiries'),
    ('reviews.moderate', 'Moderate Community Reviews', 'Community & Feedback', 'Approve, hide, or restore reviews and ratings'),
    ('feedback.manage', 'Manage Feedback & Inquiries', 'Community & Feedback', 'Review contact messages and reply to suggestions'),
    ('announcements.manage', 'Publish Platform Announcements', 'Community & Feedback', 'Create and broadcast system banners'),

    # 9. Analytics & Traffic Telemetry
    ('analytics.dashboard', 'View Command Center Analytics', 'Analytics', 'Access executive metrics, growth rates, and top-level KPIs'),
    ('analytics.traffic', 'View Traffic & Pageview Analytics', 'Analytics', 'Inspect session volumes, endpoints, and referrers'),
    ('analytics.devices', 'View Device & Browser Breakdown', 'Analytics', 'Inspect desktop/mobile/tablet platforms and browser mix'),
    ('analytics.geographic', 'View Approximate Geography', 'Analytics', 'Inspect regional visitor distribution from network logs'),

    # 10. Security, Audit & Website Control
    ('security.events_view', 'View Security Events Log', 'Security & Audit', 'Audit failed logins, rate limit violations, and security faults'),
    ('security.ip_manage', 'Manage Blocked IP Addresses', 'Security & Audit', 'Add or remove temporary and permanent IP blocks'),
    ('security.audit_logs', 'View Action Audit Trail', 'Security & Audit', 'Inspect uneditable historical ledger of admin actions'),
    ('website.settings', 'Manage System Parameters', 'Website Control', 'Configure maintenance mode, registration locks, and thresholds'),
    ('website.flags', 'Manage Feature Flags', 'Website Control', 'Toggle experimental systems and feature availability'),
    ('website.health', 'View System Health & Diagnostics', 'Website Control', 'Monitor database connection status, storage, and response times'),
    ('website.exports', 'Perform System Data Exports', 'Website Control', 'Generate official data exports of platform tables')
]


class RolePermission:
    """Unified authorization resolver maintaining legacy fallback compatibility."""
    SUPER_ADMIN = 'super_admin'

    @classmethod
    def has_permission(cls, role, permission):
        if role == cls.SUPER_ADMIN:
            return True
        return False


class AdminAuditLog(db.Model):
    __tablename__ = 'admin_audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    admin_username = db.Column(db.String(64), nullable=False)
    action = db.Column(db.String(128), nullable=False, index=True)
    target_type = db.Column(db.String(64), nullable=False, index=True)
    target_id = db.Column(db.String(64), nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    admin = db.relationship('User', foreign_keys=[admin_id])


class UserActivity(db.Model):
    __tablename__ = 'user_activities'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    action = db.Column(db.String(64), nullable=False, index=True)
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
    device_type = db.Column(db.String(32), default='desktop')
    status_code = db.Column(db.Integer, default=200)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class SecurityEvent(db.Model):
    __tablename__ = 'security_events'

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    severity = db.Column(db.String(20), default='LOW', index=True)
    identifier = db.Column(db.String(128), nullable=True)
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