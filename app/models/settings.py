from app import db

class UserSettings(db.Model):
    __tablename__ = 'user_settings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    
    # Appearance & Ergonomics
    theme = db.Column(db.String(32), default='dark') # dark, light, cyber, sepia
    font_family = db.Column(db.String(64), default='JetBrains Mono')
    font_size = db.Column(db.Integer, default=22)
    caret_style = db.Column(db.String(32), default='smooth') # smooth, block, underline
    sound_enabled = db.Column(db.Boolean, default=True)
    sound_theme = db.Column(db.String(32), default='mechanical')
    sound_volume = db.Column(db.Float, default=0.7)
    show_keyboard = db.Column(db.Boolean, default=True)

    # Initial Test Defaults (Blind Mode: ON, Ghost Mode: OFF)
    default_duration = db.Column(db.Integer, default=60) # 60s, 120s, 300s, 600s, 1200s, 0 (No Limit)
    default_content = db.Column(db.String(32), default='words') # words, quotes, numbers, punctuation, mixed, code, custom
    default_level = db.Column(db.String(32), default='moderate') # easy, moderate, hard, expert
    blind_mode = db.Column(db.Boolean, default=True) # Blind Mode ON by default
    ghost_mode = db.Column(db.Boolean, default=False) # Ghost Mode OFF by default