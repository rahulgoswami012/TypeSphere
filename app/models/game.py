from datetime import datetime
from app import db

class GameRecord(db.Model):
    __tablename__ = 'game_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    game_mode = db.Column(db.String(50), nullable=False, index=True)
    play_type = db.Column(db.String(30), default='solo_ai') # solo_practice, solo_ai, 1v1_private, multiplayer
    result_outcome = db.Column(db.String(20), default='FINISHED') # WIN, LOSS, DRAW, FINISHED
    
    score = db.Column(db.Integer, default=0, index=True)
    net_wpm = db.Column(db.Float, default=0.0)
    accuracy = db.Column(db.Float, default=100.0)
    errors = db.Column(db.Integer, default=0)
    highest_combo = db.Column(db.Integer, default=0)
    average_reaction_ms = db.Column(db.Float, default=0.0)
    
    meta_stats_json = db.Column(db.Text, default='{}')
    duration_seconds = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('game_records', lazy='dynamic'))

class ArcadeLeaderboard(db.Model):
    __tablename__ = 'arcade_leaderboards'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    game_mode = db.Column(db.String(50), nullable=False, index=True)
    high_score = db.Column(db.Integer, default=0, index=True)
    best_wpm = db.Column(db.Float, default=0.0)
    best_accuracy = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')