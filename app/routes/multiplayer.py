from flask import Blueprint, render_template, request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
import uuid
import random
from app import db, socketio
from app.models.user import User

multiplayer_bp = Blueprint('multiplayer', __name__)

ROOMS = {} # room_id -> { text, players, status, is_ranked }
RANKED_QUEUE = [] # list of { sid, user_id, username, elo }

COMPETITIVE_TEXTS = [
    "Synchronization demands calm recognition. The disciplined mind strikes keys with measured rhythm, compounding focus into unstoppable speed.",
    "Real velocity is born from economy of motion. Eliminate tension from your fingers and allow tactile muscle memory to guide every stroke.",
    "Competitive mastery requires balance under high pressure. Accuracy establishes the foundation upon which raw velocity flourishes."
]

def calculate_elo_change(player_a_elo, player_b_elo, a_won):
    """Standard Elo Algorithm (K=32)"""
    expected_a = 1.0 / (1.0 + 10.0 ** ((player_b_elo - player_a_elo) / 400.0))
    actual_a = 1.0 if a_won else 0.0
    delta = round(32 * (actual_a - expected_a))
    return delta

@multiplayer_bp.route('/')
def index():
    user_elo = current_user.elo_rating if current_user.is_authenticated else 1000
    user_division = current_user.rank_division if current_user.is_authenticated else "Bronze"
    user_badge = current_user.rank_badge if current_user.is_authenticated else {"icon": "🥉", "color": "#b45309"}
    wins = current_user.ranked_wins if current_user.is_authenticated else 0
    losses = current_user.ranked_losses if current_user.is_authenticated else 0

    return render_template(
        'multiplayer/room.html',
        user_elo=user_elo,
        user_division=user_division,
        user_badge=user_badge,
        wins=wins,
        losses=losses
    )

# ==========================================
# 1. Casual Room Handling
# ==========================================
@socketio.on('join_race')
def handle_join(data):
    room = (data.get('room') or 'public-arena').strip()
    name = (data.get('name') or 'Pilot').strip()
    sid = request.sid

    join_room(room)
    if room not in ROOMS:
        ROOMS[room] = {
            'text': random.choice(COMPETITIVE_TEXTS),
            'players': {},
            'status': 'lobby',
            'is_ranked': False
        }

    ROOMS[room]['players'][sid] = {
        'id': sid,
        'name': name,
        'progress': 0,
        'wpm': 0,
        'finished': False,
        'place': None
    }

    emit('room_update', ROOMS[room], room=room)

@socketio.on('start_countdown')
def handle_countdown(data):
    room = (data.get('room') or 'public-arena').strip()
    if room in ROOMS:
        ROOMS[room]['status'] = 'countdown'
        for sid in ROOMS[room]['players']:
            ROOMS[room]['players'][sid]['progress'] = 0
            ROOMS[room]['players'][sid]['wpm'] = 0
            ROOMS[room]['players'][sid]['finished'] = False
            ROOMS[room]['players'][sid]['place'] = None

        emit('race_countdown_started', {'status': 'countdown', 'text': ROOMS[room]['text']}, room=room)

# ==========================================
# 2. Version 2.0 Ranked 1v1 Queue & Matchmaker
# ==========================================
@socketio.on('join_ranked_queue')
def handle_ranked_queue(data):
    sid = request.sid
    username = data.get('username', 'Pilot')
    elo = int(data.get('elo', 1000))
    user_id = current_user.id if current_user.is_authenticated else None

    # Remove stale entry if re-queuing
    for q in list(RANKED_QUEUE):
        if q['sid'] == sid:
            RANKED_QUEUE.remove(q)

    # Check if an opponent is waiting
    if len(RANKED_QUEUE) > 0:
        opponent = RANKED_QUEUE.pop(0)
        match_room = f"ranked-match-{uuid.uuid4().hex[:8]}"

        selected_passage = random.choice(COMPETITIVE_TEXTS)
        ROOMS[match_room] = {
            'text': selected_passage,
            'status': 'countdown',
            'is_ranked': True,
            'players': {
                sid: {'id': sid, 'user_id': user_id, 'name': username, 'elo': elo, 'progress': 0, 'wpm': 0, 'finished': False, 'place': None},
                opponent['sid']: {'id': opponent['sid'], 'user_id': opponent['user_id'], 'name': opponent['username'], 'elo': opponent['elo'], 'progress': 0, 'wpm': 0, 'finished': False, 'place': None}
            }
        }

        join_room(match_room, sid=sid)
        join_room(match_room, sid=opponent['sid'])

        emit('ranked_match_found', {
            'room': match_room,
            'text': selected_passage,
            'player_a': {'name': username, 'elo': elo},
            'player_b': {'name': opponent['username'], 'elo': opponent['elo']}
        }, room=match_room)

    else:
        RANKED_QUEUE.append({
            'sid': sid,
            'user_id': user_id,
            'username': username,
            'elo': elo
        })
        emit('ranked_searching', {'message': 'Searching for opponent in your division...'})

@socketio.on('leave_ranked_queue')
def handle_leave_queue():
    sid = request.sid
    for q in list(RANKED_QUEUE):
        if q['sid'] == sid:
            RANKED_QUEUE.remove(q)
    emit('ranked_queue_cancelled', {'message': 'Queue search cancelled.'})

# ==========================================
# 3. Progress Tracking & Elo Recalculation
# ==========================================
@socketio.on('progress_update')
def handle_progress(data):
    room = data.get('room')
    progress = data.get('progress', 0)
    wpm = data.get('wpm', 0)
    sid = request.sid

    if room in ROOMS and sid in ROOMS[room]['players']:
        ROOMS[room]['players'][sid]['progress'] = progress
        ROOMS[room]['players'][sid]['wpm'] = wpm

        if progress >= 100 and not ROOMS[room]['players'][sid]['finished']:
            ROOMS[room]['players'][sid]['finished'] = True
            finished_count = sum(1 for p in ROOMS[room]['players'].values() if p['finished'])
            ROOMS[room]['players'][sid]['place'] = finished_count

            # If Ranked 1v1 match concludes, calculate Elo adjustments
            if ROOMS[room].get('is_ranked'):
                players_list = list(ROOMS[room]['players'].values())
                if len(players_list) == 2 and finished_count == 1:
                    winner = ROOMS[room]['players'][sid]
                    loser = players_list[1] if players_list[0]['id'] == sid else players_list[0]

                    elo_delta = calculate_elo_change(winner['elo'], loser['elo'], a_won=True)

                    # Update Database Records for registered pilots
                    if winner.get('user_id'):
                        u_win = User.query.get(winner['user_id'])
                        if u_win:
                            u_win.elo_rating = max(100, u_win.elo_rating + elo_delta)
                            u_win.ranked_wins = (u_win.ranked_wins or 0) + 1

                    if loser.get('user_id'):
                        u_lose = User.query.get(loser['user_id'])
                        if u_lose:
                            u_lose.elo_rating = max(100, u_lose.elo_rating - elo_delta)
                            u_lose.ranked_losses = (u_lose.ranked_losses or 0) + 1

                    db.session.commit()

                    emit('ranked_game_over', {
                        'winner_name': winner['name'],
                        'elo_delta': elo_delta,
                        'winner_new_elo': winner['elo'] + elo_delta,
                        'loser_new_elo': max(100, loser['elo'] - elo_delta)
                    }, room=room)

            emit('player_finished', {'name': ROOMS[room]['players'][sid]['name'], 'place': finished_count, 'wpm': wpm}, room=room)

        emit('race_progress', {'players': ROOMS[room]['players']}, room=room)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    for q in list(RANKED_QUEUE):
        if q['sid'] == sid:
            RANKED_QUEUE.remove(q)

    for room, rdata in list(ROOMS.items()):
        if sid in rdata['players']:
            del rdata['players'][sid]
            emit('room_update', rdata, room=room)