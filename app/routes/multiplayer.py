from flask import Blueprint, render_template, request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
import uuid
import random
from app import db, socketio
from app.models.user import User

multiplayer_bp = Blueprint('multiplayer', __name__)

ROOMS = {}

MATCH_PASSAGES = {
    'standard': [
        "Speed is nothing without precision. Keep your hands balanced, breathe calmly, and glide across the keys with absolute rhythm.",
        "Real velocity is born from economy of motion. Eliminate tension from your fingers and allow tactile muscle memory to guide every stroke.",
        "Consistency is the hallmark of the master typist. Every accurate strike compounds into pure flow and unmatched velocity."
    ],
    'code': [
        "def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)",
        "const calculateCadence = (events) => {\n  return events.reduce((acc, curr, idx, arr) => {\n    if (idx === 0) return acc;\n    return acc + (curr.timestamp - arr[idx - 1].timestamp);\n  }, 0) / (events.length - 1);\n};"
    ],
    'quotes': [
        "It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife.",
        "It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of foolishness."
    ]
}

def calculate_elo_change(player_a_elo, player_b_elo, a_won):
    expected_a = 1.0 / (1.0 + 10.0 ** ((player_b_elo - player_a_elo) / 400.0))
    actual_a = 1.0 if a_won else 0.0
    return round(32 * (actual_a - expected_a))

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

@socketio.on('join_race')
def handle_join(data):
    room = (data.get('room') or 'public-arena').strip()
    name = (data.get('name') or 'Pilot').strip()
    sid = request.sid

    for r_id, r_data in list(ROOMS.items()):
        if sid in r_data['players']:
            leave_room(r_id)
            del r_data['players'][sid]
            if not r_data['players']:
                del ROOMS[r_id]
            else:
                emit('room_update', r_data, room=r_id)

    join_room(room)
    if room not in ROOMS:
        ROOMS[room] = {
            'text': random.choice(MATCH_PASSAGES['standard']),
            'mode': 'standard',
            'status': 'lobby',
            'host_sid': sid,
            'players': {}
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

@socketio.on('set_match_mode')
def handle_set_mode(data):
    room = (data.get('room') or 'public-arena').strip()
    chosen_mode = data.get('mode', 'standard')
    if room in ROOMS and ROOMS[room]['status'] in ['lobby', 'finished']:
        ROOMS[room]['mode'] = chosen_mode
        passages = MATCH_PASSAGES.get(chosen_mode, MATCH_PASSAGES['standard'])
        ROOMS[room]['text'] = random.choice(passages)
        emit('mode_updated', {'mode': chosen_mode, 'text': ROOMS[room]['text']}, room=room)

@socketio.on('start_countdown')
def handle_countdown(data):
    room = (data.get('room') or 'public-arena').strip()
    if room in ROOMS:
        if ROOMS[room]['status'] in ['countdown', 'racing']:
            return

        ROOMS[room]['status'] = 'countdown'
        passages = MATCH_PASSAGES.get(ROOMS[room].get('mode', 'standard'), MATCH_PASSAGES['standard'])
        ROOMS[room]['text'] = random.choice(passages)

        for p_sid in ROOMS[room]['players']:
            ROOMS[room]['players'][p_sid]['progress'] = 0
            ROOMS[room]['players'][p_sid]['wpm'] = 0
            ROOMS[room]['players'][p_sid]['finished'] = False
            ROOMS[room]['players'][p_sid]['place'] = None

        emit('race_countdown_started', {
            'text': ROOMS[room]['text'],
            'room': room
        }, room=room)

@socketio.on('race_active_status')
def handle_race_active(data):
    room = (data.get('room') or 'public-arena').strip()
    if room in ROOMS:
        ROOMS[room]['status'] = 'racing'

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

            if finished_count >= len(ROOMS[room]['players']):
                ROOMS[room]['status'] = 'finished'

            emit('player_finished', {
                'id': sid,
                'name': ROOMS[room]['players'][sid]['name'],
                'place': finished_count,
                'wpm': wpm,
                'all_finished': (ROOMS[room]['status'] == 'finished')
            }, room=room)

        emit('race_progress', {'players': ROOMS[room]['players']}, room=room)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    for room, rdata in list(ROOMS.items()):
        if sid in rdata['players']:
            del rdata['players'][sid]
            if not rdata['players']:
                del ROOMS[room]
            else:
                emit('room_update', rdata, room=room)