from datetime import datetime
from app import db

class ArcadeContentItem(db.Model):
    __tablename__ = 'arcade_content_items'

    id = db.Column(db.Integer, primary_key=True)
    game_mode = db.Column(db.String(50), nullable=False, index=True)
    difficulty = db.Column(db.String(20), default='moderate', index=True) # easy, moderate, hard, expert
    target_text = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), default='general', index=True)
    associated_keys = db.Column(db.String(64), nullable=True)
    word_length = db.Column(db.Integer, default=5)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ArcadeGameConfig(db.Model):
    __tablename__ = 'arcade_game_configs'

    id = db.Column(db.Integer, primary_key=True)
    game_slug = db.Column(db.String(50), unique=True, nullable=False)
    display_title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    allows_solo_ai = db.Column(db.Boolean, default=True)
    allows_1v1 = db.Column(db.Boolean, default=True)
    allows_multiplayer = db.Column(db.Boolean, default=False)
    max_multiplayer_players = db.Column(db.Integer, default=2)
    durations = db.Column(db.String(50), default="60")
    default_ai_level = db.Column(db.String(20), default="moderate")
    is_enabled = db.Column(db.Boolean, default=True)