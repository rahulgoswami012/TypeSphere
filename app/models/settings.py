from app import db

class UserSettings(db.Model):
    __tablename__ = 'user_settings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)

    # Appearance & Ergonomics
    theme = db.Column(db.String(32), default='dark') # dark, cockpit-hud, cyber, sepia, light
    font_family = db.Column(db.String(64), default='JetBrains Mono')
    font_size = db.Column(db.Integer, default=22)
    caret_style = db.Column(db.String(32), default='smooth') # smooth, block, underline
    typing_area_style = db.Column(db.String(32), default='modern') # modern, cockpit, minimal, terminal
    keyboard_display = db.Column(db.String(32), default='heatmap') # heatmap, simple, hidden
    reduce_motion = db.Column(db.Boolean, default=False)

    # Acoustic Audio Feedback
    sound_enabled = db.Column(db.Boolean, default=True)
    sound_theme = db.Column(db.String(32), default='mechanical') # mechanical, bubble, beep
    sound_volume = db.Column(db.Float, default=0.7)
    game_sound_volume = db.Column(db.Float, default=0.7)
    game_sound_theme = db.Column(db.String(32), default='retro')

    # Benchmark Defaults (Blind: ON, Ghost: OFF)
    default_duration = db.Column(db.Integer, default=60)
    default_content = db.Column(db.String(32), default='words')
    default_level = db.Column(db.String(32), default='moderate')
    blind_mode = db.Column(db.Boolean, default=True)
    ghost_mode = db.Column(db.Boolean, default=False)
    confidence_mode = db.Column(db.Boolean, default=False)