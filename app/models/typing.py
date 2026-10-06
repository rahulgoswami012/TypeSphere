from datetime import datetime
import json
import re
from app import db

# Association Table: TypingText <-> PassageTag (Many-to-Many)
passage_tags = db.Table(
    'passage_tags',
    db.Column('passage_id', db.Integer, db.ForeignKey('typing_texts.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)

# Association Table: TypingText <-> PassageCollection (Many-to-Many)
passage_collections = db.Table(
    'passage_collections',
    db.Column('passage_id', db.Integer, db.ForeignKey('typing_texts.id', ondelete='CASCADE'), primary_key=True),
    db.Column('collection_id', db.Integer, db.ForeignKey('collections.id', ondelete='CASCADE'), primary_key=True),
    db.Column('added_at', db.DateTime, default=datetime.utcnow)
)


class PassageTag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False, index=True)
    slug = db.Column(db.String(64), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PassageTag {self.name}>"


class PassageCollection(db.Model):
    __tablename__ = 'collections'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), unique=True, nullable=False)
    slug = db.Column(db.String(128), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_by = db.Column(db.String(64), default='SuperAdmin')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    passages = db.relationship(
        'TypingText',
        secondary=passage_collections,
        back_populates='collections',
        lazy='dynamic'
    )

    def __repr__(self):
        return f"<PassageCollection {self.title}>"


class PassageReport(db.Model):
    __tablename__ = 'passage_reports'

    id = db.Column(db.Integer, primary_key=True)
    passage_id = db.Column(db.Integer, db.ForeignKey('typing_texts.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    reason = db.Column(db.String(64), nullable=False) # 'spelling', 'grammar', 'formatting', 'duplicate', 'offensive', 'wrong_language', 'other'
    details = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), default='pending', index=True) # 'pending', 'resolved', 'dismissed'
    admin_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.String(64), nullable=True)

    passage = db.relationship('TypingText', back_populates='reports')
    user = db.relationship('User', foreign_keys=[user_id])


class TypingTest(db.Model):
    __tablename__ = 'typing_tests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)

    # Mode & Ranked Classification
    mode = db.Column(db.String(32), default='timed') # 'timed_60', 'accuracy', 'survival', 'custom', 'daily', etc.
    is_ranked = db.Column(db.Boolean, default=False, index=True)
    content_category = db.Column(db.String(64), default='General')
    difficulty = db.Column(db.String(32), default='moderate')

    # Core Telemetry
    duration = db.Column(db.Float, nullable=False) # In seconds
    wpm = db.Column(db.Float, nullable=False, index=True) # Net WPM
    raw_wpm = db.Column(db.Float, nullable=False) # Gross WPM
    accuracy = db.Column(db.Float, nullable=False, index=True)
    consistency = db.Column(db.Float, nullable=False)
    rhythm_score = db.Column(db.Float, default=100.0)

    # Granular Keystroke Breakdown
    errors = db.Column(db.Integer, default=0) # Legacy compatibility
    total_mistakes = db.Column(db.Integer, default=0) # Every errant strike made
    uncorrected_errors = db.Column(db.Integer, default=0) # Red errors left at finish
    correct_chars = db.Column(db.Integer, default=0)
    incorrect_chars = db.Column(db.Integer, default=0)
    extra_chars = db.Column(db.Integer, default=0)
    missed_chars = db.Column(db.Integer, default=0)

    # Temporal & Timezone Telemetry
    completed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    time_of_day_ist = db.Column(db.Integer, nullable=True) # 0-23 IST

    # Anti-Cheat Telemetry
    suspicious = db.Column(db.Boolean, default=False, index=True)
    suspicion_reason = db.Column(db.String(255), nullable=True)

    # Serialized Timeline & Event Logs
    timeline_data = db.Column(db.Text, nullable=True)
    events_data = db.Column(db.Text, nullable=True)

    def get_timeline(self):
        return json.loads(self.timeline_data) if self.timeline_data else []

    def get_events(self):
        return json.loads(self.events_data) if self.events_data else []


class TypingText(db.Model):
    __tablename__ = 'typing_texts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), default="Untitled Passage", index=True)
    slug = db.Column(db.String(180), unique=True, nullable=True, index=True)

    # Content Body
    content = db.Column(db.Text, nullable=False)

    # Classification Structure
    language = db.Column(db.String(32), default='english', index=True) # english, hindi, hinglish, regional
    category = db.Column(db.String(64), default='General', index=True) # Technology, Literature, Education, Business, Science, History, etc.
    passage_type = db.Column(db.String(32), default='paragraph', index=True) # paragraph, article, story, quote, dialogue, business, technical, exam_style, numbers, code
    difficulty = db.Column(db.String(32), default='moderate', index=True) # easy, moderate, hard, expert
    purpose = db.Column(db.String(255), default='general_practice') # CSV or token list: general_practice, speed_practice, accuracy_practice, exam_prep, multiplayer, daily_challenge

    # Exam Specifics
    exam_profile = db.Column(db.String(64), nullable=True, index=True) # None, ssc_cgl, ssc_chsl, rrb, cpct, court_steno, banking, state_gov, other
    exam_style = db.Column(db.String(64), nullable=True) # general, ssc_style, cpct_style, court_style, office_style, custom
    region = db.Column(db.String(64), default='India')

    # Quantitative Lexical Metrics
    word_count = db.Column(db.Integer, default=0)
    character_count = db.Column(db.Integer, default=0)
    character_count_no_spaces = db.Column(db.Integer, default=0)
    sentence_count = db.Column(db.Integer, default=0)
    paragraph_count = db.Column(db.Integer, default=1)
    avg_word_length = db.Column(db.Float, default=0.0)
    complexity_score = db.Column(db.Float, default=1.0) # Difficulty score (1.0 to 100.0)

    # Multi-Duration Guidance
    recommended_duration = db.Column(db.Integer, default=60) # In seconds: 60, 120, 300, 600, etc.
    min_duration = db.Column(db.Integer, default=15)
    max_duration = db.Column(db.Integer, default=1200)

    # Publishing & Visibility Governance
    status = db.Column(db.String(20), default='published', index=True) # draft, review, published, featured, paused, archived
    visibility = db.Column(db.String(32), default='everyone') # everyone, logged_in, admin_only
    is_active = db.Column(db.Boolean, default=True, index=True) # legacy backwards compatibility
    is_featured = db.Column(db.Boolean, default=False, index=True)
    allow_random = db.Column(db.Boolean, default=True)
    allow_multiplayer = db.Column(db.Boolean, default=True)

    # Attribution & Provenance
    source = db.Column(db.String(128), default='System')
    source_type = db.Column(db.String(64), default='original_practice') # original_practice, exam_style, official_source, previous_year, user_submitted
    source_url = db.Column(db.String(255), nullable=True)

    # Programming Syntax Flag
    is_code = db.Column(db.Boolean, default=False)
    code_lang = db.Column(db.String(32), nullable=True)

    # Operational Telemetry & Analytics
    times_used = db.Column(db.Integer, default=0)
    unique_users = db.Column(db.Integer, default=0)
    avg_wpm = db.Column(db.Float, default=0.0)
    avg_accuracy = db.Column(db.Float, default=0.0)
    report_count = db.Column(db.Integer, default=0)
    health_score = db.Column(db.Integer, default=100) # 0 to 100%

    # Metadata & Tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.String(64), default="System")
    updated_by = db.Column(db.String(64), nullable=True)

    # Relationships
    tags = db.relationship(
        'PassageTag',
        secondary=passage_tags,
        lazy='joined',
        backref=db.backref('passages', lazy='dynamic')
    )

    collections = db.relationship(
        'PassageCollection',
        secondary=passage_collections,
        back_populates='passages',
        lazy='joined'
    )

    reports = db.relationship(
        'PassageReport',
        back_populates='passage',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    def calculate_stats(self):
        """
        Executes complete quantitative analysis across the passage body.
        """
        from app.services.passage_service import PassageService
        metrics = PassageService.calculate_metrics(self.content or "")
        self.word_count = metrics['word_count']
        self.character_count = metrics['character_count']
        self.character_count_no_spaces = metrics['character_count_no_spaces']
        self.sentence_count = metrics['sentence_count']
        self.paragraph_count = metrics['paragraph_count']
        self.avg_word_length = metrics['avg_word_length']
        self.complexity_score = metrics['complexity_score']
        if not self.difficulty or self.difficulty == 'moderate':
            self.difficulty = metrics['suggested_difficulty']

    @property
    def display_preview(self) -> str:
        if not self.content:
            return ""
        clean = " ".join(self.content.split())
        return clean[:110] + ("..." if len(clean) > 110 else "")

    @property
    def purpose_list(self) -> list:
        if not self.purpose:
            return ['general_practice']
        return [p.strip() for p in self.purpose.split(',') if p.strip()]

    def __repr__(self):
        return f"<TypingText #{self.id} '{self.title}'>"


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