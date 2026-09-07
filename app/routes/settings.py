from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from app import db
from app.models.settings import UserSettings

settings_bp = Blueprint('settings', __name__)

DEFAULT_SETTINGS = {
    'theme': 'dark',
    'font_family': 'JetBrains Mono',
    'font_size': 22,
    'caret_style': 'smooth',
    'sound_enabled': True,
    'sound_theme': 'mechanical',
    'sound_volume': 0.7,
    'show_keyboard': True,
    'default_duration': 60,
    'default_content': 'words',
    'default_level': 'moderate',
    'blind_mode': True,   # Default: ON
    'ghost_mode': False   # Default: OFF
}

@settings_bp.route('/')
def index():
    user_settings = None
    if current_user.is_authenticated:
        user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
        if not user_settings:
            user_settings = UserSettings(user_id=current_user.id)
            db.session.add(user_settings)
            db.session.commit()
    return render_template('settings/index.html', settings=user_settings, defaults=DEFAULT_SETTINGS)

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
        settings.font_size = int(data.get('font_size', 22))
        settings.caret_style = data.get('caret_style', 'smooth')
        settings.sound_enabled = bool(data.get('sound_enabled', True))
        settings.sound_theme = data.get('sound_theme', 'mechanical')
        settings.sound_volume = float(data.get('sound_volume', 0.7))
        settings.show_keyboard = bool(data.get('show_keyboard', True))
        
        settings.default_duration = int(data.get('default_duration', 60))
        settings.default_content = data.get('default_content', 'words')
        settings.default_level = data.get('default_level', 'moderate')
        settings.blind_mode = bool(data.get('blind_mode', True))
        settings.ghost_mode = bool(data.get('ghost_mode', False))
        
        db.session.commit()
        return jsonify({'success': True, 'scope': 'user_profile'})

    return jsonify({'success': True, 'scope': 'anonymous_session'})

@settings_bp.route('/api/defaults')
def get_defaults():
    return jsonify({'defaults': DEFAULT_SETTINGS})

@settings_bp.route('/api/reset-defaults', methods=['POST'])
def reset_to_defaults():
    if current_user.is_authenticated:
        settings = UserSettings.query.filter_by(user_id=current_user.id).first()
        if settings:
            for k, v in DEFAULT_SETTINGS.items():
                setattr(settings, k, v)
            db.session.commit()
    return jsonify({'success': True, 'defaults': DEFAULT_SETTINGS})