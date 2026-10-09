from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_socketio import SocketIO
from sqlalchemy import text, inspect
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')


def apply_universal_schema_patches(engine):
    """
    Non-destructive universal schema patcher for both SQLite and PostgreSQL.
    Inspects existing tables and dynamically adds any missing columns.
    Purges accidental operator IP lockouts on startup.
    """
    try:
        with engine.connect() as conn:
            inspector = inspect(conn)
            existing_tables = set(inspector.get_table_names())

            is_pg = 'postgres' in str(engine.url).lower()
            b_true = "TRUE" if is_pg else "1"
            b_false = "FALSE" if is_pg else "0"
            dt_type = "TIMESTAMP" if is_pg else "DATETIME"

            # 1. Lift any accidental operator lockout by purging test blocks
            if 'blocked_ips' in existing_tables:
                try:
                    conn.execute(text("DELETE FROM blocked_ips"))
                    conn.commit()
                except Exception:
                    conn.rollback()

            # 2. Table patch definitions
            patch_manifest = [
                ('users', [
                    ('callsign', "VARCHAR(32)"),
                    ('flight_squadron', "VARCHAR(64) DEFAULT 'Vanguard Flight Division'"),
                    ('avatar_flight_badge', "VARCHAR(32) DEFAULT 'apex_wings'"),
                    ('ranked_draws', "INTEGER DEFAULT 0"),
                    ('is_verified', f"BOOLEAN DEFAULT {b_true}"),
                    ('elo_rating', "INTEGER DEFAULT 1000"),
                    ('ranked_wins', "INTEGER DEFAULT 0"),
                    ('ranked_losses', "INTEGER DEFAULT 0"),
                    ('is_suspended', f"BOOLEAN DEFAULT {b_false}"),
                    ('is_banned', f"BOOLEAN DEFAULT {b_false}"),
                    ('status_reason', "VARCHAR(255)"),
                    ('last_active', dt_type)
                ]),
                ('user_settings', [
                    ('typing_area_style', "VARCHAR(32) DEFAULT 'modern'"),
                    ('keyboard_display', "VARCHAR(32) DEFAULT 'heatmap'"),
                    ('reduce_motion', f"BOOLEAN DEFAULT {b_false}"),
                    ('confidence_mode', f"BOOLEAN DEFAULT {b_false}"),
                    ('game_sound_volume', "FLOAT DEFAULT 0.7"),
                    ('game_sound_theme', "VARCHAR(32) DEFAULT 'retro'"),
                    ('blind_mode', f"BOOLEAN DEFAULT {b_true}"),
                    ('ghost_mode', f"BOOLEAN DEFAULT {b_false}"),
                    ('default_duration', "INTEGER DEFAULT 60"),
                    ('default_content', "VARCHAR(32) DEFAULT 'words'"),
                    ('default_level', "VARCHAR(32) DEFAULT 'moderate'"),
                    ('sound_volume', "FLOAT DEFAULT 0.7")
                ]),
                ('typing_tests', [
                    ('total_mistakes', "INTEGER DEFAULT 0"),
                    ('uncorrected_errors', "INTEGER DEFAULT 0"),
                    ('time_of_day_ist', "INTEGER"),
                    ('is_ranked', f"BOOLEAN DEFAULT {b_false}"),
                    ('content_category', "VARCHAR(64) DEFAULT 'General'"),
                    ('difficulty', "VARCHAR(32) DEFAULT 'moderate'")
                ]),
                ('arcade_game_configs', [
                    ('display_order', "INTEGER DEFAULT 1")
                ]),
                ('arcade_content_items', [
                    ('is_active', f"BOOLEAN DEFAULT {b_true}"),
                    ('word_length', "INTEGER DEFAULT 5"),
                    ('category', "VARCHAR(50) DEFAULT 'general'"),
                    ('difficulty', "VARCHAR(20) DEFAULT 'moderate'"),
                    ('associated_keys', "VARCHAR(64)")
                ]),
                ('lesson_stages', [
                    ('track', "VARCHAR(32) DEFAULT 'beginner'"),
                    ('hand_position_hint', "VARCHAR(128)"),
                    ('keyboard_row', "VARCHAR(32) DEFAULT 'home'"),
                    ('required_attempts', "INTEGER DEFAULT 2")
                ]),
                ('typing_texts', [
                    ('title', "VARCHAR(160) DEFAULT 'Passage'"),
                    ('slug', "VARCHAR(180)"),
                    ('language', "VARCHAR(32) DEFAULT 'english'"),
                    ('passage_type', "VARCHAR(32) DEFAULT 'paragraph'"),
                    ('status', "VARCHAR(20) DEFAULT 'published'"),
                    ('purpose', "VARCHAR(255) DEFAULT 'general_practice'"),
                    ('exam_profile', "VARCHAR(64)"),
                    ('exam_style', "VARCHAR(64)"),
                    ('region', "VARCHAR(64) DEFAULT 'India'"),
                    ('word_count', "INTEGER DEFAULT 0"),
                    ('character_count', "INTEGER DEFAULT 0"),
                    ('character_count_no_spaces', "INTEGER DEFAULT 0"),
                    ('sentence_count', "INTEGER DEFAULT 0"),
                    ('paragraph_count', "INTEGER DEFAULT 1"),
                    ('avg_word_length', "FLOAT DEFAULT 0.0"),
                    ('complexity_score', "FLOAT DEFAULT 1.0"),
                    ('recommended_duration', "INTEGER DEFAULT 60"),
                    ('min_duration', "INTEGER DEFAULT 15"),
                    ('max_duration', "INTEGER DEFAULT 1200"),
                    ('visibility', "VARCHAR(32) DEFAULT 'everyone'"),
                    ('is_active', f"BOOLEAN DEFAULT {b_true}"),
                    ('is_featured', f"BOOLEAN DEFAULT {b_false}"),
                    ('allow_random', f"BOOLEAN DEFAULT {b_true}"),
                    ('allow_multiplayer', f"BOOLEAN DEFAULT {b_true}"),
                    ('source_type', "VARCHAR(64) DEFAULT 'original_practice'"),
                    ('source_url', "VARCHAR(255)"),
                    ('is_code', f"BOOLEAN DEFAULT {b_false}"),
                    ('code_lang', "VARCHAR(32)"),
                    ('times_used', "INTEGER DEFAULT 0"),
                    ('unique_users', "INTEGER DEFAULT 0"),
                    ('avg_wpm', "FLOAT DEFAULT 0.0"),
                    ('avg_accuracy', "FLOAT DEFAULT 0.0"),
                    ('report_count', "INTEGER DEFAULT 0"),
                    ('health_score', "INTEGER DEFAULT 100"),
                    ('created_by', "VARCHAR(64) DEFAULT 'System'"),
                    ('updated_by', "VARCHAR(64)"),
                    ('published_at', dt_type)
                ])
            ]

            for table_name, columns_to_check in patch_manifest:
                if table_name in existing_tables:
                    current_columns = {col['name'] for col in inspector.get_columns(table_name)}
                    for col_name, col_def in columns_to_check:
                        if col_name not in current_columns:
                            try:
                                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}"))
                                conn.commit()
                            except Exception:
                                conn.rollback()
    except Exception:
        pass


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

    # Universal schema creation & dialect-agnostic column patching
    with app.app_context():
        db.create_all()
        apply_universal_schema_patches(db.engine)

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