from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user') # 'user' or 'admin'
    is_verified = db.Column(db.Boolean, default=True, nullable=True)
    
    # Version 2.0 Ranked Competitive System
    elo_rating = db.Column(db.Integer, default=1000, nullable=False, index=True)
    ranked_wins = db.Column(db.Integer, default=0, nullable=False)
    ranked_losses = db.Column(db.Integer, default=0, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    tests = db.relationship('TypingTest', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    dna_profile = db.relationship('TypingDNA', uselist=False, backref='user', cascade="all, delete-orphan")
    user_settings = db.relationship('UserSettings', uselist=False, backref='user', cascade="all, delete-orphan")
    achievements = db.relationship('UserAchievement', backref='user', lazy='dynamic', cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def rank_division(self):
        elo = self.elo_rating or 1000
        if elo >= 1900:
            return "Grandmaster"
        elif elo >= 1700:
            return "Diamond"
        elif elo >= 1500:
            return "Platinum"
        elif elo >= 1300:
            return "Gold"
        elif elo >= 1100:
            return "Silver"
        return "Bronze"

    @property
    def rank_badge(self):
        division = self.rank_division
        badges = {
            "Grandmaster": {"icon": "👑", "color": "#ff007f"},
            "Diamond": {"icon": "💎", "color": "#58a6ff"},
            "Platinum": {"icon": "⚡", "color": "#3fb950"},
            "Gold": {"icon": "🏆", "color": "#f59e0b"},
            "Silver": {"icon": "🥈", "color": "#94a3b8"},
            "Bronze": {"icon": "🥉", "color": "#b45309"}
        }
        return badges.get(division, {"icon": "🥉", "color": "#b45309"})