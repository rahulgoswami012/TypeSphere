from datetime import datetime
from app import db

class ContentItem(db.Model):
    __tablename__ = 'content_items'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=True)
    category = db.Column(db.String(64), nullable=False, index=True) 
    # 'words', 'sentences', 'paragraphs', 'quotes', 'stories', 'realworld', 'data_entry', 'numbers', 'punctuation', 'coding', 'exam'
    subcategory = db.Column(db.String(64), nullable=True, index=True) 
    # e.g., 'emails', 'invoices', 'python', 'ssc_cgl', 'court_steno'
    difficulty = db.Column(db.String(32), default='moderate', index=True) # 'easy', 'moderate', 'hard', 'expert'
    
    body = db.Column(db.Text, nullable=False)
    source_author = db.Column(db.String(128), nullable=True)
    
    # Quantitative Lexical Metadata
    word_count = db.Column(db.Integer, default=0)
    character_count = db.Column(db.Integer, default=0)
    punctuation_density = db.Column(db.Float, default=0.0) # percentage of punct chars
    numeric_density = db.Column(db.Float, default=0.0)     # percentage of digits
    avg_word_length = db.Column(db.Float, default=0.0)
    complexity_score = db.Column(db.Float, default=1.0)    # 1.0 to 5.0 difficulty rating
    
    # Premium-Ready Feature Flags (All initially completely accessible)
    is_premium_exclusive = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def calculate_metrics(self):
        chars = len(self.body)
        words = self.body.split()
        num_words = len(words) if words else 1
        
        punct_count = sum(1 for c in self.body if c in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
        num_count = sum(1 for c in self.body if c.isdigit())
        total_letters = sum(len(w) for w in words)
        
        self.character_count = chars
        self.word_count = num_words
        self.punctuation_density = round((punct_count / chars) * 100.0, 2) if chars else 0.0
        self.numeric_density = round((num_count / chars) * 100.0, 2) if chars else 0.0
        self.avg_word_length = round(total_letters / num_words, 2) if num_words else 0.0

class ExamTemplate(db.Model):
    __tablename__ = 'exam_templates'

    id = db.Column(db.Integer, primary_key=True)
    exam_code = db.Column(db.String(50), unique=True, nullable=False) # 'ssc_chsl', 'rrb_ntpc', 'court_clerk'
    exam_title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    duration_seconds = db.Column(db.Integer, default=600) # e.g. 10 or 15 mins
    required_wpm = db.Column(db.Float, default=35.0)
    max_error_percentage = db.Column(db.Float, default=5.0) # Strict government threshold
    allow_backspace = db.Column(db.Boolean, default=True)
    strict_case_match = db.Column(db.Boolean, default=True)
    
    content = db.Column(db.Text, nullable=False)