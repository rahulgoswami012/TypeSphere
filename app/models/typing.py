from datetime import datetime
from app import db
import json

class TypingTest(db.Model):
    __tablename__ = 'typing_tests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    mode = db.Column(db.String(32), default='timed') # timed, word, quote, code, survival, etc.
    duration = db.Column(db.Float, nullable=False) # seconds
    wpm = db.Column(db.Float, nullable=False, index=True)
    raw_wpm = db.Column(db.Float, nullable=False)
    accuracy = db.Column(db.Float, nullable=False, index=True)
    consistency = db.Column(db.Float, nullable=False)
    rhythm_score = db.Column(db.Float, default=100.0)
    errors = db.Column(db.Integer, default=0)
    correct_chars = db.Column(db.Integer, default=0)
    incorrect_chars = db.Column(db.Integer, default=0)
    extra_chars = db.Column(db.Integer, default=0)
    missed_chars = db.Column(db.Integer, default=0)
    suspicious = db.Column(db.Boolean, default=False, index=True)
    suspicion_reason = db.Column(db.String(255), nullable=True)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Serialized detailed metrics & replay keystrokes
    timeline_data = db.Column(db.Text, nullable=True) # JSON list: [{'t': 1.0, 'wpm': 75, 'acc': 98}]
    events_data = db.Column(db.Text, nullable=True) # JSON list of keystroke events for Ghost replay

    def get_timeline(self):
        return json.loads(self.timeline_data) if self.timeline_data else []

    def get_events(self):
        return json.loads(self.events_data) if self.events_data else []

class TypingText(db.Model):
    __tablename__ = 'typing_texts'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(64), default='General', index=True)
    difficulty = db.Column(db.String(32), default='medium') # easy, medium, hard
    language = db.Column(db.String(32), default='english')
    content = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(128), default='System')
    is_code = db.Column(db.Boolean, default=False)
    code_lang = db.Column(db.String(32), nullable=True) # python, javascript, sql, etc.

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
    key_stats_json = db.Column(db.Text, default='{}') # Per-key frequency, error rate, avg delay
    confusion_matrix_json = db.Column(db.Text, default='{}') # {"e": {"r": 4}}
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_key_stats(self):
        return json.loads(self.key_stats_json) if self.key_stats_json else {}

    def get_confusion_matrix(self):
        return json.loads(self.confusion_matrix_json) if self.confusion_matrix_json else {}