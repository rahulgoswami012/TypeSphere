from datetime import datetime
import json
from app import db

class TypingTest(db.Model):
    __tablename__ = 'typing_tests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    
    # Mode & Ranked Classification
    mode = db.Column(db.String(32), default='timed') # 'timed', 'words', 'quote', 'custom', 'code', etc.
    is_ranked = db.Column(db.Boolean, default=False, index=True) # True only for verified standard runs
    content_category = db.Column(db.String(64), default='General')
    difficulty = db.Column(db.String(32), default='moderate') # 'easy', 'moderate', 'hard', 'expert'
    
    # Core Telemetry
    duration = db.Column(db.Float, nullable=False) # In seconds
    wpm = db.Column(db.Float, nullable=False, index=True) # Net WPM
    raw_wpm = db.Column(db.Float, nullable=False) # Gross WPM
    accuracy = db.Column(db.Float, nullable=False, index=True)
    consistency = db.Column(db.Float, nullable=False)
    rhythm_score = db.Column(db.Float, default=100.0)
    
    # Keystroke Breakdown
    errors = db.Column(db.Integer, default=0)
    correct_chars = db.Column(db.Integer, default=0)
    incorrect_chars = db.Column(db.Integer, default=0)
    extra_chars = db.Column(db.Integer, default=0)
    missed_chars = db.Column(db.Integer, default=0)
    
    # Integrity & Anti-Cheat
    suspicious = db.Column(db.Boolean, default=False, index=True)
    suspicion_reason = db.Column(db.String(255), nullable=True)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Serialized Keystroke Log & WPM Timeline for Replays
    timeline_data = db.Column(db.Text, nullable=True)
    events_data = db.Column(db.Text, nullable=True)

    def get_timeline(self):
        return json.loads(self.timeline_data) if self.timeline_data else []

    def get_events(self):
        return json.loads(self.events_data) if self.events_data else []

class TypingText(db.Model):
    __tablename__ = 'typing_texts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), default="Untitled Passage")
    category = db.Column(db.String(64), default='General', index=True)
    difficulty = db.Column(db.String(32), default='Medium', index=True) # Easy, Medium, Hard, Expert
    language = db.Column(db.String(32), default='english')
    content = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(128), default='System')
    is_code = db.Column(db.Boolean, default=False)
    code_lang = db.Column(db.String(32), nullable=True)
    
    # Content Metadata
    word_count = db.Column(db.Integer, default=0)
    character_count = db.Column(db.Integer, default=0)
    complexity_score = db.Column(db.Float, default=1.0)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(64), default="System")
    updated_by = db.Column(db.String(64), nullable=True)

    def calculate_stats(self):
        words = self.content.strip().split()
        self.word_count = len(words)
        self.character_count = len(self.content.strip())

class TypingDNA(db.Model):
    __tablename__ = 'typing_dna'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    
    left_hand_accuracy = db.Column(db.Float, default=100.0)
    right_hand_accuracy = db.Column(db.Float, default=100.0)
    punctuation_accuracy = db.Column(db.Float, default=100.0)
    numbers_accuracy = db.Column(db.Float, default=100.0)
    capitals_accuracy = db.Column(db.Float, default=100.0)
    rhythm_consistency_avg = db.Column(db.Float, default=100.0)
    
    key_stats_json = db.Column(db.Text, default='{}')
    confusion_matrix_json = db.Column(db.Text, default='{}')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_key_stats(self):
        return json.loads(self.key_stats_json) if self.key_stats_json else {}

    def get_confusion_matrix(self):
        return json.loads(self.confusion_matrix_json) if self.confusion_matrix_json else {}