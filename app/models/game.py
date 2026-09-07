from datetime import datetime
from app import db

class GameRecord(db.Model):
    __tablename__ = 'game_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    game_mode = db.Column(db.String(50), nullable=False, index=True) # 'falling_words', 'shooter', 'reaction'
    score = db.Column(db.Integer, default=0)
    words_typed = db.Column(db.Integer, default=0)
    accuracy = db.Column(db.Float, default=100.0)
    duration_seconds = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('game_records', lazy='dynamic'))