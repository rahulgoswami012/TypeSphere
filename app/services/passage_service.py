"""
TypeSphere - Passage Intelligence & Lexical Telemetry Service
Performs quantitative textual analysis, automatic difficulty scoring,
duplicate passage detection, and health score verification.
"""

import re
import unicodedata
from typing import Dict, Any, List, Tuple
from app import db
from app.models.typing import TypingText


class PassageService:
    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalizes text for duplicate comparisons: lowercase, stripped punctuation,
        normalized whitespace and unicode canonical decomposition.
        """
        if not text:
            return ""
        norm = unicodedata.normalize('NFKD', text).lower()
        norm = re.sub(r'[^\w\s]', '', norm)
        return " ".join(norm.split())

    @staticmethod
    def calculate_metrics(text: str) -> Dict[str, Any]:
        """
        Calculates exact typographical and lexical statistics.
        """
        raw = text or ""
        trimmed = raw.strip()

        # Word tokens
        words = trimmed.split()
        word_count = len(words)

        # Characters
        char_count = len(raw)
        char_count_no_spaces = len(re.sub(r'\s', '', raw))

        # Sentences & Paragraphs
        sentences = [s for s in re.split(r'[.!?]+', raw) if s.strip()]
        sentence_count = max(1, len(sentences)) if trimmed else 0

        paragraphs = [p for p in raw.split('\n') if p.strip()]
        paragraph_count = max(1, len(paragraphs)) if trimmed else 1

        # Average Word Length
        total_letters = sum(len(w) for w in words)
        avg_word_length = round(total_letters / word_count, 2) if word_count else 0.0

        # Punctuation & Numeric density
        punct_count = len(re.findall(r'[!\"#$%&\'()*+,-./:;<=>?@\[\\\]^_`{|}~]', raw))
        digits_count = len(re.findall(r'\d', raw))

        punct_density = (punct_count / char_count * 100.0) if char_count else 0.0
        digit_density = (digits_count / char_count * 100.0) if char_count else 0.0

        # Lexical Difficulty Scoring (1.0 to 100.0)
        # Factor 1: Word length (normal English is ~4.7 chars)
        word_len_score = max(0.0, (avg_word_length - 4.0) * 15.0)

        # Factor 2: Syllabic complexity / long words (7+ letters)
        long_words = sum(1 for w in words if len(w) >= 7)
        long_word_pct = (long_words / word_count * 100.0) if word_count else 0.0

        # Composite complexity score
        raw_score = 25.0 + (word_len_score * 0.8) + (long_word_pct * 0.6) + (punct_density * 1.5) + (digit_density * 1.2)
        complexity_score = round(max(10.0, min(99.0, raw_score)), 1)

        # Suggested difficulty tier
        if complexity_score < 40.0:
            suggested_difficulty = 'easy'
        elif complexity_score < 65.0:
            suggested_difficulty = 'moderate'
        elif complexity_score < 80.0:
            suggested_difficulty = 'hard'
        else:
            suggested_difficulty = 'expert'

        return {
            'word_count': word_count,
            'character_count': char_count,
            'character_count_no_spaces': char_count_no_spaces,
            'sentence_count': sentence_count,
            'paragraph_count': paragraph_count,
            'avg_word_length': avg_word_length,
            'punctuation_density': round(punct_density, 2),
            'numeric_density': round(digit_density, 2),
            'complexity_score': complexity_score,
            'suggested_difficulty': suggested_difficulty
        }

    @staticmethod
    def detect_duplicates(text: str, exclude_id: int = None, threshold: float = 0.78) -> List[Tuple[TypingText, float]]:
        """
        Detects possible duplicate passages using tokenized Jaccard similarity.
        Returns list of (TypingText, similarity_percentage).
        """
        target_norm = PassageService.normalize_text(text)
        target_tokens = set(target_norm.split())
        if not target_tokens:
            return []

        query = TypingText.query
        if exclude_id:
            query = query.filter(TypingText.id != exclude_id)

        all_passages = query.with_entities(TypingText.id, TypingText.title, TypingText.content).all()
        duplicates = []

        for p_id, p_title, p_content in all_passages:
            other_norm = PassageService.normalize_text(p_content)
            other_tokens = set(other_norm.split())
            if not other_tokens:
                continue

            intersection = len(target_tokens & other_tokens)
            union = len(target_tokens | other_tokens)
            similarity = (intersection / union) if union > 0 else 0.0

            if similarity >= threshold:
                passage_obj = TypingText.query.get(p_id)
                if passage_obj:
                    duplicates.append((passage_obj, round(similarity * 100.0, 1)))

        duplicates.sort(key=lambda x: x[1], reverse=True)
        return duplicates

    @staticmethod
    def calculate_health_score(passage: TypingText) -> int:
        """
        Computes 0-100% Passage Health Score based on typographical standards,
        completeness, report history, and length sanity.
        """
        score = 100

        # Word count checks
        if passage.word_count < 15:
            score -= 30
        elif passage.word_count < 30:
            score -= 15

        # Empty or missing titles
        if not passage.title or passage.title.strip().lower() in ['untitled passage', 'passage', 'text']:
            score -= 10

        # Reports penalty
        reports = passage.report_count or 0
        score -= min(40, reports * 10)

        # Formatting irregularities (triple spaces, dangling lines)
        if re.search(r' {3,}', passage.content or ''):
            score -= 10
        if '\t' in (passage.content or '') and not passage.is_code:
            score -= 5

        # Ensure bounds
        return max(10, min(100, score))

    @staticmethod
    def get_library_statistics() -> Dict[str, Any]:
        """
        Returns high-level statistics for the Passage Library Overview dashboard.
        """
        total = TypingText.query.count()
        published = TypingText.query.filter(
            (TypingText.status == 'published') | ((TypingText.status == None) & (TypingText.is_active == True))
        ).count()
        draft = TypingText.query.filter_by(status='draft').count()
        review = TypingText.query.filter_by(status='review').count()
        archived = TypingText.query.filter(
            (TypingText.status == 'archived') | ((TypingText.status == None) & (TypingText.is_active == False))
        ).count()
        featured = TypingText.query.filter_by(is_featured=True).count()

        # Language breakdown
        english_count = TypingText.query.filter(
            (TypingText.language == 'english') | (TypingText.language == None)
        ).count()
        hindi_count = TypingText.query.filter_by(language='hindi').count()
        regional_count = total - english_count - hindi_count

        # Category / Purpose counts
        quotes_count = TypingText.query.filter(
            (TypingText.passage_type == 'quote') | (TypingText.category == 'Quotes')
        ).count()
        exam_count = TypingText.query.filter(
            (TypingText.exam_profile != None) | (TypingText.category.ilike('%exam%'))
        ).count()
        code_count = TypingText.query.filter_by(is_code=True).count()

        # Pending reports
        from app.models.typing import PassageReport
        pending_reports = PassageReport.query.filter_by(status='pending').count()

        return {
            'total_passages': total,
            'published': published,
            'draft': draft,
            'review': review,
            'archived': archived,
            'featured': featured,
            'english_count': english_count,
            'hindi_count': hindi_count,
            'regional_count': max(0, regional_count),
            'quotes_count': quotes_count,
            'exam_count': exam_count,
            'code_count': code_count,
            'pending_reports': pending_reports
        }