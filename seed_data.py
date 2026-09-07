from app import create_app, db
from app.models.user import User
from app.models.typing import TypingText
from app.models.challenge import Achievement, DailyChallenge
from app.models.curriculum import LessonStage
from sqlalchemy import text
from datetime import date
import sys

app = create_app()

def seed_database():
    with app.app_context():
        print("🌱 Initializing Database Schema...")
        db.create_all()

        # Resilient SQLite Schema Auto-Patch
        try:
            with db.engine.connect() as conn:
                # Only run PRAGMA if on SQLite
                if 'sqlite' in str(db.engine.url):
                    res = conn.execute(text("PRAGMA table_info(users)"))
                    existing_cols = {row[1] for row in res.fetchall()}
                    if existing_cols:
                        if 'is_verified' not in existing_cols:
                            conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 1"))
                        if 'elo_rating' not in existing_cols:
                            conn.execute(text("ALTER TABLE users ADD COLUMN elo_rating INTEGER DEFAULT 1000"))
                        if 'ranked_wins' not in existing_cols:
                            conn.execute(text("ALTER TABLE users ADD COLUMN ranked_wins INTEGER DEFAULT 0"))
                        if 'ranked_losses' not in existing_cols:
                            conn.execute(text("ALTER TABLE users ADD COLUMN ranked_losses INTEGER DEFAULT 0"))
                        conn.commit()
        except Exception as e:
            print("Auto-migration note:", e)

        # 1. Admin & Test Typist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@typesphere.io',
                role='admin',
                is_verified=True,
                elo_rating=1200,
                ranked_wins=0,
                ranked_losses=0
            )
            admin.set_password('AdminMaster2026!')
            db.session.add(admin)
        else:
            admin.is_verified = True

        typist = User.query.filter_by(username='speeddemon').first()
        if not typist:
            typist = User(
                username='speeddemon',
                email='speed@typesphere.io',
                role='user',
                is_verified=True,
                elo_rating=1350,
                ranked_wins=5,
                ranked_losses=1
            )
            typist.set_password('SpeedPass123!')
            db.session.add(typist)
        else:
            typist.is_verified = True

        # 2. Universal Achievement Catalog
        badges = [
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
        for code, title, desc, icon in badges:
            if not Achievement.query.filter_by(code=code).first():
                db.session.add(Achievement(code=code, title=title, description=desc, icon=icon))

        # 3. Categorized Typing Prompts
        prompts = [
            ("Literature", "It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife. However little known the feelings or views of such a man may be on his first entering a neighbourhood, this truth is so well fixed in the minds of the surrounding families, that he is considered as the rightful property of some one or other of their daughters.", False, None),
            ("Technology", "Distributed ledger systems and asynchronous message brokers provide high fault-tolerance across modern decoupled server meshes. Ensuring sub-millisecond execution demands rigorous attention to serialization overhead, kernel context switches, and cache locality.", False, None),
            ("Science", "The double helix of DNA encapsulates the biochemical blueprint of organic life. Hydrogen bonds bridging complementary base pairs ensure stability across generations while allowing cellular replication mechanisms to unwind and transcribe genetic commands.", False, None),
            ("Programming", "def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)", True, "python")
        ]

        for cat, content, is_code, code_lang in prompts:
            if not TypingText.query.filter_by(content=content).first():
                db.session.add(TypingText(category=cat, content=content, is_code=is_code, code_lang=code_lang))

        # 4. Daily Challenge
        today = date.today()
        if not DailyChallenge.query.filter_by(target_date=today).first():
            db.session.add(DailyChallenge(
                target_date=today,
                title="The Kinetic Discipline",
                content="True velocity is not rushed chaos; it is calm, deliberate movement free of hesitation and unnecessary recoil."
            ))

        db.session.commit()
        print("✅ Database seeding complete. Ready for production.")

if __name__ == '__main__':
    seed_database()
    sys.exit(0)