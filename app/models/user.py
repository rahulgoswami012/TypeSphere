"""
TypeSphere - Pilot & User Entity Model
Maintains authentication, Callsigns, Elo ratings, biometric profiles,
multi-role custom authorizations, and Super Admin protection.
"""

from datetime import datetime
import re
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db
from app.models.admin import user_roles, CustomRole


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)

    # Pilot Identity & Callsign
    callsign = db.Column(db.String(32), unique=True, nullable=True, index=True)
    flight_squadron = db.Column(db.String(64), default='Vanguard Flight Division')
    avatar_flight_badge = db.Column(db.String(32), default='apex_wings')

    # Authority & Account Classification
    role = db.Column(db.String(32), default='user', nullable=False, index=True)
    is_verified = db.Column(db.Boolean, default=True, nullable=True)

    # Moderation States
    is_suspended = db.Column(db.Boolean, default=False, index=True)
    is_banned = db.Column(db.Boolean, default=False, index=True)
    status_reason = db.Column(db.String(255), nullable=True)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)

    # Competitive Ranked MMR Telemetry
    elo_rating = db.Column(db.Integer, default=1000, nullable=False, index=True)
    ranked_wins = db.Column(db.Integer, default=0, nullable=False)
    ranked_losses = db.Column(db.Integer, default=0, nullable=False)
    ranked_draws = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    tests = db.relationship('TypingTest', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    dna_profile = db.relationship('TypingDNA', uselist=False, backref='user', cascade="all, delete-orphan")
    user_settings = db.relationship('UserSettings', uselist=False, backref='user', cascade="all, delete-orphan")
    achievements = db.relationship('UserAchievement', backref='user', lazy='dynamic', cascade="all, delete-orphan")

    # Multi-Role Dynamic Association
    custom_roles = db.relationship(
        'CustomRole',
        secondary=user_roles,
        back_populates='users',
        lazy='joined'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def display_callsign(self) -> str:
        if self.callsign and self.callsign.strip():
            return self.callsign.strip().upper()
        clean = re.sub(r'[^A-Za-z0-9]', '', self.username)
        return (clean[:10] if clean else "PILOT").upper()

    @property
    def is_super_admin(self) -> bool:
        """
        True if the user holds Super Admin authority.
        Encompasses 'super_admin', legacy primary 'admin', or username 'admin'.
        """
        return self.role in ['super_admin', 'admin'] or self.username.lower() == 'admin'

    @property
    def is_admin(self) -> bool:
        """
        True if the user is a Super Admin, holds an administrative role,
        or has at least one active custom delegated role.
        """
        if self.is_super_admin:
            return True
        if self.role in ['moderator', 'content_manager', 'analyst']:
            return True
        return any(r.is_active for r in self.custom_roles)

    @property
    def is_active_account(self) -> bool:
        return not self.is_banned and not self.is_suspended

    @property
    def effective_permissions(self) -> set:
        """
        Calculates the complete union of active permissions across all assigned roles.
        Super Administrators inherently possess universal clearance '*'.
        """
        if self.is_super_admin:
            return {'*'}

        perms = set()
        for role in self.custom_roles:
            if role.is_active:
                for p in role.permissions:
                    perms.add(p.code)

        # Legacy role compatibility mapping
        legacy_role_map = {
            'moderator': {'users.view', 'users.profile', 'users.moderate', 'reviews.view', 'reviews.moderate', 'security.audit_logs'},
            'content_manager': {'typing.*', 'challenges.manage', 'academy.manage', 'reviews.view'},
            'analyst': {'analytics.*'}
        }
        if self.role in legacy_role_map:
            perms.update(legacy_role_map[self.role])

        return perms

    def has_permission(self, permission_code: str) -> bool:
        """
        Authoritative server-side evaluation.
        The Super Admin possesses unrestricted clearance.
        """
        if self.is_super_admin:
            return True

        if self.is_banned or self.is_suspended:
            return False

        effective = self.effective_permissions
        if '*' in effective:
            return True

        if permission_code in effective:
            return True

        category_wildcard = permission_code.split('.')[0] + '.*' if '.' in permission_code else None
        if category_wildcard and category_wildcard in effective:
            return True

        return False

    @property
    def rank_division(self) -> str:
        elo = self.elo_rating or 1000
        if elo >= 1900: return "Grandmaster"
        if elo >= 1700: return "Diamond"
        if elo >= 1500: return "Platinum"
        if elo >= 1300: return "Gold"
        if elo >= 1100: return "Silver"
        return "Bronze"

    @property
    def rank_badge(self) -> dict:
        division = self.rank_division
        badges = {
            "Grandmaster": {"icon": "👑", "color": "#ec4899", "bg": "rgba(236,72,153,0.15)"},
            "Diamond": {"icon": "💎", "color": "#38bdf8", "bg": "rgba(56,189,248,0.15)"},
            "Platinum": {"icon": "⚡", "color": "#10b981", "bg": "rgba(16,185,129,0.15)"},
            "Gold": {"icon": "🏆", "color": "#f59e0b", "bg": "rgba(245,158,11,0.15)"},
            "Silver": {"icon": "🥈", "color": "#94a3b8", "bg": "rgba(148,163,184,0.15)"},
            "Bronze": {"icon": "🥉", "color": "#d97706", "bg": "rgba(217,119,6,0.15)"}
        }
        return badges.get(division, {"icon": "🥉", "color": "#d97706", "bg": "rgba(217,119,6,0.15)"})

    def update_competitive_elo(self, opponent_elo: int, match_outcome: str, k_factor: int = 32) -> int:
        current_elo = self.elo_rating or 1000
        score_map = {'WIN': 1.0, 'DRAW': 0.5, 'LOSS': 0.0}
        actual_score = score_map.get(match_outcome, 0.0)

        expected_score = 1.0 / (1.0 + (10.0 ** ((opponent_elo - current_elo) / 400.0)))
        delta = int(round(k_factor * (actual_score - expected_score)))

        self.elo_rating = max(100, current_elo + delta)
        if match_outcome == 'WIN':
            self.ranked_wins = (self.ranked_wins or 0) + 1
        elif match_outcome == 'LOSS':
            self.ranked_losses = (self.ranked_losses or 0) + 1
        else:
            self.ranked_draws = (self.ranked_draws or 0) + 1

        return delta