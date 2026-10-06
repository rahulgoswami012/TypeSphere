from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_socketio import SocketIO
from sqlalchemy import text
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Register models before schema initialization
    from app.models.user import User
    from app.models.typing import (
        TypingTest, TypingText, TypingDNA,
        PassageTag, PassageCollection, PassageReport,
        passage_tags, passage_collections
    )
    from app.models.challenge import DailyChallenge, Achievement, UserAchievement
    from app.models.settings import UserSettings
    from app.models.feedback import ContactMessage, FeedbackItem, RatingReview, SiteSetting, Announcement
    from app.models.curriculum import LessonStage, UserLessonProgress
    from app.models.content import ContentItem, ExamTemplate
    from app.models.game import GameRecord, ArcadeLeaderboard
    from app.models.arcade_content import ArcadeContentItem, ArcadeGameConfig
    from app.models.plan import UserSubscription
    from app.models.admin import (
        RolePermission, AdminAuditLog, UserActivity, VisitorTraffic,
        SecurityEvent, PlatformConfig, Permission, CustomRole,
        role_permissions, user_roles, BlockedIP, FeatureFlag,
        SiteNavigationItem
    )

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Capability-based access control context processor
    from app.services.access_control import inject_capabilities
    app.context_processor(inject_capabilities)

    # Resilient auto-patchers for local SQLite & production PostgreSQL
    with app.app_context():
        db.create_all()
        try:
            with db.engine.connect() as conn:
                # 1. Patch users table with Pilot Identity attributes
                res = conn.execute(text("PRAGMA table_info(users)"))
                u_cols = {row[1] for row in res.fetchall()}
                if u_cols:
                    if 'callsign' not in u_cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN callsign VARCHAR(32)"))
                    if 'flight_squadron' not in u_cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN flight_squadron VARCHAR(64) DEFAULT 'Vanguard Flight Division'"))
                    if 'avatar_flight_badge' not in u_cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN avatar_flight_badge VARCHAR(32) DEFAULT 'apex_wings'"))
                    if 'ranked_draws' not in u_cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN ranked_draws INTEGER DEFAULT 0"))

                # 2. Patch user_settings table with Cockpit preferences
                res = conn.execute(text("PRAGMA table_info(user_settings)"))
                s_cols = {row[1] for row in res.fetchall()}
                if s_cols:
                    patches = [
                        ('typing_area_style', "VARCHAR(32) DEFAULT 'modern'"),
                        ('keyboard_display', "VARCHAR(32) DEFAULT 'heatmap'"),
                        ('reduce_motion', "BOOLEAN DEFAULT 0"),
                        ('confidence_mode', "BOOLEAN DEFAULT 0"),
                        ('game_sound_volume', "FLOAT DEFAULT 0.7"),
                        ('game_sound_theme', "VARCHAR(32) DEFAULT 'retro'"),
                        ('blind_mode', "BOOLEAN DEFAULT 1"),
                        ('ghost_mode', "BOOLEAN DEFAULT 0")
                    ]
                    for col_name, col_def in patches:
                        if col_name not in s_cols:
                            conn.execute(text(f"ALTER TABLE user_settings ADD COLUMN {col_name} {col_def}"))

                # 3. Patch typing_tests table
                res = conn.execute(text("PRAGMA table_info(typing_tests)"))
                t_cols = {row[1] for row in res.fetchall()}
                if t_cols:
                    if 'total_mistakes' not in t_cols:
                        conn.execute(text("ALTER TABLE typing_tests ADD COLUMN total_mistakes INTEGER DEFAULT 0"))
                    if 'uncorrected_errors' not in t_cols:
                        conn.execute(text("ALTER TABLE typing_tests ADD COLUMN uncorrected_errors INTEGER DEFAULT 0"))
                    if 'time_of_day_ist' not in t_cols:
                        conn.execute(text("ALTER TABLE typing_tests ADD COLUMN time_of_day_ist INTEGER"))

                # 4. Patch arcade_game_configs with display_order
                res = conn.execute(text("PRAGMA table_info(arcade_game_configs)"))
                ag_cols = {row[1] for row in res.fetchall()}
                if ag_cols:
                    if 'display_order' not in ag_cols:
                        conn.execute(text("ALTER TABLE arcade_game_configs ADD COLUMN display_order INTEGER DEFAULT 1"))

                # 5. Patch typing_texts table with multi-tier classification & rules
                res = conn.execute(text("PRAGMA table_info(typing_texts)"))
                txt_cols = {row[1] for row in res.fetchall()}
                if txt_cols:
                    text_patches = [
                        ('slug', "VARCHAR(180)"),
                        ('passage_type', "VARCHAR(32) DEFAULT 'paragraph'"),
                        ('status', "VARCHAR(20) DEFAULT 'published'"),
                        ('purpose', "VARCHAR(255) DEFAULT 'general_practice'"),
                        ('exam_profile', "VARCHAR(64)"),
                        ('exam_style', "VARCHAR(64)"),
                        ('region', "VARCHAR(64) DEFAULT 'India'"),
                        ('character_count_no_spaces', "INTEGER DEFAULT 0"),
                        ('sentence_count', "INTEGER DEFAULT 0"),
                        ('paragraph_count', "INTEGER DEFAULT 1"),
                        ('avg_word_length', "FLOAT DEFAULT 0.0"),
                        ('recommended_duration', "INTEGER DEFAULT 60"),
                        ('min_duration', "INTEGER DEFAULT 15"),
                        ('max_duration', "INTEGER DEFAULT 1200"),
                        ('visibility', "VARCHAR(32) DEFAULT 'everyone'"),
                        ('is_featured', "BOOLEAN DEFAULT 0"),
                        ('allow_random', "BOOLEAN DEFAULT 1"),
                        ('allow_multiplayer', "BOOLEAN DEFAULT 1"),
                        ('source_type', "VARCHAR(64) DEFAULT 'original_practice'"),
                        ('source_url', "VARCHAR(255)"),
                        ('times_used', "INTEGER DEFAULT 0"),
                        ('unique_users', "INTEGER DEFAULT 0"),
                        ('avg_wpm', "FLOAT DEFAULT 0.0"),
                        ('avg_accuracy', "FLOAT DEFAULT 0.0"),
                        ('report_count', "INTEGER DEFAULT 0"),
                        ('health_score', "INTEGER DEFAULT 100"),
                        ('published_at', "DATETIME")
                    ]
                    for col_name, col_def in text_patches:
                        if col_name not in txt_cols:
                            conn.execute(text(f"ALTER TABLE typing_texts ADD COLUMN {col_name} {col_def}"))

                conn.commit()
        except Exception:
            pass

        # Seed canonical system permissions and default navigation
        from app.services.admin_security import ensure_permissions_seeded, ensure_navigation_seeded
        ensure_permissions_seeded()
        ensure_navigation_seeded()

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.typing import typing_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.leaderboard import leaderboard_bp
    from app.routes.challenges import challenges_bp
    from app.routes.multiplayer import multiplayer_bp
    from app.routes.admin import admin_bp
    from app.routes.settings import settings_bp
    from app.routes.feedback import feedback_bp
    from app.routes.learn import learn_bp
    from app.routes.games import games_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(typing_bp, url_prefix='/typing')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(leaderboard_bp, url_prefix='/leaderboard')
    app.register_blueprint(challenges_bp, url_prefix='/challenges')
    app.register_blueprint(multiplayer_bp, url_prefix='/multiplayer')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(feedback_bp, url_prefix='/feedback')
    app.register_blueprint(learn_bp, url_prefix='/learn')
    app.register_blueprint(games_bp, url_prefix='/games')

    from app.services.admin_security import capture_traffic
    capture_traffic(app)

    from app.services.game_socket_engine import register_arcade_socket_events
    register_arcade_socket_events()

    @app.route('/')
    def root_home():
        from app.routes.typing import test_page
        return test_page()

    return app