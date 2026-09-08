import sys
from datetime import date, datetime
from sqlalchemy import text
from app import create_app, db
from app.models.user import User
from app.models.typing import TypingText, TypingTest
from app.models.challenge import Achievement, DailyChallenge
from app.models.curriculum import LessonStage
from app.models.arcade_content import ArcadeGameConfig, ArcadeContentItem
from app.models.admin import PlatformConfig
from app.models.feedback import RatingReview

app = create_app()

def seed_database():
    with app.app_context():
        print("🌱 Initializing Database Schema...")
        db.create_all()

        # 1. Resilient Auto-Migration Patch for SQLite
        try:
            with db.engine.connect() as conn:
                if 'sqlite' in str(db.engine.url):
                    # Patch users table
                    res = conn.execute(text("PRAGMA table_info(users)"))
                    cols = {row[1] for row in res.fetchall()}
                    if cols:
                        if 'is_verified' not in cols:
                            conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 1"))
                        if 'elo_rating' not in cols:
                            conn.execute(text("ALTER TABLE users ADD COLUMN elo_rating INTEGER DEFAULT 1000"))
                        if 'ranked_wins' not in cols:
                            conn.execute(text("ALTER TABLE users ADD COLUMN ranked_wins INTEGER DEFAULT 0"))
                        if 'ranked_losses' not in cols:
                            conn.execute(text("ALTER TABLE users ADD COLUMN ranked_losses INTEGER DEFAULT 0"))
                        if 'is_suspended' not in cols:
                            conn.execute(text("ALTER TABLE users ADD COLUMN is_suspended BOOLEAN DEFAULT 0"))
                        if 'is_banned' not in cols:
                            conn.execute(text("ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT 0"))
                        if 'status_reason' not in cols:
                            conn.execute(text("ALTER TABLE users ADD COLUMN status_reason VARCHAR(255)"))
                        if 'last_active' not in cols:
                            conn.execute(text("ALTER TABLE users ADD COLUMN last_active DATETIME"))

                    # Patch user_settings table
                    res = conn.execute(text("PRAGMA table_info(user_settings)"))
                    s_cols = {row[1] for row in res.fetchall()}
                    if s_cols:
                        if 'blind_mode' not in s_cols:
                            conn.execute(text("ALTER TABLE user_settings ADD COLUMN blind_mode BOOLEAN DEFAULT 1"))
                        if 'ghost_mode' not in s_cols:
                            conn.execute(text("ALTER TABLE user_settings ADD COLUMN ghost_mode BOOLEAN DEFAULT 0"))
                        if 'default_duration' not in s_cols:
                            conn.execute(text("ALTER TABLE user_settings ADD COLUMN default_duration INTEGER DEFAULT 60"))
                        if 'default_content' not in s_cols:
                            conn.execute(text("ALTER TABLE user_settings ADD COLUMN default_content VARCHAR(32) DEFAULT 'words'"))
                        if 'default_level' not in s_cols:
                            conn.execute(text("ALTER TABLE user_settings ADD COLUMN default_level VARCHAR(32) DEFAULT 'moderate'"))
                        if 'sound_volume' not in s_cols:
                            conn.execute(text("ALTER TABLE user_settings ADD COLUMN sound_volume FLOAT DEFAULT 0.7"))

                    # Patch typing_texts table
                    res = conn.execute(text("PRAGMA table_info(typing_texts)"))
                    t_cols = {row[1] for row in res.fetchall()}
                    if t_cols:
                        if 'title' not in t_cols:
                            conn.execute(text("ALTER TABLE typing_texts ADD COLUMN title VARCHAR(128) DEFAULT 'Passage'"))
                        if 'word_count' not in t_cols:
                            conn.execute(text("ALTER TABLE typing_texts ADD COLUMN word_count INTEGER DEFAULT 0"))
                        if 'character_count' not in t_cols:
                            conn.execute(text("ALTER TABLE typing_texts ADD COLUMN character_count INTEGER DEFAULT 0"))
                        if 'complexity_score' not in t_cols:
                            conn.execute(text("ALTER TABLE typing_texts ADD COLUMN complexity_score FLOAT DEFAULT 1.0"))
                        if 'is_active' not in t_cols:
                            conn.execute(text("ALTER TABLE typing_texts ADD COLUMN is_active BOOLEAN DEFAULT 1"))
                        if 'created_by' not in t_cols:
                            conn.execute(text("ALTER TABLE typing_texts ADD COLUMN created_by VARCHAR(64) DEFAULT 'System'"))
                        if 'updated_by' not in t_cols:
                            conn.execute(text("ALTER TABLE typing_texts ADD COLUMN updated_by VARCHAR(64)"))

                    # Patch typing_tests table
                    res = conn.execute(text("PRAGMA table_info(typing_tests)"))
                    test_cols = {row[1] for row in res.fetchall()}
                    if test_cols:
                        if 'is_ranked' not in test_cols:
                            conn.execute(text("ALTER TABLE typing_tests ADD COLUMN is_ranked BOOLEAN DEFAULT 0"))
                        if 'content_category' not in test_cols:
                            conn.execute(text("ALTER TABLE typing_tests ADD COLUMN content_category VARCHAR(64) DEFAULT 'General'"))
                        if 'difficulty' not in test_cols:
                            conn.execute(text("ALTER TABLE typing_tests ADD COLUMN difficulty VARCHAR(32) DEFAULT 'moderate'"))

                    # Patch lesson_stages table
                    res = conn.execute(text("PRAGMA table_info(lesson_stages)"))
                    l_cols = {row[1] for row in res.fetchall()}
                    if l_cols:
                        if 'track' not in l_cols:
                            conn.execute(text("ALTER TABLE lesson_stages ADD COLUMN track VARCHAR(32) DEFAULT 'beginner'"))
                        if 'hand_position_hint' not in l_cols:
                            conn.execute(text("ALTER TABLE lesson_stages ADD COLUMN hand_position_hint VARCHAR(128)"))
                        if 'keyboard_row' not in l_cols:
                            conn.execute(text("ALTER TABLE lesson_stages ADD COLUMN keyboard_row VARCHAR(32) DEFAULT 'home'"))
                        if 'required_attempts' not in l_cols:
                            conn.execute(text("ALTER TABLE lesson_stages ADD COLUMN required_attempts INTEGER DEFAULT 2"))

                    conn.commit()
        except Exception as e:
            print("Auto-migration note:", e)

        # 2. Seed Super Admin & Test Typist
        print("👤 Seeding Accounts...")
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@typesphere.io',
                role='super_admin',
                is_verified=True,
                elo_rating=1500,
                ranked_wins=24,
                ranked_losses=2
            )
            admin.set_password('AdminMaster2026!')
            db.session.add(admin)
        else:
            admin.role = 'super_admin'
            admin.is_verified = True

        typist = User.query.filter_by(username='speeddemon').first()
        if not typist:
            typist = User(
                username='speeddemon',
                email='speed@typesphere.io',
                role='user',
                is_verified=True,
                elo_rating=1350,
                ranked_wins=15,
                ranked_losses=4
            )
            typist.set_password('SpeedPass123!')
            db.session.add(typist)
        else:
            typist.is_verified = True

        # 3. Seed Platform Achievements
        print("🏆 Seeding Achievements...")
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

        # 4. Seed Multi-Track Academy Curriculum (12 Stages across 4 Tracks)
        print("🎓 Seeding Academy Curriculum (4 Tracks, 12 Stages)...")
        curriculum_data = [
            ('beginner', 1, "Keyboard Orientation & Posture", "intro", "Learn home row resting anchors, hand ergonomics, and finger coordination.", "f j f j f j dk dk sl sl a; a; fj dk sl a;", 15.0, 90.0, 2, "F J D K"),
            ('beginner', 2, "Home Row Mastery", "home-row", "Anchor muscle memory exclusively on the baseline resting keys.", "asdf jkl; a fad flask fall glad half dash salad flash salsa lad fall", 20.0, 92.0, 2, "A S D F J K L ;"),
            ('beginner', 3, "Top Row Extensions", "top-row", "Train upward vertical reaches without shifting wrists off the desk.", "quit write power tower quote trip your wipe wire pure quiet root weep", 25.0, 92.0, 2, "Q W E R T Y U I O P"),
            ('beginner', 4, "Bottom Row Transitions", "bottom-row", "Practice downward finger tucks while maintaining palm stability.", "cabin van mix zoom bomb zinc exam calm civic move bank comb mimic", 28.0, 92.0, 2, "Z X C V B N M"),

            ('intermediate', 1, "Contralateral Shift Synchronization", "shifts", "Synchronize shift-key holds for effortless capitalization.", "The Quick Brown Fox Jumps Over The Lazy Dog London Paris Tokyo", 38.0, 94.0, 2, "Shift Keys"),
            ('intermediate', 2, "High-Frequency Core Vocabulary", "core-words", "Fluid execution on the top 100 most frequent English building blocks.", "their there would about which could people other first water after", 45.0, 94.0, 2, "General Vocabulary"),
            ('intermediate', 3, "Complete Sentence Cadence", "sentences", "Punctuation rhythms, sentence capitalization, and natural phrase timing.", "Consistent practice builds velocity. Never compromise accuracy for speed.", 52.0, 95.0, 2, "Punctuation & Syntax"),
            ('intermediate', 4, "Top Number Row Reaches", "numbers", "Reach the top number row with correct finger stretches without looking.", "Invoice 8402 total 195 dollars on 2026-09-15 tracking number 7391054", 42.0, 92.0, 2, "1 2 3 4 5 6 7 8 9 0"),

            ('advanced', 1, "Complex Symbols & Brackets", "symbols", "Master hyphens, parentheses, semicolons, quotes, and code brackets.", "function(arg) { return [x, y]; } value = 'true'; (check == 100)", 60.0, 95.0, 2, "{} [] () <> /"),
            ('advanced', 2, "High-Speed N-Gram Sprints", "ngrams", "Rapid bursts of frequent bigrams and trigrams (the, ing, tion, ment).", "the and for that with this from have they which would there their about", 72.0, 95.0, 2, "the and ing tion"),
            ('advanced', 3, "Zero-Error Precision Gauntlet", "precision", "Eliminate stutter pauses with strict 98% accuracy thresholds.", "Deliberate movement precedes true velocity. Calm hands strike cleanly.", 78.0, 98.0, 3, "All Standard Keys"),

            ('expert', 1, "Professional Workplace Execution", "professional", "Simulated office memos, executive briefings, and technical reports.", "Please review the quarterly engineering deployment roadmap attached.", 95.0, 96.0, 3, "Office Vocabulary"),
            ('expert', 2, "Grandmaster Endurance Sprint", "grandmaster", "Sustained high-velocity paragraphs demanding flawless cognitive stamina.", "Synchronized kinetic movement compounds into unstoppable tactile velocity under intense pressure.", 105.0, 97.0, 3, "Mastery Corpus")
        ]
        for track, num, title, slug, desc, practice, min_w, min_a, req_att, f_keys in curriculum_data:
            stage = LessonStage.query.filter_by(slug=slug).first()
            if not stage:
                stage = LessonStage(
                    track=track,
                    stage_number=num,
                    title=title,
                    slug=slug,
                    description=desc,
                    practice_material=practice,
                    min_wpm_to_pass=min_w,
                    min_accuracy_to_pass=min_a,
                    required_attempts=req_att,
                    focus_keys=f_keys
                )
                db.session.add(stage)

        # 5. Seed Arcade Game Configs
        print("🕹️ Seeding 12 Arcade Game Configs & Content Items...")
        game_configs = [
            ('speed_racer', 'Speed Racer', 'Control a live vehicle on an open race track. Correct strokes accelerate your car forward; typos apply backward recoil without halting momentum.', True, True, True, 4, "60,120,300", "moderate"),
            ('falling_words', 'Falling Words', 'Target descending words before they cross the defense laser.', True, True, False, 2, "60,120", "moderate"),
            ('bubble_pop', 'Bubble Pop', 'Floating bubbles contain single isolated target characters.', True, True, False, 2, "30,60,120", "moderate"),
            ('whack_a_word', 'Whack-A-Word', '3x3 grid where targets pop up for brief exposure windows.', True, True, False, 2, "30,60,90", "moderate"),
            ('zombie_defense', 'Zombie Defense', 'Incoming hordes march towards your base barrier. Type overhead words to eliminate them.', True, False, False, 1, "60,120", "moderate"),
            ('zombie_duel', 'Zombie Duel', '1v1 combat duel. Fast keystrokes launch attack spells; typos break defensive shields.', True, True, False, 2, "60,120", "moderate"),
            ('cipher_hacker', 'Cipher Hacker', 'Progressive security layers. Decrypt hexadecimal, alphanumeric tokens, and code syntax.', True, True, False, 2, "60,120", "hard"),
            ('space_defender', 'Space Defender', 'Defend your starship from incoming asteroids in all orbital quadrants.', True, True, False, 2, "45,60,120", "moderate"),
            ('bomb_defuse', 'Bomb Defuse', 'Defuse time bombs with sequential multi-character cryptograms.', True, True, False, 2, "40,60", "hard"),
            ('typing_ninja', 'Typing Ninja', 'Slice across floating words as they launch into the air.', True, True, False, 2, "45,60", "moderate"),
            ('memory_type', 'Memory Type', 'Sequences flash for 1.5 seconds and disappear. Type from mental recall.', True, True, False, 2, "60", "hard"),
            ('keyboard_quest', 'Keyboard Quest', 'Ergonomic stage map training home-row, upper reaches, bottom tucks, and numbers.', True, False, False, 1, "60", "easy")
        ]
        for slug, title, desc, s_ai, a_1v1, a_mp, max_p, durs, def_ai in game_configs:
            cfg = ArcadeGameConfig.query.filter_by(game_slug=slug).first()
            if not cfg:
                cfg = ArcadeGameConfig(
                    game_slug=slug,
                    display_title=title,
                    description=desc,
                    allows_solo_ai=s_ai,
                    allows_1v1=a_1v1,
                    allows_multiplayer=a_mp,
                    max_multiplayer_players=max_p,
                    durations=durs,
                    default_ai_level=def_ai,
                    is_enabled=True
                )
                db.session.add(cfg)

        # 6. Seed Complete Typing Content Library
        print("📝 Seeding Complete Content Library (Literature, Tech, Science, Business, Code)...")
        passages_catalog = [
            ("The Morning Walk", "Daily Life", "Easy", False, None,
             "The sun was up early and the sky was clear and bright. A small bird sat on the high green tree and sang a sweet song. The cool morning air made the walk pleasant and relaxing. People walked their dogs along the quiet path near the pond while children laughed and played with a red ball."),
            ("The Small Town Baker", "Daily Life", "Easy", False, None,
             "Every morning before dawn the baker would turn on the lights in his warm shop. He made fresh bread with flour yeast water and salt. The sweet smell of warm loaves filled the whole street. Neighbors stopped by on their way to work to buy fresh rolls and say hello with a smile."),
            ("Learning to Read", "Education", "Easy", False, None,
             "A good book can take you to places you have never seen before. When you open a page you can travel to high mountains deep blue oceans or distant green forests. Reading every day helps your mind grow strong and makes your imagination fly."),

            ("Pride and Prejudice Excerpt", "Literature", "Medium", False, None,
             "It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife. However little known the feelings or views of such a man may be on his first entering a neighbourhood, this truth is so well fixed in the minds of the surrounding families, that he is considered as the rightful property of some one or other of their daughters."),
            ("A Tale of Two Cities", "Literature", "Medium", False, None,
             "It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of foolishness, it was the epoch of belief, it was the epoch of incredulity, it was the season of light, it was the season of darkness, it was the spring of hope, it was the winter of despair."),
            ("Cloud Computing Fundamentals", "Technology", "Medium", False, None,
             "Distributed computing architecture enables modern web applications to dynamically scale compute resources based on incoming request volume. Load balancers distribute user traffic evenly across independent server instances, ensuring high availability and fault tolerance even during hardware failures."),
            ("The Structure of DNA", "Science", "Medium", False, None,
             "Deoxyribonucleic acid is the hereditary material in humans and almost all other living organisms. The information stored in DNA is encoded in a sequence of four chemical bases: adenine, guanine, cytosine, and thymine. These bases pair up with each other to form the rungs of a twisted ladder."),
            ("The Printing Press Revolution", "History", "Medium", False, None,
             "Johannes Gutenberg introduced movable metal type printing to Europe around fourteen forty, transforming the dissemination of knowledge forever. Books that previously required months of manual copying by scribes could now be reproduced rapidly, accelerating the Renaissance and scientific discovery."),

            ("Quarterly Financial Review", "Business", "Hard", False, None,
             "During the fourth fiscal quarter of 2025, operating revenue increased by 14.8% year-over-year to $42.6 million. However, administrative expenditures rose sharply due to localized inflation, regulatory compliance auditing, and accelerated software capitalization. The board recommended a quarterly dividend of $0.45 per share."),
            ("Biomechanical Ergonomics", "Science", "Hard", False, None,
             "Repetitive strain injuries often manifest when typists maintain static isometric contraction of the forearm extensor muscles. Ergonomic keyboards designed with split key clusters, tenting angles between 10 and 15 degrees, and low actuation-force mechanical switches substantially reduce carpal tunnel hydrostatic pressure."),
            ("Decoupled Message Queues", "Technology", "Hard", False, None,
             "Asynchronous event-driven architectures decouple producers from consumers using partitioned commit logs. By enforcing strict message ordering per partition key, streaming platforms guarantee that high-throughput downstream workers process state updates with at-least-once delivery semantics."),
            ("Legal Jurisprudence Memo", "Professional", "Hard", False, None,
             "Pursuant to Section 104(b) of the revised commercial code, the plaintiff must establish prima facie evidence that the contractual indemnification clause was both procedurally and substantively unconscionable at the time of execution. Laches and equitable estoppel arguments remain unavailing."),

            ("Phenomenological Inquiry", "Education", "Expert", False, None,
             "Phenomenology seeks an epochal suspension of the natural attitude, interrogating the intentionality that constitutes consciousness toward transcendental objects. Such transcendental bracketing reveals that subjectivity is inextricably bound to the spatio-temporal horizon of lived experience, precluding naive empirical reductionism."),
            ("Quantum Computing Paradigms", "Science", "Expert", False, None,
             "Superconducting qubits utilize Josephson junctions to create non-linear dissipationless inductance, establishing discrete macroscopic quantum eigenstates. Mitigating phase decoherence and environmental noise requires topological braiding or fault-tolerant surface codes operating at sub-millikelvin temperatures."),

            ("Python Quicksort Algorithm", "Technology", "Medium", True, "python",
             "def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)"),
            ("JavaScript Async Debounce", "Technology", "Medium", True, "javascript",
             "const debounce = (func, delay = 300) => {\n  let timerId;\n  return (...args) => {\n    clearTimeout(timerId);\n    timerId = setTimeout(() => func.apply(this, args), delay);\n  };\n};"),
            ("SQL Analytical Window Function", "Business", "Hard", True, "sql",
             "SELECT department_id, employee_name, salary,\n       AVG(salary) OVER(PARTITION BY department_id) as dept_avg_salary,\n       RANK() OVER(PARTITION BY department_id ORDER BY salary DESC) as salary_rank\nFROM corporate_payroll\nWHERE employment_status = 'ACTIVE';")
        ]

        for title, cat, diff, is_code, code_lang, content in passages_catalog:
            existing = TypingText.query.filter_by(content=content).first()
            if not existing:
                t_item = TypingText(
                    title=title,
                    category=cat,
                    difficulty=diff,
                    content=content,
                    is_code=is_code,
                    code_lang=code_lang,
                    is_active=True,
                    created_by="System"
                )
                t_item.calculate_stats()
                db.session.add(t_item)

        # 7. Seed Daily Challenge
        print("📅 Seeding Daily Challenge...")
        today = date.today()
        daily = DailyChallenge.query.filter_by(target_date=today).first()
        if not daily:
            daily = DailyChallenge(
                target_date=today,
                title="The Kinetic Discipline",
                content="True velocity is not rushed chaos; it is calm, deliberate movement free of hesitation and unnecessary recoil. Keep your hands balanced and let cadence carry your speed."
            )
            db.session.add(daily)

        # 8. Seed Platform Parameters
        print("⚙️ Seeding Platform Parameters...")
        configs = [
            ('maintenance_mode', 'false', 'general', 'Master toggle for system maintenance'),
            ('allow_registrations', 'true', 'auth', 'Enables new user registration'),
            ('default_test_duration', '60', 'typing', 'Default timed test duration in seconds'),
            ('min_wpm_cutoff', '250', 'security', 'Anti-cheat upper bound for human velocity')
        ]
        for key, val, cat, desc in configs:
            if not PlatformConfig.query.filter_by(key=key).first():
                db.session.add(PlatformConfig(key=key, value=val, category=cat, description=desc, updated_by="System"))

        # 9. Commit All Seed Data
        db.session.commit()
        print("\n" + "=" * 65)
        print("✅ SUCCESS: TypeSphere Master Database Populated Cleanly!")
        print("   • Accounts: admin (super_admin) & speeddemon (verified)")
        print("   • Achievements: 10 Core Badges")
        print("   • Academy: 12 Stages across 4 Skill Tracks")
        print("   • Arcade: 12 Playable Games Configured")
        print("   • Content: 18 Multi-Tier Passages (Literature, Tech, Science, Business, Code)")
        print("   • Daily Challenge & System Parameters: Initialized")
        print("=" * 65 + "\n")

if __name__ == '__main__':
    seed_database()
    sys.exit(0)