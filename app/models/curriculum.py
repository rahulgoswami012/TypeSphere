from datetime import datetime
from app import db

class LessonStage(db.Model):
    __tablename__ = 'lesson_stages'

    id = db.Column(db.Integer, primary_key=True)
    stage_number = db.Column(db.Integer, unique=True, nullable=False) # 1 to 12
    title = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    focus_keys = db.Column(db.String(64), nullable=True) # e.g., 'A S D F J K L ;'
    practice_material = db.Column(db.Text, nullable=False)
    min_wpm_to_pass = db.Column(db.Float, default=20.0)
    min_accuracy_to_pass = db.Column(db.Float, default=92.0)

class UserLessonProgress(db.Model):
    __tablename__ = 'user_lesson_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stage_id = db.Column(db.Integer, db.ForeignKey('lesson_stages.id'), nullable=False)
    
    completed = db.Column(db.Boolean, default=False)
    best_wpm = db.Column(db.Float, default=0.0)
    best_accuracy = db.Column(db.Float, default=0.0)
    attempts = db.Column(db.Integer, default=0)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    stage = db.relationship('LessonStage')
    user = db.relationship('User', backref=db.backref('curriculum_progress', lazy='dynamic'))