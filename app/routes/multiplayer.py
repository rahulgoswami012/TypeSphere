from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
import uuid
import time
import random
from app import db, socketio
from app.models.user import User
from app.models.typing import TypingTest

multiplayer_bp = Blueprint('multiplayer', __name__)

# Core state containers
ROOMS = {}         # room_code -> room_dict
QUICK_QUEUE = []   # list of {'sid': sid, 'user_id': uid, 'name': str, 'queued_at': float}
SID_TO_ROOM = {}   # sid -> room_code

CURATED_PASSAGES = {
    30: [
        "Speed is nothing without precision. Keep your hands balanced, breathe calmly, and glide across the keys with absolute rhythm.",
        "Consistency is the hallmark of the master typist. Every accurate strike compounds into pure flow and unmatched velocity.",
        "Real velocity is born from economy of motion. Eliminate tension from your fingers and allow muscle memory to guide every stroke."
    ],
    60: [
        "Yes, the story is real, but the Taj Mahal did not physically disappear. The magician was P. C. Sorcar Jr., one of India's most famous illusionists. On 8 November 2000, he performed an illusion in Agra in which the Taj Mahal appeared to vanish for about two minutes to the spectators.",
        "It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife. However little known the feelings or views of such a man may be on his first entering a neighbourhood, this truth is fixed in the minds of the surrounding families.",
        "Distributed event streaming architectures enable modern services to communicate asynchronously with high throughput and resilience against failures by decoupling producers from consumers through immutable append-only logs."
    ],
    120: [
        "It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of foolishness, it was the epoch of belief, it was the epoch of incredulity, it was the season of light, it was the season of darkness, it was the spring of hope, it was the winter of despair. We had everything before us, we had nothing before us, we were all going direct to Heaven, we were all going direct the other way."
    ]
}

def get_passage(duration, custom_text=None):
    if custom_text and len(custom_text.strip()) >= 10:
        return custom_text.strip()
    if duration <= 30:
        return random.choice(CURATED_PASSAGES[30])
    elif duration <= 60:
        return random.choice(CURATED_PASSAGES[60])
    return random.choice(CURATED_PASSAGES[120])

def serialize_public_rooms():
    public_list = []
    for code, r in ROOMS.items():
        if r['type'] == 'public' and r['status'] == 'waiting':
            public_list.append({
                'code': code,
                'name': r['name'],
                'host_name': r['host_name'],
                'current_players': len([p for p in r['players'].values() if not p.get('left_early')]),
                'max_players': r['max_players'],
                'duration': r['duration'],
                'status': r['status']
            })
    return public_list

def get_sorted_standings(room):
    plist = [p for p in room['players'].values()]
    plist.sort(key=lambda x: (
        x.get('left_early', False),
        not x.get('finished', False),
        x.get('place') if x.get('place') is not None else 999,
        -(x.get('wpm') or 0),
        -(x.get('accuracy') or 0)
    ))
    return plist

@multiplayer_bp.route('/')
def index():
    return render_template('multiplayer/room.html')

@multiplayer_bp.route('/api/public-rooms')
def get_public_rooms():
    return jsonify({'rooms': serialize_public_rooms()})

# ==========================================
# Socket.IO Event Handlers
# ==========================================

@socketio.on('request_public_rooms')
def handle_request_public_rooms():
    emit('public_rooms_update', {'rooms': serialize_public_rooms()})

@socketio.on('create_room')
def handle_create_room(data):
    sid = request.sid
    room_type = data.get('type', 'public') # 'public' or 'private'
    name = (data.get('name') or f"Room-{random.randint(100,999)}").strip()
    player_name = (data.get('player_name') or 'Pilot').strip()
    duration = int(data.get('duration', 60))
    max_players = 2 if room_type == 'private' else int(data.get('max_players', 4))
    custom_text = (data.get('custom_text') or '').strip()

    cleanup_player(sid)

    code_prefix = "1V1" if room_type == 'private' else "PUB"
    room_code = f"{code_prefix}-{uuid.uuid4().hex[:6].upper()}"

    ROOMS[room_code] = {
        'code': room_code,
        'name': name,
        'type': room_type,
        'host_sid': sid,
        'host_name': player_name,
        'max_players': max_players,
        'duration': duration,
        'custom_text': custom_text,
        'text': get_passage(duration, custom_text),
        'status': 'waiting',
        'race_start_time': None,
        'created_at': time.time(),
        'players': {}
    }

    ROOMS[room_code]['players'][sid] = {
        'sid': sid,
        'user_id': current_user.id if current_user.is_authenticated else None,
        'name': player_name,
        'ready': True, # Host is ready by default
        'is_host': True,
        'progress': 0,
        'wpm': 0,
        'accuracy': 100,
        'errors': 0,
        'finished': False,
        'finish_time': None,
        'place': None,
        'left_early': False
    }

    SID_TO_ROOM[sid] = room_code
    join_room(room_code)

    emit('room_joined', {'room': ROOMS[room_code], 'your_sid': sid})
    emit('public_rooms_update', {'rooms': serialize_public_rooms()}, broadcast=True)

@socketio.on('join_room')
def handle_join_room(data):
    sid = request.sid
    room_code = (data.get('code') or '').strip().upper()
    player_name = (data.get('player_name') or 'Pilot').strip()

    if room_code not in ROOMS:
        emit('join_error', {'message': f"Room '{room_code}' was not found or has closed."})
        return

    room = ROOMS[room_code]

    if room['status'] != 'waiting':
        emit('join_error', {'message': "This room is currently in progress or finished."})
        return

    active_count = len([p for p in room['players'].values() if not p.get('left_early')])
    if active_count >= room['max_players']:
        emit('join_error', {'message': f"Room '{room_code}' is full (maximum {room['max_players']} players)."})
        return

    if sid in room['players']:
        emit('room_joined', {'room': room, 'your_sid': sid})
        return

    cleanup_player(sid)

    room['players'][sid] = {
        'sid': sid,
        'user_id': current_user.id if current_user.is_authenticated else None,
        'name': player_name,
        'ready': False,
        'is_host': False,
        'progress': 0,
        'wpm': 0,
        'accuracy': 100,
        'errors': 0,
        'finished': False,
        'finish_time': None,
        'place': None,
        'left_early': False
    }

    SID_TO_ROOM[sid] = room_code
    join_room(room_code)

    emit('room_joined', {'room': room, 'your_sid': sid})
    emit('room_state_updated', {'room': room}, room=room_code)
    emit('public_rooms_update', {'rooms': serialize_public_rooms()}, broadcast=True)

@socketio.on('toggle_ready')
def handle_toggle_ready():
    sid = request.sid
    room_code = SID_TO_ROOM.get(sid)
    if not room_code or room_code not in ROOMS:
        return

    room = ROOMS[room_code]
    if room['status'] != 'waiting':
        return

    if sid in room['players']:
        room['players'][sid]['ready'] = not room['players'][sid]['ready']
        emit('room_state_updated', {'room': room}, room=room_code)

@socketio.on('start_match')
def handle_start_match():
    sid = request.sid
    room_code = SID_TO_ROOM.get(sid)
    if not room_code or room_code not in ROOMS:
        return

    room = ROOMS[room_code]
    if room['status'] != 'waiting':
        return

    if room['host_sid'] != sid:
        emit('action_error', {'message': 'Only the room host can initiate the match.'})
        return

    players = room['players']
    active_players = [p for p in players.values() if not p.get('left_early')]

    if room['type'] in ['private', 'quick'] and len(active_players) < 2:
        emit('action_error', {'message': 'Cannot start a 1v1 match without an opponent.'})
        return

    not_ready = [p['name'] for p in active_players if not p['ready']]
    if not_ready:
        emit('action_error', {'message': f"Waiting for racers to ready up: {', '.join(not_ready)}"})
        return

    room['status'] = 'countdown'
    for p in players.values():
        p['progress'] = 0
        p['wpm'] = 0
        p['accuracy'] = 100
        p['errors'] = 0
        p['finished'] = False
        p['finish_time'] = None
        p['place'] = None
        p['left_early'] = False

    emit('match_countdown_started', {
        'room_code': room_code,
        'duration': room['duration'],
        'text': room['text']
    }, room=room_code)

    emit('public_rooms_update', {'rooms': serialize_public_rooms()}, broadcast=True)

@socketio.on('client_race_active')
def handle_client_race_active():
    sid = request.sid
    room_code = SID_TO_ROOM.get(sid)
    if room_code and room_code in ROOMS:
        room = ROOMS[room_code]
        if room['status'] == 'countdown':
            room['status'] = 'in_progress'
            room['race_start_time'] = time.time()

# ==========================================
# Real-Time Progress & Independent Finishes
# ==========================================

@socketio.on('progress_update')
def handle_progress_update(data):
    sid = request.sid
    room_code = SID_TO_ROOM.get(sid)
    if not room_code or room_code not in ROOMS:
        return

    room = ROOMS[room_code]
    if room['status'] not in ['countdown', 'in_progress']:
        return

    if sid not in room['players']:
        return

    player = room['players'][sid]
    if player.get('finished') or player.get('left_early'):
        return

    progress = max(0, min(100, float(data.get('progress', 0))))
    wpm = max(0, float(data.get('wpm', 0)))
    accuracy = max(0, min(100, float(data.get('accuracy', 100))))
    errors = int(data.get('errors', 0))

    player['progress'] = progress
    player['wpm'] = wpm
    player['accuracy'] = accuracy
    player['errors'] = errors

    # Individual Player Finish Execution
    if progress >= 100 and not player['finished']:
        player['finished'] = True
        
        # Calculate rank based on non-left finished players
        finished_racers = [p for p in room['players'].values() if p['finished'] and not p.get('left_early')]
        player['place'] = len(finished_racers)
        
        elapsed = time.time() - room['race_start_time'] if room.get('race_start_time') else room['duration']
        player['finish_time'] = round(elapsed, 2)

        # Save to database for authenticated users
        if player.get('user_id'):
            try:
                test_rec = TypingTest(
                    user_id=player['user_id'],
                    mode='multiplayer',
                    duration=float(player['finish_time']),
                    wpm=round(wpm, 1),
                    raw_wpm=round(wpm, 1),
                    accuracy=round(accuracy, 1),
                    consistency=100.0,
                    errors=errors,
                    suspicious=False
                )
                db.session.add(test_rec)
                db.session.commit()
            except Exception:
                db.session.rollback()

        # Check if ALL active participants have now finished
        active_remaining = [p for p in room['players'].values() if not p['finished'] and not p.get('left_early')]
        all_done = (len(active_remaining) == 0)

        if all_done:
            room['status'] = 'finished'

        emit('individual_player_finished', {
            'player': player,
            'remaining_count': len(active_remaining),
            'all_finished': all_done,
            'standings': get_sorted_standings(room) if all_done else []
        }, room=room_code)

    emit('room_progress_update', {'players': list(room['players'].values())}, room=room_code)

@socketio.on('time_expired_finish')
def handle_time_expired():
    sid = request.sid
    room_code = SID_TO_ROOM.get(sid)
    if not room_code or room_code not in ROOMS:
        return

    room = ROOMS[room_code]
    if room['status'] != 'in_progress':
        return

    room['status'] = 'finished'
    for p in room['players'].values():
        if not p['finished'] and not p.get('left_early'):
            p['finished'] = True
            p['place'] = 'DNF' if p['progress'] < 100 else p.get('place', 99)

    emit('race_concluded', {
        'room': room,
        'standings': get_sorted_standings(room)
    }, room=room_code)

@socketio.on('leave_race_after_finish')
def handle_leave_after_finish():
    """Player finished and chooses to leave instead of spectating."""
    sid = request.sid
    room_code = SID_TO_ROOM.get(sid)
    if not room_code or room_code not in ROOMS:
        emit('left_room_confirmed')
        return

    room = ROOMS[room_code]
    leave_room(room_code, sid=sid)
    SID_TO_ROOM.pop(sid, None)

    emit('left_room_confirmed')

    # Check if remaining active players are all finished
    active_remaining = [p for p in room['players'].values() if not p['finished'] and not p.get('left_early')]
    if len(active_remaining) == 0 and room['status'] == 'in_progress':
        room['status'] = 'finished'
        emit('race_concluded', {
            'room': room,
            'standings': get_sorted_standings(room)
        }, room=room_code)

@socketio.on('rematch_request')
def handle_rematch():
    sid = request.sid
    room_code = SID_TO_ROOM.get(sid)
    if not room_code or room_code not in ROOMS:
        return

    room = ROOMS[room_code]
    room['status'] = 'waiting'
    room['race_start_time'] = None
    room['text'] = get_passage(room['duration'], room.get('custom_text'))

    for p in room['players'].values():
        p['progress'] = 0
        p['wpm'] = 0
        p['accuracy'] = 100
        p['errors'] = 0
        p['finished'] = False
        p['finish_time'] = None
        p['place'] = None
        p['left_early'] = False
        p['ready'] = (p['sid'] == room['host_sid'])

    emit('rematch_accepted', {'room': room}, room=room_code)
    emit('public_rooms_update', {'rooms': serialize_public_rooms()}, broadcast=True)

# ==========================================
# Quick Match Matchmaking Queue
# ==========================================

@socketio.on('join_quick_queue')
def handle_join_quick_queue(data):
    sid = request.sid
    player_name = (data.get('name') or 'Pilot').strip()
    user_id = current_user.id if current_user.is_authenticated else None

    cleanup_player(sid)

    for q in list(QUICK_QUEUE):
        if q['sid'] == sid:
            QUICK_QUEUE.remove(q)

    if len(QUICK_QUEUE) > 0:
        opponent = QUICK_QUEUE.pop(0)

        if opponent['sid'] == sid:
            QUICK_QUEUE.append({'sid': sid, 'user_id': user_id, 'name': player_name, 'queued_at': time.time()})
            emit('quick_queue_waiting')
            return

        match_code = f"QM-{uuid.uuid4().hex[:6].upper()}"
        duration = 60
        text = get_passage(duration)

        ROOMS[match_code] = {
            'code': match_code,
            'name': 'Quick 1v1 Match',
            'type': 'quick',
            'host_sid': sid,
            'host_name': player_name,
            'max_players': 2,
            'duration': duration,
            'custom_text': '',
            'text': text,
            'status': 'waiting',
            'race_start_time': None,
            'created_at': time.time(),
            'players': {
                sid: {
                    'sid': sid,
                    'user_id': user_id,
                    'name': player_name,
                    'ready': True,
                    'is_host': True,
                    'progress': 0,
                    'wpm': 0,
                    'accuracy': 100,
                    'errors': 0,
                    'finished': False,
                    'finish_time': None,
                    'place': None,
                    'left_early': False
                },
                opponent['sid']: {
                    'sid': opponent['sid'],
                    'user_id': opponent['user_id'],
                    'name': opponent['name'],
                    'ready': True,
                    'is_host': False,
                    'progress': 0,
                    'wpm': 0,
                    'accuracy': 100,
                    'errors': 0,
                    'finished': False,
                    'finish_time': None,
                    'place': None,
                    'left_early': False
                }
            }
        }

        SID_TO_ROOM[sid] = match_code
        SID_TO_ROOM[opponent['sid']] = match_code

        join_room(match_code, sid=sid)
        join_room(match_code, sid=opponent['sid'])

        emit('quick_match_paired', {'room': ROOMS[match_code], 'your_sid': sid}, room=sid)
        emit('quick_match_paired', {'room': ROOMS[match_code], 'your_sid': opponent['sid']}, room=opponent['sid'])
    else:
        QUICK_QUEUE.append({'sid': sid, 'user_id': user_id, 'name': player_name, 'queued_at': time.time()})
        emit('quick_queue_waiting')

@socketio.on('cancel_quick_queue')
def handle_cancel_quick_queue():
    sid = request.sid
    for q in list(QUICK_QUEUE):
        if q['sid'] == sid:
            QUICK_QUEUE.remove(q)
    emit('quick_queue_cancelled')

# ==========================================
# Disconnect & Navigation Cleanup
# ==========================================

@socketio.on('leave_room_voluntary')
def handle_leave_room_voluntary():
    cleanup_player(request.sid)
    emit('left_room_confirmed')
    emit('public_rooms_update', {'rooms': serialize_public_rooms()}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    cleanup_player(request.sid)
    emit('public_rooms_update', {'rooms': serialize_public_rooms()}, broadcast=True)

def cleanup_player(sid):
    for q in list(QUICK_QUEUE):
        if q['sid'] == sid:
            QUICK_QUEUE.remove(q)

    room_code = SID_TO_ROOM.pop(sid, None)
    if not room_code or room_code not in ROOMS:
        return

    room = ROOMS[room_code]
    leave_room(room_code, sid=sid)

    if sid in room['players']:
        player = room['players'][sid]
        # If left during active race, mark as DNF
        if room['status'] in ['countdown', 'in_progress'] and not player.get('finished'):
            player['left_early'] = True
            player['place'] = 'DNF'
        elif room['status'] == 'waiting':
            del room['players'][sid]

    # Delete if entirely empty
    active_any = [p for p in room['players'].values() if not p.get('left_early')]
    if not active_any:
        del ROOMS[room_code]
        return

    # If host departed in lobby, assign next player
    if room['status'] == 'waiting' and room['host_sid'] == sid:
        next_sid = next(iter(room['players']))
        room['host_sid'] = next_sid
        room['host_name'] = room['players'][next_sid]['name']
        room['players'][next_sid]['is_host'] = True
        room['players'][next_sid]['ready'] = True

    # If all remaining players in active match are finished, conclude
    if room['status'] == 'in_progress':
        active_remaining = [p for p in room['players'].values() if not p['finished'] and not p.get('left_early')]
        if len(active_remaining) == 0:
            room['status'] = 'finished'
            emit('race_concluded', {
                'room': room,
                'standings': get_sorted_standings(room)
            }, room=room_code)

    emit('room_state_updated', {'room': room}, room=room_code)