from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from app import db
from app.models.game import GameRecord

games_bp = Blueprint('games', __name__)

@games_bp.route('/')
def index():
    user_records = []
    if current_user.is_authenticated:
        user_records = GameRecord.query.filter_by(user_id=current_user.id).order_by(GameRecord.score.desc()).limit(8).all()
    return render_template('games/index.html', records=user_records)

@games_bp.route('/falling-words')
def falling_words():
    return render_template('games/falling_words.html')

@games_bp.route('/speed-racer')
def speed_racer():
    return render_template('games/speed_racer.html')

@games_bp.route('/bubble-pop')
def bubble_pop():
    return render_template('games/bubble_pop.html')

@games_bp.route('/whack-a-word')
def whack_a_word():
    return render_template('games/whack_a_word.html')

@games_bp.route('/zombie-outbreak')
def zombie_outbreak():
    return render_template('games/zombie_outbreak.html')

@games_bp.route('/word-blitz')
def word_blitz():
    return render_template('games/word_blitz.html')

@games_bp.route('/cipher-hacker')
def cipher_hacker():
    return render_template('games/cipher_hacker.html')

@games_bp.route('/api/record-score', methods=['POST'])
def record_score():
    data = request.get_json(force=True) or {}
    record = GameRecord(
        user_id=current_user.id if current_user.is_authenticated else None,
        game_mode=data.get('game_mode', 'arcade'),
        score=int(data.get('score', 0)),
        words_typed=int(data.get('words_typed', 0)),
        accuracy=float(data.get('accuracy', 100.0)),
        duration_seconds=float(data.get('duration_seconds', 0.0))
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({'success': True, 'record_id': record.id})