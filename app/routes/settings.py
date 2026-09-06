from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from app import db
from app.models.settings import UserSettings

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/')
def index():
    user_settings = None
    if current_user.is_authenticated:
        user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
        if not user_settings:
            user_settings = UserSettings(user_id=current_user.id)
            db.session.add(user_settings)
            db.session.commit()
    return render_template('settings/index.html', settings=user_settings)

@settings_bp.route('/api/save', methods=['POST'])
def save_settings():
    data = request.get_json(force=True) or {}
    if current_user.is_authenticated:
        settings = UserSettings.query.filter_by(user_id=current_user.id).first()
        if not settings:
            settings = UserSettings(user_id=current_user.id)
            db.session.add(settings)

        settings.theme = data.get('theme', 'dark')
        settings.font_family = data.get('font_family', 'JetBrains Mono')
        settings.font_size = int(data.get('font_size', 20))
        settings.caret_style = data.get('caret_style', 'smooth')
        settings.sound_enabled = bool(data.get('sound_enabled', True))
        settings.sound_theme = data.get('sound_theme', 'mechanical')
        settings.show_keyboard = bool(data.get('show_keyboard', True))
        db.session.commit()
        return jsonify({'success': True, 'persisted': 'database'})

    return jsonify({'success': True, 'persisted': 'local'})