from datetime import datetime
from app import db

class LessonStage(db.Model):
    __tablename__ = 'lesson_stages'
    __table_args__ = (
        db.UniqueConstraint('track', 'stage_number', name='uix_track_stage'),
    )

    id = db.Column(db.Integer, primary_key=True)
    track = db.Column(db.String(32), default='beginner', index=True) # 'beginner', 'intermediate', 'advanced', 'expert'
    stage_number = db.Column(db.Integer, nullable=False) # Sequence within track
    title = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # Ergonomic Guidance
    focus_keys = db.Column(db.String(64), nullable=True) # e.g., 'F J D K'
    hand_position_hint = db.Column(db.String(128), nullable=True)
    keyboard_row = db.Column(db.String(32), default='home') # 'home', 'top', 'bottom', 'numbers', 'symbols'
    
    practice_material = db.Column(db.Text, nullable=False)
    min_wpm_to_pass = db.Column(db.Float, default=20.0)
    min_accuracy_to_pass = db.Column(db.Float, default=95.0)
    required_attempts = db.Column(db.Integer, default=2) # Multi-attempt verification


class UserLessonProgress(db.Model):
    __tablename__ = 'user_lesson_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stage_id = db.Column(db.Integer, db.ForeignKey('lesson_stages.id'), nullable=False)
    
    completed = db.Column(db.Boolean, default=False)
    successful_attempts = db.Column(db.Integer, default=0)
    best_wpm = db.Column(db.Float, default=0.0)
    best_accuracy = db.Column(db.Float, default=0.0)
    total_attempts = db.Column(db.Integer, default=0)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    stage = db.relationship('LessonStage')
    user = db.relationship('User', backref=db.backref('curriculum_progress', lazy='dynamic'))