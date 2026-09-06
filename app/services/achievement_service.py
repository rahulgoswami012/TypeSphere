from datetime import datetime
from app import db
from app.models.challenge import Achievement, UserAchievement
from app.models.typing import TypingTest

BADGES_CATALOG = [
    ('first_test', 'First Contact', 'Complete your very first typing test on TypeSphere.', 'zap'),
    ('wpm_50', 'Cruising Velocity', 'Reach a verified speed of 50 WPM.', 'award'),
    ('wpm_75', 'Sonic Cadence', 'Reach a verified speed of 75 WPM.', 'trending-up'),
    ('wpm_100', 'Century Club', 'Surpass the triple-digit barrier of 100 WPM.', 'cpu'),
    ('perfect_acc', 'Flawless Flow', 'Complete a full test with exactly 100% accuracy.', 'shield'),
    ('night_owl', 'Night Owl', 'Complete a verified typing run between 12:00 AM and 5:00 AM.', 'moon'),
    ('early_bird', 'Early Bird', 'Complete a verified typing run between 5:00 AM and 8:00 AM.', 'sun'),
    ('survival_master', 'Survival Master', 'Complete a full test in Survival Mode without losing all 3 hearts.', 'heart'),
    ('certified_typist', 'Certified Scholar', 'Generate an official proficiency certificate.', 'file-text'),
    ('century_veteran', 'Century Veteran', 'Complete 100 verified tests on TypeSphere.', 'activity')
]

class AchievementService:
    @staticmethod
    def ensure_catalog():
        """Ensure all badges exist in the database with matching codes."""
        for code, title, desc, icon in BADGES_CATALOG:
            ach = Achievement.query.filter_by(code=code).first()
            if not ach:
                # Check legacy aliases (e.g. 'century' vs 'century_veteran')
                if code == 'century_veteran':
                    legacy = Achievement.query.filter_by(code='century').first()
                    if legacy:
                        legacy.code = 'century_veteran'
                        legacy.title = title
                        legacy.description = desc
                        continue
                ach = Achievement(code=code, title=title, description=desc, icon=icon)
                db.session.add(ach)
        db.session.commit()

    @staticmethod
    def check_and_award(user):
        if not user or not user.is_authenticated:
            return []

        AchievementService.ensure_catalog()

        # Retrieve all tests logged by this user
        tests = TypingTest.query.filter_by(user_id=user.id).all()
        if not tests:
            return []

        test_count = len(tests)
        max_wpm = max((t.wpm for t in tests), default=0)
        perfect_tests = any(t.accuracy >= 100.0 for t in tests)
        survival_wins = any(t.mode == 'survival' for t in tests)

        # Check existing unlocked codes for this user
        user_achievements = UserAchievement.query.filter_by(user_id=user.id).all()
        existing_codes = set()
        for ua in user_achievements:
            if ua.achievement:
                existing_codes.add(ua.achievement.code)

        earned_codes = []

        # 1. First Test
        if test_count >= 1 and 'first_test' not in existing_codes:
            earned_codes.append('first_test')

        # 2. Speed Tiers
        if max_wpm >= 50 and 'wpm_50' not in existing_codes:
            earned_codes.append('wpm_50')
        if max_wpm >= 75 and 'wpm_75' not in existing_codes:
            earned_codes.append('wpm_75')
        if max_wpm >= 100 and 'wpm_100' not in existing_codes:
            earned_codes.append('wpm_100')

        # 3. Flawless Accuracy
        if perfect_tests and 'perfect_acc' not in existing_codes:
            earned_codes.append('perfect_acc')

        # 4. Night Owl (12 AM - 5 AM)
        if any(0 <= t.completed_at.hour < 5 for t in tests) and 'night_owl' not in existing_codes:
            earned_codes.append('night_owl')

        # 5. Early Bird (5 AM - 8 AM)
        if any(5 <= t.completed_at.hour < 8 for t in tests) and 'early_bird' not in existing_codes:
            earned_codes.append('early_bird')

        # 6. Survival Master
        if survival_wins and 'survival_master' not in existing_codes:
            earned_codes.append('survival_master')

        # 7. Century Veteran
        if test_count >= 100 and 'century_veteran' not in existing_codes:
            earned_codes.append('century_veteran')

        newly_unlocked = []
        for code in earned_codes:
            ach = Achievement.query.filter_by(code=code).first()
            if ach:
                ua = UserAchievement(user_id=user.id, achievement_id=ach.id)
                db.session.add(ua)
                newly_unlocked.append(ach.title)

        if newly_unlocked:
            db.session.commit()

        return newly_unlocked

    @staticmethod
    def award_code(user, code):
        """Directly award a specific badge code (e.g. for generating certificate)."""
        if not user or not user.is_authenticated:
            return False
        AchievementService.ensure_catalog()
        ach = Achievement.query.filter_by(code=code).first()
        if not ach:
            return False
        existing = UserAchievement.query.filter_by(user_id=user.id, achievement_id=ach.id).first()
        if not existing:
            ua = UserAchievement(user_id=user.id, achievement_id=ach.id)
            db.session.add(ua)
            db.session.commit()
            return True
        return False