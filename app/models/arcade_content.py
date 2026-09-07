from datetime import datetime
from app import db

class ArcadeContentItem(db.Model):
    __tablename__ = 'arcade_content_items'

    id = db.Column(db.Integer, primary_key=True)
    game_mode = db.Column(db.String(50), nullable=False, index=True) 
    # 'falling_words', 'speed_racer', 'bubble_pop', 'whack_a_word', 'zombie_duel', 
    # 'word_blitz', 'cipher_hacker', 'space_defender', 'bomb_defuse', 'typing_ninja', 
    # 'memory_type', 'keyboard_quest'
    
    difficulty = db.Column(db.String(20), default='intermediate', index=True) 
    # 'beginner', 'intermediate', 'advanced', 'expert'
    
    target_text = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), default='general', index=True)
    # 'common', 'rare', 'numeric', 'symbolic', 'code', 'punctuation', 'weak_ngram'
    
    associated_keys = db.Column(db.String(64), nullable=True) # e.g. "E,R,T" or "1,2,3"
    word_length = db.Column(db.Integer, default=5)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ArcadeGameConfig(db.Model):
    __tablename__ = 'arcade_game_configs'

    id = db.Column(db.Integer, primary_key=True)
    game_slug = db.Column(db.String(50), unique=True, nullable=False)
    display_title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # Supported Mode Constraints
    allows_solo_ai = db.Column(db.Boolean, default=True)
    allows_1v1 = db.Column(db.Boolean, default=True)
    allows_multiplayer = db.Column(db.Boolean, default=False)
    max_multiplayer_players = db.Column(db.Integer, default=2)
    
    # Available Durations (comma-separated seconds, e.g. "30,60,120")
    durations = db.Column(db.String(50), default="60")
    default_ai_level = db.Column(db.String(20), default="intermediate")
    is_enabled = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)