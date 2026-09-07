from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from app import db
from app.models.game import GameRecord, ArcadeLeaderboard
from app.models.arcade_content import ArcadeGameConfig
from app.services.arcade_content_engine import ArcadeContentEngine
from app.services.ai_typist_engine import AI_LEVEL_PROFILES

games_bp = Blueprint('games', __name__)

ARCADE_GAMES_METADATA = [
    {
        'slug': 'falling_words',
        'title': 'Falling Words',
        'badge': 'ARCADE CLASSIC',
        'category': 'Peripheral Vision & Speed',
        'icon': '☄️',
        'desc': 'Target descending words before they cross the defense laser. Higher waves test peripheral recognition.',
        'modes': ['Solo vs AI', '1v1 Duel', 'Multiplayer'],
        'skills': 'Reaction Time, Fast Recovery'
    },
    {
        'slug': 'speed_racer',
        'title': 'Speed Racer',
        'badge': 'CANVAS RACING',
        'category': 'Velocity & Nitro Streaks',
        'icon': '🏎️',
        'desc': 'Throttle a live racecar on a 5-lane circuit. Sustained streaks trigger nitro acceleration.',
        'modes': ['Solo vs AI', '1v1 Duel', 'Multiplayer'],
        'skills': 'Burst Cadence, Sustained Velocity'
    },
    {
        'slug': 'bubble_pop',
        'title': 'Bubble Pop',
        'badge': 'KEYBOARD DRILL',
        'category': 'Single Key Mastery',
        'icon': '🫧',
        'desc': 'Float bubbles contain single isolated targets: lowercase, capitals, numbers, and symbols.',
        'modes': ['Solo vs AI', '1v1 Challenge'],
        'skills': 'Finger Independence, Reach Precision'
    },
    {
        'slug': 'whack_a_word',
        'title': 'Whack-A-Word',
        'badge': 'REACTION GRID',
        'category': 'Spatial Recognition',
        'icon': '🔨',
        'desc': '3x3 grid where targets pop up for 1.8 seconds. Type the active position before it retracts.',
        'modes': ['Solo vs AI', '1v1 Duel'],
        'skills': 'Spatial Cognition, Fast Reflexes'
    },
    {
        'slug': 'zombie_duel',
        'title': 'Zombie Duel',
        'badge': '1V1 COMBAT',
        'category': 'Two-Player HP Battle',
        'icon': '🧟',
        'desc': 'Head-to-head combat. Accurate words launch offensive strikes; errors damage your defensive barrier.',
        'modes': ['Solo vs AI', '1v1 Matchmaking'],
        'skills': 'Stress Resilience, Error Restraint'
    },
    {
        'slug': 'word_blitz',
        'title': 'Word Blitz',
        'badge': 'TIME TRIAL',
        'category': '60s High-Intensity Burst',
        'icon': '⚡',
        'desc': 'High-octane sprint. Words flash one by one with combo multipliers for unbroken accuracy.',
        'modes': ['Solo vs AI', '1v1 Duel', 'Multiplayer'],
        'skills': 'Sprint Speed, Flow State'
    },
    {
        'slug': 'cipher_hacker',
        'title': 'Cipher Hacker',
        'badge': 'CYBER INTRUSION',
        'category': 'Programming & Hex Code',
        'icon': '💻',
        'desc': 'Progressive security layers. Decrypt hexadecimal, alphanumeric tokens, and code syntax.',
        'modes': ['Solo vs AI', '1v1 Race'],
        'skills': 'Symbol Dexterity, Syntax Typing'
    },
    {
        'slug': 'space_defender',
        'title': 'Space Defender',
        'badge': 'NEW',
        'category': 'Directional Asteroid Defense',
        'icon': '🚀',
        'desc': 'Defend your starship from incoming asteroids in all quadrants. Lock on and eliminate orbital debris.',
        'modes': ['Solo vs AI', '1v1 Duel'],
        'skills': 'Peripheral Scanning, Precision'
    },
    {
        'slug': 'bomb_defuse',
        'title': 'Bomb Defuse',
        'badge': 'NEW',
        'category': 'High-Pressure Code Cracking',
        'icon': '💣',
        'desc': 'Defuse time bombs with sequential multi-stage passcodes. A single typo reduces countdown time.',
        'modes': ['Solo vs Timer', '1v1 Duel'],
        'skills': 'Zero-Error Precision, Coolness'
    },
    {
        'slug': 'typing_ninja',
        'title': 'Typing Ninja',
        'badge': 'NEW',
        'category': 'Combos & Slicing Mechanics',
        'icon': '🥷',
        'desc': 'Slice across floating words as they launch into the air. Chain multiple words together for combos.',
        'modes': ['Solo vs AI', '1v1 Challenge'],
        'skills': 'Rhythmic Accuracy, Momentum'
    },
    {
        'slug': 'memory_type',
        'title': 'Memory Type',
        'badge': 'NEW',
        'category': 'Cognitive Working Memory',
        'icon': '🧠',
        'desc': 'Sequences flash for 1.5 seconds and disappear. Type the sequence completely from mental recall.',
        'modes': ['Solo vs AI', '1v1 Duel'],
        'skills': 'Visual Memory, Blind Execution'
    },
    {
        'slug': 'keyboard_quest',
        'title': 'Keyboard Quest',
        'badge': 'NEW',
        'category': 'Biomechanic Row Progression',
        'icon': '🗺️',
        'desc': 'Ergonomic stage map training home-row, upper reaches, bottom tucks, and numeric stretches.',
        'modes': ['Solo Quest', 'Stage Duel'],
        'skills': 'Ergonomic Technique, Reach Memory'
    }
]

@games_bp.route('/')
def index():
    user_high_scores = {}
    if current_user.is_authenticated:
        records = ArcadeLeaderboard.query.filter_by(user_id=current_user.id).all()
        user_high_scores = {r.game_mode: r.high_score for r in records}
        
    return render_template(
        'games/index.html', 
        games=ARCADE_GAMES_METADATA,
        high_scores=user_high_scores
    )

@games_bp.route('/play/<game_slug>')
def play_arena(game_slug):
    game_info = next((g for g in ARCADE_GAMES_METADATA if g['slug'] == game_slug), None)
    if not game_info:
        return render_template('games/index.html', games=ARCADE_GAMES_METADATA)

    # Pre-fetch user weak keys for target practice options
    user_weak_keys = []
    if current_user.is_authenticated and current_user.dna_profile:
        stats = current_user.dna_profile.get_key_stats()
        user_weak_keys = [k.upper() for k, v in stats.items() if v.get('total', 0) >= 4 and (v.get('errors', 0)/v['total']) > 0.08][:5]

    return render_template(
        'games/arena.html',
        game=game_info,
        ai_levels=['Beginner', 'Intermediate', 'Advanced', 'Expert', 'Adaptive'],
        weak_keys=user_weak_keys
    )

@games_bp.route('/api/submit-score', methods=['POST'])
def submit_score():
    data = request.get_json(force=True) or {}
    game_mode = data.get('game_mode', 'arcade')
    score = int(data.get('score', 0))
    net_wpm = float(data.get('net_wpm', 0.0))
    accuracy = float(data.get('accuracy', 100.0))
    errors = int(data.get('errors', 0))
    highest_combo = int(data.get('highest_combo', 0))
    reaction_ms = float(data.get('reaction_ms', 0.0))
    duration = float(data.get('duration', 0.0))

    record = GameRecord(
        user_id=current_user.id if current_user.is_authenticated else None,
        game_mode=game_mode,
        play_type=data.get('play_type', 'solo_ai'),
        score=score,
        net_wpm=net_wpm,
        accuracy=accuracy,
        errors=errors,
        highest_combo=highest_combo,
        average_reaction_ms=reaction_ms,
        duration_seconds=duration,
        meta_stats_json=data.get('meta_json', '{}')
    )
    db.session.add(record)

    is_new_pb = False
    if current_user.is_authenticated:
        lb = ArcadeLeaderboard.query.filter_by(user_id=current_user.id, game_mode=game_mode).first()
        if not lb:
            lb = ArcadeLeaderboard(user_id=current_user.id, game_mode=game_mode, high_score=score, best_wpm=net_wpm, best_accuracy=accuracy)
            db.session.add(lb)
            is_new_pb = True
        else:
            if score > lb.high_score:
                lb.high_score = score
                is_new_pb = True
            if net_wpm > lb.best_wpm: lb.best_wpm = net_wpm
            if accuracy > lb.best_accuracy: lb.best_accuracy = accuracy
            lb.updated_at = db.func.now()

    db.session.commit()
    return jsonify({'success': True, 'is_pb': is_new_pb, 'score': score})