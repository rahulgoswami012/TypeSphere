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

    # Register all database models before create_all
    from app.models.user import User
    from app.models.typing import TypingTest, TypingText, TypingDNA
    from app.models.challenge import DailyChallenge, Achievement, UserAchievement
    from app.models.settings import UserSettings
    from app.models.feedback import ContactMessage, FeedbackItem, RatingReview, SiteSetting, Announcement
    from app.models.curriculum import LessonStage, UserLessonProgress
    from app.models.content import ContentItem, ExamTemplate
    from app.models.game import GameRecord
    from app.models.plan import UserSubscription

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()
        # Safe SQLite migrations
        try:
            with db.engine.connect() as conn:
                res = conn.execute(text("PRAGMA table_info(user_settings)"))
                cols = [row[1] for row in res.fetchall()]
                if cols and 'blind_mode' not in cols:
                    conn.execute(text("ALTER TABLE user_settings ADD COLUMN blind_mode BOOLEAN DEFAULT 1"))
                if cols and 'ghost_mode' not in cols:
                    conn.execute(text("ALTER TABLE user_settings ADD COLUMN ghost_mode BOOLEAN DEFAULT 0"))
                conn.commit()
        except Exception:
            pass

    # Register All Blueprints
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

    @app.route('/')
    def root_home():
        from app.routes.typing import test_page
        return test_page()

    return app