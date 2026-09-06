from app import db

class UserSettings(db.Model):
    __tablename__ = 'user_settings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    theme = db.Column(db.String(32), default='dark') # dark, light, cyber
    font_family = db.Column(db.String(64), default='JetBrains Mono')
    font_size = db.Column(db.Integer, default=20)
    caret_style = db.Column(db.String(32), default='smooth') # smooth, block, underline
    sound_enabled = db.Column(db.Boolean, default=True)
    sound_theme = db.Column(db.String(32), default='mechanical')
    show_keyboard = db.Column(db.Boolean, default=True)