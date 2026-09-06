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

    from app.models.user import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Automatic SQLite Column Migration Guard for V2.0 Ranked Fields
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                res = conn.execute(text("PRAGMA table_info(users)"))
                cols = [row[1] for row in res.fetchall()]
                if cols and 'is_verified' not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 1"))
                if cols and 'elo_rating' not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN elo_rating INTEGER DEFAULT 1000"))
                if cols and 'ranked_wins' not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN ranked_wins INTEGER DEFAULT 0"))
                if cols and 'ranked_losses' not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN ranked_losses INTEGER DEFAULT 0"))
                conn.commit()
        except Exception as e:
            pass

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.typing import typing_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.leaderboard import leaderboard_bp
    from app.routes.challenges import challenges_bp
    from app.routes.multiplayer import multiplayer_bp
    from app.routes.admin import admin_bp
    from app.routes.settings import settings_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(typing_bp, url_prefix='/typing')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(leaderboard_bp, url_prefix='/leaderboard')
    app.register_blueprint(challenges_bp, url_prefix='/challenges')
    app.register_blueprint(multiplayer_bp, url_prefix='/multiplayer')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(settings_bp, url_prefix='/settings')

    @app.route('/')
    def index():
        from flask import redirect, url_for
        return redirect(url_for('typing.test_page'))

    return app