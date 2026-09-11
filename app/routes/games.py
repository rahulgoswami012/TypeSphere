from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from app import db
from app.models.game import GameRecord, ArcadeLeaderboard
from app.services.arcade_content_engine import ArcadeContentEngine
from app.models.typing import TypingDNA

games_bp = Blueprint('games', __name__)

ARCADE_MASTER_REGISTRY = [
    {
        'slug': 'speed_racer',
        'title': 'Speed Racer',
        'badge': 'REAL CAR PHYSICS',
        'icon': '🏎️',
        'category': 'Momentum & Recoil Sprint',
        'summary': 'Control a live vehicle on an open race track. Correct strokes accelerate your car forward; typos apply backward recoil without halting momentum.',
        'win_condition': 'Cross the finish line first or cover the furthest distance before timer expires.',
        'lose_condition': 'Opponent crosses the finish line ahead of you or covers greater distance.',
        'supports': ['Solo vs AI', '1v1 Duel', 'Multiplayer'],
        'default_objective': 'distance',
        'objective_options': [
            {'label': '300m Sprint', 'val': '300'},
            {'label': '500m Grand Prix', 'val': '500'},
            {'label': '1000m Marathon', 'val': '1000'}
        ]
    },
    {
        'slug': 'falling_words',
        'title': 'Falling Words',
        'badge': 'GRAVITY DEFENSE',
        'icon': '☄️',
        'category': 'Target Locking & Peripheral Vision',
        'summary': 'Words descend with accelerating gravitational velocity. Target lock descending phrases before they touch the defense barrier.',
        'win_condition': 'Survive the selected flight duration with defense integrity intact.',
        'lose_condition': 'Lose all lives before the timer runs out.',
        'supports': ['Solo vs AI', '1v1 Duel'],
        'default_objective': 'timed',
        'objective_options': [
            {'label': '30 Seconds', 'val': '30'},
            {'label': '45 Seconds', 'val': '45'},
            {'label': '60 Seconds (1 Min)', 'val': '60'},
            {'label': '120 Seconds (2 Min)', 'val': '120'},
            {'label': '300 Seconds (5 Min)', 'val': '300'}
        ]
    },
    {
        'slug': 'bubble_pop',
        'title': 'Bubble Pop',
        'badge': 'ISOLATED TARGETS',
        'icon': '🫧',
        'category': 'Single-Key Tactile Precision',
        'summary': 'Floating bubbles hold isolated target characters. Pop targets before they hit the ceiling barrier.',
        'win_condition': 'Pop required targets with highest score and unbroken combos.',
        'lose_condition': 'Allow 3 bubbles to burst against ceiling line.',
        'supports': ['Solo vs AI', '1v1 Challenge'],
        'default_objective': 'timed',
        'objective_options': [
            {'label': '30 Seconds', 'val': '30'},
            {'label': '60 Seconds', 'val': '60'},
            {'label': '120 Seconds', 'val': '120'}
        ]
    },
    {
        'slug': 'whack_a_word',
        'title': 'Whack-A-Word',
        'badge': 'REACTION GRID',
        'icon': '🔨',
        'category': 'Spatial Reaction Latency',
        'summary': 'Targets emerge across a 3x3 reaction grid with calibrated exposure times. Strike the active target before it retracts into the bunker.',
        'win_condition': 'Score higher points by striking targets within the millisecond window.',
        'lose_condition': 'Exhaust all 5 hammer attempts or score lower than opponent.',
        'supports': ['Solo vs AI', '1v1 Challenge'],
        'default_objective': 'timed',
        'objective_options': [
            {'label': '30 Seconds', 'val': '30'},
            {'label': '60 Seconds', 'val': '60'},
            {'label': '90 Seconds', 'val': '90'}
        ]
    },
    {
        'slug': 'zombie_defense',
        'title': 'Zombie Defense',
        'badge': 'BASE SURVIVAL',
        'icon': '🧟‍♂️',
        'category': 'Perimeter Defense',
        'summary': 'Incoming hordes march towards your fortified base. Type overhead words to discharge defensive turrets.',
        'win_condition': 'Survive the full session duration with base barrier intact.',
        'lose_condition': 'Zombies breach the perimeter and reduce base health to 0%.',
        'supports': ['Solo vs AI', 'Co-op Score Duel'],
        'default_objective': 'timed',
        'objective_options': [
            {'label': '45 Seconds', 'val': '45'},
            {'label': '60 Seconds (1 Min)', 'val': '60'},
            {'label': '120 Seconds (2 Min)', 'val': '120'},
            {'label': '300 Seconds (5 Min)', 'val': '300'}
        ]
    },
    {
        'slug': 'zombie_duel',
        'title': 'Zombie Duel',
        'badge': '1V1 HP COMBAT',
        'icon': '⚔️',
        'category': 'Two-Player Health Combat',
        'summary': 'Head-to-head combat duel. Fast keystrokes launch attack projectiles; typos break defensive shields and trigger recoil damage.',
        'win_condition': 'Reduce opponent combat health to 0 HP.',
        'lose_condition': 'Your combat health drops to 0 HP first.',
        'supports': ['Solo vs AI', '1v1 Challenge'],
        'default_objective': 'knockout',
        'objective_options': [
            {'label': 'Standard 100 HP Duel', 'val': '100'},
            {'label': 'Hardcore 50 HP Sudden Death', 'val': '50'}
        ]
    },
    {
        'slug': 'cipher_hacker',
        'title': 'Cipher Hacker',
        'badge': 'LAYER BREACH',
        'icon': '💻',
        'category': 'Progressive Security Architecture',
        'summary': 'Decrypt layered cybersecurity defenses: from hex dumps to complex syntax tokens. Advance through security clearances.',
        'win_condition': 'Breach all security layers before the firewall lockdown countdown concludes.',
        'lose_condition': 'Timer expires before root access decryption.',
        'supports': ['Solo vs AI', '1v1 Race'],
        'default_objective': 'layers',
        'objective_options': [
            {'label': '3 Security Layers', 'val': '3'},
            {'label': '4 Security Layers (Root Access)', 'val': '4'}
        ]
    },
    {
        'slug': 'space_defender',
        'title': 'Space Defender',
        'badge': 'ORBITAL GRID',
        'icon': '🚀',
        'category': 'Orbital Trajectory Defense',
        'summary': 'Debris and drones converge on your starship across 360 degrees. Acquire target locks and neutralize orbital threats.',
        'win_condition': 'Survive orbital debris impacts for the full flight duration.',
        'lose_condition': 'Ship shields collapse from debris impacts.',
        'supports': ['Solo vs AI', '1v1 Duel'],
        'default_objective': 'timed',
        'objective_options': [
            {'label': '30 Seconds', 'val': '30'},
            {'label': '45 Seconds', 'val': '45'},
            {'label': '60 Seconds (1 Min)', 'val': '60'},
            {'label': '120 Seconds (2 Min)', 'val': '120'}
        ]
    },
    {
        'slug': 'bomb_defuse',
        'title': 'Bomb Defuse',
        'badge': 'PRESSURE DECRYPT',
        'icon': '💣',
        'category': 'Precision Code Cracking',
        'summary': 'Defuse time bombs with sequential multi-character cryptograms. Typos inflict immediate timer penalties.',
        'win_condition': 'Crack all stages before detonation clock reaches 00:00.',
        'lose_condition': 'Countdown timer hits 00:00.',
        'supports': ['Solo vs Timer', '1v1 Duel'],
        'default_objective': 'stages',
        'objective_options': [
            {'label': '4 Detonation Stages', 'val': '4'},
            {'label': '7 Detonation Stages', 'val': '7'},
            {'label': '10 Detonation Stages', 'val': '10'}
        ]
    },
    {
        'slug': 'typing_ninja',
        'title': 'Typing Ninja',
        'badge': 'COMBO SLICE',
        'icon': '🥷',
        'category': 'Airborne Word Trajectories',
        'summary': 'Airborne words launch with parabolic momentum. Slice targets cleanly mid-air to build score multipliers.',
        'win_condition': 'Survive flight duration with highest slice score and unbroken multiplier combos.',
        'lose_condition': 'Drop 3 unsliced targets or score lower than opponent.',
        'supports': ['Solo vs AI', '1v1 Challenge'],
        'default_objective': 'timed',
        'objective_options': [
            {'label': '30 Seconds', 'val': '30'},
            {'label': '45 Seconds', 'val': '45'},
            {'label': '60 Seconds (1 Min)', 'val': '60'},
            {'label': '120 Seconds (2 Min)', 'val': '120'}
        ]
    },
    {
        'slug': 'memory_type',
        'title': 'Memory Type',
        'badge': 'BLIND RECALL',
        'icon': '🧠',
        'category': 'Working Cognitive Recall',
        'summary': 'Sequences flash briefly and vanish. Type the sequence completely from mental recall.',
        'win_condition': 'Maintain memory recall streak through selected flight duration.',
        'lose_condition': 'Accumulate 3 sequence recall strikes.',
        'supports': ['Solo vs AI', '1v1 Duel'],
        'default_objective': 'timed',
        'objective_options': [
            {'label': '30 Seconds', 'val': '30'},
            {'label': '45 Seconds', 'val': '45'},
            {'label': '60 Seconds (1 Min)', 'val': '60'},
            {'label': '120 Seconds (2 Min)', 'val': '120'}
        ]
    },
    {
        'slug': 'keyboard_quest',
        'title': 'Keyboard Quest',
        'badge': 'BIOMECHANIC MAP',
        'icon': '🗺️',
        'category': 'Ergonomic Row Progression',
        'summary': 'Journey through ergonomic training stages: Home Row anchors, upper extensions, bottom tucks, and number stretches.',
        'win_condition': 'Maintain typing stream throughout selected flight time with high accuracy.',
        'lose_condition': 'Timer expires with accuracy below baseline.',
        'supports': ['Solo Quest', 'Stage Duel'],
        'default_objective': 'timed',
        'objective_options': [
            {'label': '45 Seconds', 'val': '45'},
            {'label': '1 Minute (60s)', 'val': '60'},
            {'label': '2 Minutes (120s)', 'val': '120'},
            {'label': '5 Minutes (300s)', 'val': '300'},
            {'label': '10 Minutes (600s)', 'val': '600'}
        ]
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
        games=ARCADE_MASTER_REGISTRY,
        high_scores=user_high_scores
    )

@games_bp.route('/play/<game_slug>')
def play_arena(game_slug):
    game_info = next((g for g in ARCADE_MASTER_REGISTRY if g['slug'] == game_slug), None)
    if not game_info:
        return render_template('games/index.html', games=ARCADE_MASTER_REGISTRY)
    user_weak_keys = []
    if current_user.is_authenticated and current_user.dna_profile:
        stats = current_user.dna_profile.get_key_stats()
        user_weak_keys = [k.upper() for k, v in stats.items() if v.get('total', 0) >= 4 and (v.get('errors', 0)/v['total']) > 0.08][:6]
    return render_template(
        'games/arena.html',
        game=game_info,
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
    outcome = data.get('outcome', 'FINISHED')

    record = GameRecord(
        user_id=current_user.id if current_user.is_authenticated else None,
        game_mode=game_mode,
        play_type=data.get('play_type', 'solo_ai'),
        result_outcome=outcome,
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