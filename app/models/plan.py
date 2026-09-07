from datetime import datetime
from app import db

class UserSubscription(db.Model):
    """
    Extensible access control layer. All users initially default to 'free' with full capability.
    """
    __tablename__ = 'user_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    tier = db.Column(db.String(32), default='free', nullable=False) # 'free', 'pro', 'enterprise'
    is_active = db.Column(db.Boolean, default=True)
    
    # Feature Toggles (All unlocked initially)
    ai_coach_unlimited = db.Column(db.Boolean, default=True)
    unlimited_multiplayer = db.Column(db.Boolean, default=True)
    official_certification = db.Column(db.Boolean, default=True)
    custom_themes_access = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('subscription', uselist=False))