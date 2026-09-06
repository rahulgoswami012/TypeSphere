from flask import Blueprint, render_template, request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
import uuid
import random
from app import db, socketio
from app.models.user import User

multiplayer_bp = Blueprint('multiplayer', __name__)

# ROOMS structure: room_id -> { 'text': str, 'status': 'lobby'|'countdown'|'racing'|'finished', 'host_sid': str, 'players': {} }
ROOMS = {}

COMPETITIVE_TEXTS = [
    "Speed is nothing without precision. Keep your hands balanced, breathe calmly, and glide across the keys with absolute rhythm.",
    "Real velocity is born from economy of motion. Eliminate tension from your fingers and allow tactile muscle memory to guide every stroke.",
    "Competitive mastery requires balance under high pressure. Accuracy establishes the foundation upon which raw velocity flourishes.",
    "Consistency is the hallmark of the master typist. Every accurate strike compounds into pure flow and unmatched velocity."
]

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

    # Remove from previous rooms
    for r_id, r_data in list(ROOMS.items()):
        if sid in r_data['players']:
            leave_room(r_id)
            del r_data['players'][sid]
            if not r_data['players']:
                del ROOMS[r_id]
            else:
                if r_data['host_sid'] == sid:
                    r_data['host_sid'] = next(iter(r_data['players']))
                emit('room_update', r_data, room=r_id)

    join_room(room)
    if room not in ROOMS:
        ROOMS[room] = {
            'text': random.choice(COMPETITIVE_TEXTS),
            'status': 'lobby', # 'lobby', 'countdown', 'racing', 'finished'
            'host_sid': sid,
            'players': {}
        }

    ROOMS[room]['players'][sid] = {
        'id': sid,
        'name': name,
        'progress': 0,
        'wpm': 0,
        'finished': False,
        'place': None,
        'is_host': (ROOMS[room]['host_sid'] == sid)
    }

    emit('room_update', ROOMS[room], room=room)

@socketio.on('start_countdown')
def handle_countdown(data):
    room = (data.get('room') or 'public-arena').strip()
    sid = request.sid

    if room in ROOMS:
        # STRICT LOCK: Only allow starting from 'lobby' or 'finished'
        if ROOMS[room]['status'] in ['countdown', 'racing']:
            return

        ROOMS[room]['status'] = 'countdown'
        ROOMS[room]['text'] = random.choice(COMPETITIVE_TEXTS)

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

            # If all human players in room have finished, unlock for rematch
            if finished_count >= len(ROOMS[room]['players']):
                ROOMS[room]['status'] = 'finished'

            emit('player_finished', {
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
                if rdata['host_sid'] == sid:
                    rdata['host_sid'] = next(iter(rdata['players']))
                    rdata['players'][rdata['host_sid']]['is_host'] = True
                emit('room_update', rdata, room=room)